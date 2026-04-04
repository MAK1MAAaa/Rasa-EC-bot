<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'

interface ShopInfo {
  id: string
  name: string
  description?: string | null
  contact_email?: string | null
  contact_phone?: string | null
}

interface AddressItem {
  id: string
  shop_id: string
  label: string
  contact_name: string
  contact_phone: string
  province: string
  city: string
  district: string
  address_line: string
  postal_code?: string | null
  is_default: boolean
}

interface MerchantProduct {
  id: string
  shop_id: string
  shop_name: string
  name: string
  description?: string
  image_url?: string
  category?: string
  price: number
  stock: number
  is_active: boolean
}

interface MerchantOrderItem {
  id: string
  product_id: string
  product_name: string
  quantity: number
  subtotal: number
  product_link: string
}

interface MerchantLogistics {
  tracking_no?: string | null
  status: string
  current_location?: string | null
  estimated_delivery_at?: string | null
  route_plan: string[]
}

interface MerchantOrder {
  id: string
  status: string
  address: string
  contact_email: string
  total_amount: number
  created_at: string
  items: MerchantOrderItem[]
  logistics?: MerchantLogistics | null
}

type TabKey = 'orders' | 'products' | 'addresses'
type ToastKind = 'success' | 'error'

const authStore = useAuthStore()
const activeTab = ref<TabKey>('orders')
const loading = ref(false)
const actionLoading = ref(false)
const error = ref('')
const success = ref('')

const shop = ref<ShopInfo | null>(null)
const addresses = ref<AddressItem[]>([])
const products = ref<MerchantProduct[]>([])
const orders = ref<MerchantOrder[]>([])
const orderFilter = ref<'pending_shipment' | 'shipped' | 'all'>('pending_shipment')
const shipAddressByOrder = ref<Record<string, string>>({})
const shippingOrderState = ref<Record<string, boolean>>({})
const shipToast = ref<{ visible: boolean; type: ToastKind; message: string }>({
  visible: false,
  type: 'success',
  message: ''
})
let shipToastTimer: ReturnType<typeof setTimeout> | null = null

const productForm = reactive({
  name: '',
  category: '',
  price: 0,
  stock: 0,
  image_url: '',
  description: ''
})

const addressForm = reactive({
  label: '',
  contact_name: '',
  contact_phone: '',
  province: '',
  city: '',
  district: '',
  address_line: '',
  postal_code: '',
  is_default: false
})

const shopDisplay = computed(() => shop.value?.name || authStore.user?.shop?.name || '商家店铺')

const showShipToast = (type: ToastKind, message: string) => {
  if (shipToastTimer) {
    clearTimeout(shipToastTimer)
  }
  shipToast.value = { visible: true, type, message }
  shipToastTimer = setTimeout(() => {
    shipToast.value.visible = false
  }, 2600)
}

const isShippingOrder = (orderId: string) => !!shippingOrderState.value[orderId]

const clearNotice = () => {
  error.value = ''
  success.value = ''
}

const parseErr = (err: any, fallback: string) => {
  const detail = err?.response?.data?.detail
  if (!detail) {
    return fallback
  }
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || JSON.stringify(item))
      .join('；')
  }
  return JSON.stringify(detail)
}

const loadShop = async () => {
  const response = await api.get('/merchant/shop')
  shop.value = response.data
}

const loadAddresses = async () => {
  const response = await api.get('/merchant/addresses')
  addresses.value = response.data
}

const loadProducts = async () => {
  const pageSize = 100
  let page = 1
  let allItems: MerchantProduct[] = []
  let total = 0

  do {
    const response = await api.get('/merchant/products', {
      params: { page, page_size: pageSize }
    })
    const items: MerchantProduct[] = response.data.items || []
    total = Number(response.data.total || 0)
    if (items.length === 0) {
      break
    }
    allItems = allItems.concat(items)
    page += 1
  } while (allItems.length < total)

  products.value = allItems
}

const loadOrders = async () => {
  const response = await api.get('/merchant/orders', {
    params: { status_filter: orderFilter.value }
  })
  orders.value = response.data.items

  const map: Record<string, string> = {}
  for (const order of orders.value) {
    const defaultAddress = addresses.value.find((item) => item.is_default)
    if (defaultAddress) {
      map[order.id] = defaultAddress.id
    }
  }
  shipAddressByOrder.value = { ...shipAddressByOrder.value, ...map }
}

const loadAll = async () => {
  loading.value = true
  clearNotice()
  try {
    await loadShop()
    await loadAddresses()
    await loadProducts()
    await loadOrders()
  } catch (err: any) {
    error.value = parseErr(err, '商家控制台加载失败')
  } finally {
    loading.value = false
  }
}

const createProduct = async () => {
  clearNotice()
  actionLoading.value = true
  try {
    await api.post('/merchant/products', {
      name: productForm.name,
      category: productForm.category || null,
      price: Number(productForm.price),
      stock: Number(productForm.stock),
      image_url: productForm.image_url || null,
      description: productForm.description || null,
      is_active: true
    })
    success.value = '商品已上架'
    productForm.name = ''
    productForm.category = ''
    productForm.price = 0
    productForm.stock = 0
    productForm.image_url = ''
    productForm.description = ''
    await loadProducts()
  } catch (err: any) {
    error.value = parseErr(err, '商品上架失败')
  } finally {
    actionLoading.value = false
  }
}

const toggleProductActive = async (item: MerchantProduct) => {
  clearNotice()
  actionLoading.value = true
  try {
    await api.patch(`/merchant/products/${item.id}`, {
      is_active: !item.is_active
    })
    success.value = item.is_active ? '商品已下架' : '商品已上架'
    await loadProducts()
  } catch (err: any) {
    error.value = parseErr(err, '更新商品状态失败')
  } finally {
    actionLoading.value = false
  }
}

const createAddress = async () => {
  clearNotice()
  actionLoading.value = true
  try {
    await api.post('/merchant/addresses', {
      ...addressForm,
      postal_code: addressForm.postal_code || null
    })
    success.value = '发货地址已新增'
    addressForm.label = ''
    addressForm.contact_name = ''
    addressForm.contact_phone = ''
    addressForm.province = ''
    addressForm.city = ''
    addressForm.district = ''
    addressForm.address_line = ''
    addressForm.postal_code = ''
    addressForm.is_default = false
    await loadAddresses()
    await loadOrders()
  } catch (err: any) {
    error.value = parseErr(err, '新增地址失败')
  } finally {
    actionLoading.value = false
  }
}

const setDefaultAddress = async (addressId: string) => {
  clearNotice()
  actionLoading.value = true
  try {
    await api.patch(`/merchant/addresses/${addressId}`, { is_default: true })
    success.value = '默认地址已更新'
    await loadAddresses()
    await loadOrders()
  } catch (err: any) {
    error.value = parseErr(err, '更新默认地址失败')
  } finally {
    actionLoading.value = false
  }
}

const shipOrder = async (order: MerchantOrder) => {
  clearNotice()
  if (isShippingOrder(order.id)) {
    return
  }
  const addressId = shipAddressByOrder.value[order.id]

  shippingOrderState.value[order.id] = true
  try {
    await api.post(
      `/merchant/orders/${order.id}/ship`,
      {
        ship_from_address_id: addressId || null
      },
      {
        timeout: 60000
      }
    )
    showShipToast('success', '订单 ' + order.id + ' 已发货')
    await loadOrders()
  } catch (err: any) {
    showShipToast('error', parseErr(err, '发货失败'))
  } finally {
    shippingOrderState.value[order.id] = false
  }
}

onMounted(loadAll)
onBeforeUnmount(() => {
  if (shipToastTimer) {
    clearTimeout(shipToastTimer)
  }
})
</script>

<template>
  <section class="merchant-page">
    <transition name="toast-fade">
      <div v-if="shipToast.visible" class="ship-toast" :class="shipToast.type">
        {{ shipToast.message }}
      </div>
    </transition>

    <div class="hero">
      <h1>{{ shopDisplay }}</h1>
      <span>商家工作台</span>
    </div>

    <div class="tabs">
      <button :class="activeTab === 'orders' ? 'active' : ''" @click="activeTab = 'orders'">订单</button>
      <button :class="activeTab === 'products' ? 'active' : ''" @click="activeTab = 'products'">商品</button>
      <button :class="activeTab === 'addresses' ? 'active' : ''" @click="activeTab = 'addresses'">地址</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="success" class="success">{{ success }}</p>

    <div v-if="loading" class="state-card">加载中...</div>

    <template v-else>
      <section v-if="activeTab === 'orders'" class="panel">
        <div class="panel-head">
          <h2>订单</h2>
          <div class="filter-row">
            <select v-model="orderFilter" @change="loadOrders">
              <option value="pending_shipment">待发货</option>
              <option value="shipped">已发货</option>
              <option value="all">全部</option>
            </select>
            <button @click="loadOrders">刷新</button>
          </div>
        </div>

        <div v-if="orders.length === 0" class="state-card">暂无订单</div>

        <article v-for="order in orders" :key="order.id" class="order-card">
          <div class="row">
            <strong>{{ order.id }}</strong>
            <span class="status">{{ order.status }}</span>
          </div>
          <p class="muted">收货地址：{{ order.address }}</p>

          <ul class="items">
            <li v-for="item in order.items" :key="item.id">
              <a :href="`/products/${item.product_id}`" target="_blank">{{ item.product_name }}</a>
              <span>x {{ item.quantity }}</span>
              <strong>¥ {{ item.subtotal.toFixed(2) }}</strong>
            </li>
          </ul>

          <div class="ship-row" v-if="order.status === 'pending_shipment'">
            <select v-model="shipAddressByOrder[order.id]">
              <option value="">默认发货地址</option>
              <option v-for="addr in addresses" :key="addr.id" :value="addr.id">
                {{ addr.label }} · {{ addr.province }}{{ addr.city }}{{ addr.district }}{{ addr.address_line }}
              </option>
            </select>
            <button :disabled="actionLoading || isShippingOrder(order.id)" @click="shipOrder(order)">
              {{ isShippingOrder(order.id) ? '发货中...' : '发货' }}
            </button>
          </div>

          <div v-if="order.logistics" class="logistics">
            <p><strong>运单号：</strong>{{ order.logistics.tracking_no || '待生成' }}</p>
            <p><strong>当前位置：</strong>{{ order.logistics.current_location || '-' }}</p>
            <p><strong>预计送达：</strong>{{ order.logistics.estimated_delivery_at ? new Date(order.logistics.estimated_delivery_at).toLocaleString() : '-' }}</p>
            <p><strong>途径：</strong>{{ (order.logistics.route_plan || []).join(' -> ') || '-' }}</p>
          </div>
        </article>
      </section>

      <section v-if="activeTab === 'products'" class="panel">
        <h2>上架商品</h2>
        <form class="grid-form" @submit.prevent="createProduct">
          <input v-model="productForm.name" required placeholder="商品名称">
          <input v-model="productForm.category" placeholder="分类">
          <input v-model.number="productForm.price" min="0" step="0.01" type="number" required placeholder="价格">
          <input v-model.number="productForm.stock" min="0" step="1" type="number" required placeholder="库存">
          <input v-model="productForm.image_url" placeholder="图片 URL">
          <textarea v-model="productForm.description" rows="2" placeholder="商品描述"></textarea>
          <button :disabled="actionLoading" type="submit">上架</button>
        </form>

        <h3>商品列表</h3>
        <div class="table-list">
          <article v-for="item in products" :key="item.id" class="product-row">
            <div>
              <strong>{{ item.name }}</strong>
              <p class="muted">{{ item.category || '未分类' }} · 库存 {{ item.stock }} · ¥ {{ item.price.toFixed(2) }}</p>
            </div>
            <button :disabled="actionLoading" @click="toggleProductActive(item)">
              {{ item.is_active ? '下架' : '上架' }}
            </button>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'addresses'" class="panel">
        <h2>发货地址</h2>
        <form class="grid-form" @submit.prevent="createAddress">
          <input v-model="addressForm.label" required placeholder="地址标签">
          <input v-model="addressForm.contact_name" required placeholder="联系人">
          <input v-model="addressForm.contact_phone" required placeholder="联系电话">
          <input v-model="addressForm.province" required placeholder="省份">
          <input v-model="addressForm.city" required placeholder="城市">
          <input v-model="addressForm.district" required placeholder="区县">
          <input v-model="addressForm.address_line" required placeholder="详细地址">
          <input v-model="addressForm.postal_code" placeholder="邮编（可选）">
          <label class="inline-check">
            <input v-model="addressForm.is_default" type="checkbox">
            设为默认
          </label>
          <button :disabled="actionLoading" type="submit">新增</button>
        </form>

        <h3>地址列表</h3>
        <div class="table-list">
          <article v-for="addr in addresses" :key="addr.id" class="address-row">
            <div>
              <strong>{{ addr.label }}</strong>
              <p class="muted">{{ addr.contact_name }} · {{ addr.contact_phone }}</p>
              <p class="muted">{{ addr.province }}{{ addr.city }}{{ addr.district }}{{ addr.address_line }}</p>
            </div>
            <div class="right-tools">
              <span v-if="addr.is_default" class="badge">默认</span>
              <button v-else :disabled="actionLoading" @click="setDefaultAddress(addr.id)">设为默认</button>
            </div>
          </article>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.merchant-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 18px 38px;
  display: grid;
  gap: 14px;
}

.hero {
  background: linear-gradient(120deg, #2f2413, #765322);
  color: #fff7ea;
  border-radius: 18px;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: end;
}

.hero h1 {
  margin: 0;
}

.hero span {
  opacity: 0.85;
}

.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tabs button {
  border: 1px solid #d7c8ae;
  border-radius: 999px;
  background: #fff8eb;
  color: #4d3d22;
  padding: 8px 14px;
}

.tabs button.active {
  background: #2f2413;
  color: #fff7ea;
  border-color: #2f2413;
}

.panel {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.filter-row {
  display: flex;
  gap: 8px;
}

.filter-row select,
.filter-row button,
.ship-row select,
.ship-row button,
.grid-form input,
.grid-form textarea,
.grid-form button {
  border: 1px solid #d8cbb4;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fffcf5;
}

.filter-row button,
.ship-row button,
.grid-form button,
.product-row button,
.address-row button {
  border: none;
  background: #2f2413;
  color: #fff7ea;
}

.grid-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.grid-form textarea,
.grid-form button,
.grid-form .inline-check {
  grid-column: 1 / -1;
}

.inline-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #5b5244;
}

.order-card,
.product-row,
.address-row {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  display: grid;
  gap: 8px;
  background: #fffcf6;
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status,
.badge {
  background: #f1dfbd;
  color: #594523;
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}

.items li {
  display: flex;
  gap: 8px;
  align-items: center;
}

.items a {
  color: #60431a;
  text-decoration: none;
}

.ship-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.logistics {
  border-top: 1px dashed #d6c7ad;
  padding-top: 8px;
  color: #4f4538;
}

.table-list {
  display: grid;
  gap: 8px;
}

.product-row,
.address-row {
  grid-template-columns: 1fr auto;
  align-items: center;
}

.muted {
  margin: 0;
  color: #6f6657;
  font-size: 13px;
}

.right-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.state-card,
.error,
.success {
  border-radius: 12px;
  padding: 12px;
}

.state-card {
  background: #fffdf7;
  border: 1px dashed #d7c9af;
  text-align: center;
}

.error {
  background: #fff1f2;
  color: #be123c;
}

.success {
  background: #ecfeff;
  color: #0f766e;
}

.ship-toast {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: 1200;
  max-width: min(88vw, 360px);
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 14px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14);
  border: 1px solid transparent;
  backdrop-filter: blur(4px);
}

.ship-toast.success {
  background: rgba(236, 253, 255, 0.96);
  color: #0f766e;
  border-color: #99f6e4;
}

.ship-toast.error {
  background: rgba(255, 241, 242, 0.96);
  color: #be123c;
  border-color: #fecdd3;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.22s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 860px) {
  .grid-form {
    grid-template-columns: 1fr;
  }

  .ship-row,
  .product-row,
  .address-row,
  .panel-head {
    grid-template-columns: 1fr;
    display: grid;
  }
}
</style>


