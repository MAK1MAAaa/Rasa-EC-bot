<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'

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

interface MerchantAfterSalesBrief {
  id: string
  order_id: string
  type: string
  reason?: string | null
  status: string
  created_at: string
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
  after_sales: MerchantAfterSalesBrief[]
}

interface MerchantAfterSalesItem {
  id: string
  order_id: string
  type: string
  reason?: string | null
  status: string
  created_at: string
  order_status: string
  contact_email: string
  order_link: string
}

type TabKey = 'orders' | 'products' | 'addresses' | 'afterSales'
type ToastKind = 'success' | 'error'
type AfterSalesFilter = 'open' | 'submitted' | 'merchant_approved' | 'processing' | 'merchant_rejected' | 'completed' | 'all'

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
const advancingLogisticsState = ref<Record<string, boolean>>({})
const shippingSlowHintState = ref<Record<string, boolean>>({})
const advancingSlowHintState = ref<Record<string, boolean>>({})
const slowHintTimers = ref<Record<string, ReturnType<typeof setTimeout>>>({})
const SLOW_HINT_DELAY_MS = 1200
const SLOW_SHIPMENT_HOURS = 24

const afterSalesItems = ref<MerchantAfterSalesItem[]>([])
const afterSalesFilter = ref<AfterSalesFilter>('open')
const afterSalesActionState = ref<Record<string, boolean>>({})

const pageToast = ref<{ visible: boolean; type: ToastKind; message: string }>({
  visible: false,
  type: 'success',
  message: ''
})
let pageToastTimer: ReturnType<typeof setTimeout> | null = null
let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

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

const showToast = (type: ToastKind, message: string) => {
  if (pageToastTimer) {
    clearTimeout(pageToastTimer)
  }
  pageToast.value = { visible: true, type, message }
  pageToastTimer = setTimeout(() => {
    pageToast.value.visible = false
  }, 2600)
}

const isShippingOrder = (orderId: string) => !!shippingOrderState.value[orderId]
const isAdvancingLogistics = (orderId: string) => !!advancingLogisticsState.value[orderId]
const isAfterSalesActing = (requestId: string) => !!afterSalesActionState.value[requestId]
const isSlowShipment = (order: MerchantOrder) => {
  if (order.status !== 'pending_shipment') return false
  const createdAtMs = new Date(order.created_at).getTime()
  if (!Number.isFinite(createdAtMs)) return false
  const hours = (Date.now() - createdAtMs) / (1000 * 60 * 60)
  return hours >= SLOW_SHIPMENT_HOURS
}

const pendingHoursLabel = (createdAt: string) => {
  const createdAtMs = new Date(createdAt).getTime()
  if (!Number.isFinite(createdAtMs)) return '-'
  const hours = Math.max(0, Math.floor((Date.now() - createdAtMs) / (1000 * 60 * 60)))
  if (hours >= 24) {
    const days = Math.floor(hours / 24)
    const rest = hours % 24
    return `${days}d ${rest}h`
  }
  return `${hours}h`
}

const clearSlowHintTimer = (timerKey: string) => {
  const timer = slowHintTimers.value[timerKey]
  if (timer) {
    clearTimeout(timer)
    delete slowHintTimers.value[timerKey]
  }
}

const startSlowHintTimer = (
  timerKey: string,
  targetState: { value: Record<string, boolean> },
  orderId: string,
  messageWhenDone = true
) => {
  clearSlowHintTimer(timerKey)
  targetState.value[orderId] = false
  slowHintTimers.value[timerKey] = setTimeout(() => {
    if (messageWhenDone) {
      targetState.value[orderId] = true
    }
    delete slowHintTimers.value[timerKey]
  }, SLOW_HINT_DELAY_MS)
}

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

const orderStatusLabel = (status: string) => {
  if (status === 'pending_shipment') return '待发货'
  if (status === 'shipped') return '已发货'
  return status
}

const logisticsStatusLabel = (status: string) => {
  if (status === 'in_transit') return '运输中'
  if (status === 'delivered') return '已送达'
  return status || '-'
}

const afterSalesTypeLabel = (type: string) => {
  if (type === 'return') return '退货'
  if (type === 'exchange') return '换货'
  return type
}

const afterSalesStatusLabel = (status: string) => {
  if (status === 'submitted') return '待处理'
  if (status === 'merchant_approved') return '已同意'
  if (status === 'processing') return '处理中'
  if (status === 'merchant_rejected') return '已拒绝'
  if (status === 'completed') return '已完成'
  if (status === 'cancelled') return '已取消'
  return status
}

const afterSalesActions = (item: MerchantAfterSalesItem) => {
  if (item.status === 'submitted') {
    return [
      { key: 'approve', label: '同意' },
      { key: 'reject', label: '驳回' }
    ]
  }
  if (item.status === 'merchant_approved') {
    return [
      { key: 'processing', label: '处理中' },
      { key: 'complete', label: '完成' }
    ]
  }
  if (item.status === 'processing') {
    return [{ key: 'complete', label: '完成' }]
  }
  return []
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
  orders.value = response.data.items || []
  const activeOrderIds = new Set(orders.value.map((item) => item.id))
  shippingSlowHintState.value = Object.fromEntries(
    Object.entries(shippingSlowHintState.value).filter(([orderId]) => activeOrderIds.has(orderId))
  )
  advancingSlowHintState.value = Object.fromEntries(
    Object.entries(advancingSlowHintState.value).filter(([orderId]) => activeOrderIds.has(orderId))
  )

  const map: Record<string, string> = {}
  for (const order of orders.value) {
    const defaultAddress = addresses.value.find((item) => item.is_default)
    if (defaultAddress) {
      map[order.id] = defaultAddress.id
    }
  }
  shipAddressByOrder.value = { ...shipAddressByOrder.value, ...map }
}

const loadAfterSales = async () => {
  const response = await api.get('/merchant/after-sales', {
    params: { status_filter: afterSalesFilter.value }
  })
  afterSalesItems.value = response.data.items || []
}

const loadAll = async () => {
  loading.value = true
  clearNotice()
  try {
    await loadShop()
    await loadAddresses()
    await loadProducts()
    await loadOrders()
    await loadAfterSales()
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

  startSlowHintTimer(`ship:${order.id}`, shippingSlowHintState, order.id)
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
    showToast('success', `订单 ${order.id} 已发货`)
    await loadOrders()
  } catch (err: any) {
    showToast('error', parseErr(err, '发货失败'))
  } finally {
    clearSlowHintTimer(`ship:${order.id}`)
    shippingSlowHintState.value[order.id] = false
    shippingOrderState.value[order.id] = false
  }
}

const advanceLogistics = async (order: MerchantOrder) => {
  if (isAdvancingLogistics(order.id)) {
    return
  }
  startSlowHintTimer(`advance:${order.id}`, advancingSlowHintState, order.id)
  advancingLogisticsState.value[order.id] = true
  try {
    await api.post(`/merchant/orders/${order.id}/logistics/advance`)
    showToast('success', `订单 ${order.id} 物流已推进到下一站`)
    await loadOrders()
  } catch (err: any) {
    showToast('error', parseErr(err, '推进物流失败'))
  } finally {
    clearSlowHintTimer(`advance:${order.id}`)
    advancingSlowHintState.value[order.id] = false
    advancingLogisticsState.value[order.id] = false
  }
}

const handleAfterSales = async (item: MerchantAfterSalesItem, action: string) => {
  if (isAfterSalesActing(item.id)) {
    return
  }
  afterSalesActionState.value[item.id] = true
  try {
    await api.patch(`/merchant/after-sales/${item.id}`, { action })
    showToast('success', `售后 ${item.order_id} 已更新`)
    await loadAfterSales()
    await loadOrders()
  } catch (err: any) {
    showToast('error', parseErr(err, '售后处理失败'))
  } finally {
    afterSalesActionState.value[item.id] = false
  }
}

const scheduleRealtimeRefresh = (target: 'orders' | 'products' | 'after_sales' | 'all') => {
  if (realtimeRefreshTimer) {
    return
  }
  realtimeRefreshTimer = setTimeout(async () => {
    realtimeRefreshTimer = null
    try {
      if (target === 'all') {
        await Promise.all([loadProducts(), loadOrders(), loadAfterSales()])
        return
      }
      if (target === 'orders') {
        await loadOrders()
        return
      }
      if (target === 'products') {
        await loadProducts()
        return
      }
      await loadAfterSales()
    } catch {
      // Keep current page responsive even if one realtime refresh fails.
    }
  }, 320)
}

const handleRealtimeEvent = (event: RealtimeEvent) => {
  const eventShopId = typeof event.data?.shop_id === 'string' ? event.data.shop_id : ''
  if (eventShopId && shop.value?.id && eventShopId !== shop.value.id) {
    return
  }
  if (event.event === 'inventory_changed') {
    scheduleRealtimeRefresh(activeTab.value === 'products' ? 'products' : 'all')
    return
  }
  if (event.event === 'order_changed') {
    scheduleRealtimeRefresh(activeTab.value === 'orders' ? 'orders' : 'all')
    return
  }
  if (event.event === 'after_sales_changed') {
    scheduleRealtimeRefresh(activeTab.value === 'afterSales' ? 'after_sales' : 'all')
  }
}

onMounted(async () => {
  await loadAll()
  realtimeClient = createRealtimeClient({
    token: authStore.token,
    onEvent: handleRealtimeEvent
  })
})
onBeforeUnmount(() => {
  for (const timerKey of Object.keys(slowHintTimers.value)) {
    clearSlowHintTimer(timerKey)
  }
  if (pageToastTimer) {
    clearTimeout(pageToastTimer)
    pageToastTimer = null
  }
  if (realtimeRefreshTimer) {
    clearTimeout(realtimeRefreshTimer)
    realtimeRefreshTimer = null
  }
  realtimeClient?.close()
  realtimeClient = null
})
</script>

<template>
  <section class="merchant-page">
    <transition name="toast-fade">
      <div v-if="pageToast.visible" class="ship-toast" :class="pageToast.type">
        {{ pageToast.message }}
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
      <button :class="activeTab === 'afterSales' ? 'active' : ''" @click="activeTab = 'afterSales'">售后</button>
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
            <div class="order-meta">
              <span class="status">{{ orderStatusLabel(order.status) }}</span>
              <span
                v-if="order.status === 'pending_shipment'"
                :class="['age-badge', { 'is-slow': isSlowShipment(order) }]"
              >
                待处理 {{ pendingHoursLabel(order.created_at) }}
              </span>
            </div>
          </div>
          <p class="muted">收货地址：{{ order.address }}</p>
          <p class="muted">售后申请：{{ order.after_sales?.length || 0 }} 条</p>

          <ul class="items">
            <li v-for="item in order.items" :key="item.id">
              <a :href="`/products/${item.product_id}`" target="_blank">{{ item.product_name }}</a>
              <span>x {{ item.quantity }}</span>
              <strong>¥ {{ item.subtotal.toFixed(2) }}</strong>
            </li>
          </ul>

          <div class="chips" v-if="order.after_sales && order.after_sales.length > 0">
            <span class="badge" v-for="asItem in order.after_sales" :key="asItem.id">
              {{ afterSalesTypeLabel(asItem.type) }} · {{ afterSalesStatusLabel(asItem.status) }}
            </span>
          </div>

          <div class="ship-row" v-if="order.status === 'pending_shipment'">
            <select v-model="shipAddressByOrder[order.id]">
              <option value="">默认发货地址</option>
              <option v-for="addr in addresses" :key="addr.id" :value="addr.id">
                {{ addr.label }} · {{ addr.province }}{{ addr.city }}{{ addr.district }}{{ addr.address_line }}
              </option>
            </select>
            <button
              :class="{ 'btn-busy': isShippingOrder(order.id) }"
              :disabled="actionLoading || isShippingOrder(order.id)"
              @click="shipOrder(order)"
            >
              <span v-if="isShippingOrder(order.id)" class="cute-loader" aria-hidden="true"></span>
              <span>{{ isShippingOrder(order.id) ? '发货中...' : '发货' }}</span>
            </button>
            <p v-if="shippingSlowHintState[order.id]" class="slow-hint">正在联系仓库并同步物流，请稍候...</p>
            <div v-if="isShippingOrder(order.id)" class="slow-skeleton"></div>
          </div>

          <div v-if="order.logistics" class="logistics">
            <p><strong>运单号：</strong>{{ order.logistics.tracking_no || '待生成' }}</p>
            <p><strong>物流状态：</strong>{{ logisticsStatusLabel(order.logistics.status) }}</p>
            <p><strong>当前位置：</strong>{{ order.logistics.current_location || '-' }}</p>
            <p><strong>预计送达：</strong>{{ order.logistics.estimated_delivery_at ? new Date(order.logistics.estimated_delivery_at).toLocaleString() : '-' }}</p>
            <p><strong>途径：</strong>{{ (order.logistics.route_plan || []).join(' -> ') || '-' }}</p>
            <div class="logistics-actions">
              <button
                :class="{ 'btn-busy': isAdvancingLogistics(order.id) }"
                :disabled="actionLoading || isAdvancingLogistics(order.id) || order.logistics.status === 'delivered'"
                @click="advanceLogistics(order)"
              >
                <span v-if="isAdvancingLogistics(order.id)" class="cute-loader" aria-hidden="true"></span>
                <span>{{ isAdvancingLogistics(order.id) ? '推进中...' : (order.logistics.status === 'delivered' ? '已送达' : '推进到下一站') }}</span>
              </button>
              <p v-if="advancingSlowHintState[order.id]" class="slow-hint">正在同步下一站轨迹，请稍候...</p>
            </div>
          </div>
        </article>
      </section>

      <section v-if="activeTab === 'afterSales'" class="panel">
        <div class="panel-head">
          <h2>售后处理</h2>
          <div class="filter-row">
            <select v-model="afterSalesFilter" @change="loadAfterSales">
              <option value="open">进行中</option>
              <option value="submitted">待处理</option>
              <option value="merchant_approved">已同意</option>
              <option value="processing">处理中</option>
              <option value="merchant_rejected">已拒绝</option>
              <option value="completed">已完成</option>
              <option value="all">全部</option>
            </select>
            <button @click="loadAfterSales">刷新</button>
          </div>
        </div>

        <div v-if="afterSalesItems.length === 0" class="state-card">暂无售后申请</div>

        <article v-for="item in afterSalesItems" :key="item.id" class="after-sales-row">
          <div class="row">
            <strong>{{ item.order_id }}</strong>
            <span class="status">{{ afterSalesStatusLabel(item.status) }}</span>
          </div>
          <p class="muted">{{ afterSalesTypeLabel(item.type) }} · 下单邮箱 {{ item.contact_email }}</p>
          <p class="muted">{{ new Date(item.created_at).toLocaleString() }}</p>
          <p class="reason">{{ item.reason || '无说明' }}</p>
          <a class="order-link" :href="item.order_link" target="_blank">查看订单</a>

          <div class="action-row" v-if="afterSalesActions(item).length > 0">
            <button
              v-for="action in afterSalesActions(item)"
              :key="action.key"
              :disabled="isAfterSalesActing(item.id)"
              @click="handleAfterSales(item, action.key)"
            >
              {{ isAfterSalesActing(item.id) ? '处理中...' : action.label }}
            </button>
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
.action-row button,
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
.action-row button,
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
.after-sales-row,
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
  gap: 8px;
}

.order-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status,
.badge {
  background: #f1dfbd;
  color: #594523;
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.age-badge {
  background: #fdf3e2;
  border: 1px solid #f2d6a3;
  color: #5b3e16;
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.age-badge.is-slow {
  background: #fff1f2;
  border-color: #fda4af;
  color: #9f1239;
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

.items a,
.order-link {
  color: #60431a;
  text-decoration: none;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ship-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.ship-row .slow-hint,
.ship-row .slow-skeleton {
  grid-column: 1 / -1;
}

.logistics {
  border-top: 1px dashed #d6c7ad;
  padding-top: 8px;
  color: #4f4538;
}

.logistics-actions {
  margin-top: 8px;
}

.logistics-actions .slow-hint {
  margin-top: 6px;
}

.logistics-actions button {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  background: #315f58;
  color: #f2fff8;
}

.btn-busy {
  opacity: 0.95;
}

.cute-loader {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: #fff;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
  animation: spin-loader 0.8s linear infinite;
  vertical-align: middle;
}

.slow-hint {
  margin: 0;
  color: #6e5f45;
  font-size: 12px;
}

.slow-skeleton {
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, #f6ede0 25%, #fff8eb 45%, #f6ede0 65%);
  background-size: 280% 100%;
  animation: ship-shimmer 1.2s linear infinite;
}

@keyframes spin-loader {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes ship-shimmer {
  from {
    background-position: 100% 0;
  }
  to {
    background-position: 0 0;
  }
}

.reason {
  margin: 0;
  color: #4c4234;
  white-space: pre-wrap;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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

