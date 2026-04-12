<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import api from '@/api/client'
import ListPager from '@/components/ListPager.vue'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import PageHero from '@/components/shared/PageHero.vue'

interface ShopInfo {
  id: string
  name: string
  description?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  logo_url?: string | null
  rating?: number | null
  service_score?: number | null
  logistics_score?: number | null
  after_sales_score?: number | null
  shipping_city?: string | null
  featured_categories: string[]
  service_tags: string[]
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
  brand?: string
  model?: string
  sku_code?: string
  price: number
  original_price?: number | null
  rating?: number | null
  review_count: number
  monthly_sales: number
  ship_in_hours: number
  warranty_days: number
  tags: string[]
  spec_highlights: string[]
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

interface AddressListResponse {
  items: AddressItem[]
  total: number
  page: number
  page_size: number
}

interface MerchantProductListResponse {
  items: MerchantProduct[]
  total: number
  page: number
  page_size: number
}

interface MerchantOrderListResponse {
  items: MerchantOrder[]
  total: number
  page: number
  page_size: number
}

interface MerchantAfterSalesListResponse {
  items: MerchantAfterSalesItem[]
  total: number
  page: number
  page_size: number
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
const shippingAddresses = ref<AddressItem[]>([])
const addressPage = ref(1)
const addressPageSize = 6
const addressTotal = ref(0)
const products = ref<MerchantProduct[]>([])
const productPage = ref(1)
const productPageSize = 8
const productTotal = ref(0)
const orders = ref<MerchantOrder[]>([])
const orderPage = ref(1)
const orderPageSize = 6
const orderTotal = ref(0)
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
const afterSalesPage = ref(1)
const afterSalesPageSize = 6
const afterSalesTotal = ref(0)
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
  sku_code: '',
  brand: '',
  model: '',
  price: 0,
  original_price: 0,
  rating: 4.5,
  review_count: 0,
  monthly_sales: 0,
  ship_in_hours: 24,
  warranty_days: 365,
  stock: 0,
  image_url: '',
  description: '',
  tags: '',
  spec_highlights: ''
})

const shopForm = reactive({
  logo_url: '',
  description: '',
  contact_email: '',
  contact_phone: '',
  shipping_city: '',
  featured_categories: '',
  service_tags: ''
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
const addressTotalPages = computed(() => Math.max(1, Math.ceil(addressTotal.value / addressPageSize)))
const productTotalPages = computed(() => Math.max(1, Math.ceil(productTotal.value / productPageSize)))
const orderTotalPages = computed(() => Math.max(1, Math.ceil(orderTotal.value / orderPageSize)))
const afterSalesTotalPages = computed(() => Math.max(1, Math.ceil(afterSalesTotal.value / afterSalesPageSize)))

const splitMultiValue = (raw: string) =>
  raw
    .split(/\r?\n|,|，/)
    .map((item) => item.trim())
    .filter(Boolean)

const formatScore = (value?: number | null) => {
  const score = Number(value)
  return Number.isFinite(score) ? score.toFixed(1) : '-'
}

const formatShipHours = (value?: number | null) => {
  const hours = Number(value)
  if (!Number.isFinite(hours) || hours < 0) return '-'
  return hours === 0 ? '即时发货' : `${hours} 小时发货`
}

const fillShopForm = (value: ShopInfo | null) => {
  shopForm.logo_url = value?.logo_url || ''
  shopForm.description = value?.description || ''
  shopForm.contact_email = value?.contact_email || ''
  shopForm.contact_phone = value?.contact_phone || ''
  shopForm.shipping_city = value?.shipping_city || ''
  shopForm.featured_categories = (value?.featured_categories || []).join('，')
  shopForm.service_tags = (value?.service_tags || []).join('，')
}

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
  if (status === 'cancelled') return '已取消'
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
  fillShopForm(shop.value)
}

const loadAddresses = async (targetPage = addressPage.value) => {
  const response = await api.get<AddressListResponse>('/merchant/addresses', {
    params: { page: targetPage, page_size: addressPageSize }
  })
  addresses.value = response.data.items || []
  addressTotal.value = Number(response.data.total || 0)
  addressPage.value = Number(response.data.page || targetPage)
  const maxPage = Math.max(1, Math.ceil(addressTotal.value / addressPageSize))
  if (addressTotal.value > 0 && addressPage.value > maxPage) {
    await loadAddresses(maxPage)
  }
}

const loadShippingAddresses = async () => {
  const response = await api.get<AddressListResponse>('/merchant/addresses', {
    params: { page: 1, page_size: 100 }
  })
  shippingAddresses.value = response.data.items || []
}

const loadProducts = async (targetPage = productPage.value) => {
  const response = await api.get<MerchantProductListResponse>('/merchant/products', {
    params: { page: targetPage, page_size: productPageSize }
  })
  products.value = response.data.items || []
  productTotal.value = Number(response.data.total || 0)
  productPage.value = Number(response.data.page || targetPage)
  const maxPage = Math.max(1, Math.ceil(productTotal.value / productPageSize))
  if (productTotal.value > 0 && productPage.value > maxPage) {
    await loadProducts(maxPage)
  }
}

const loadOrders = async (targetPage = orderPage.value) => {
  const response = await api.get<MerchantOrderListResponse>('/merchant/orders', {
    params: {
      status_filter: orderFilter.value,
      page: targetPage,
      page_size: orderPageSize
    }
  })
  orders.value = response.data.items || []
  orderTotal.value = Number(response.data.total || 0)
  orderPage.value = Number(response.data.page || targetPage)
  const maxPage = Math.max(1, Math.ceil(orderTotal.value / orderPageSize))
  if (orderTotal.value > 0 && orderPage.value > maxPage) {
    await loadOrders(maxPage)
    return
  }
  const activeOrderIds = new Set(orders.value.map((item) => item.id))
  shippingSlowHintState.value = Object.fromEntries(
    Object.entries(shippingSlowHintState.value).filter(([orderId]) => activeOrderIds.has(orderId))
  )
  advancingSlowHintState.value = Object.fromEntries(
    Object.entries(advancingSlowHintState.value).filter(([orderId]) => activeOrderIds.has(orderId))
  )

  const map: Record<string, string> = {}
  for (const order of orders.value) {
    const defaultAddress = shippingAddresses.value.find((item) => item.is_default)
    if (defaultAddress) {
      map[order.id] = defaultAddress.id
    }
  }
  shipAddressByOrder.value = { ...shipAddressByOrder.value, ...map }
}

const loadAfterSales = async (targetPage = afterSalesPage.value) => {
  const response = await api.get<MerchantAfterSalesListResponse>('/merchant/after-sales', {
    params: {
      status_filter: afterSalesFilter.value,
      page: targetPage,
      page_size: afterSalesPageSize
    }
  })
  afterSalesItems.value = response.data.items || []
  afterSalesTotal.value = Number(response.data.total || 0)
  afterSalesPage.value = Number(response.data.page || targetPage)
  const maxPage = Math.max(1, Math.ceil(afterSalesTotal.value / afterSalesPageSize))
  if (afterSalesTotal.value > 0 && afterSalesPage.value > maxPage) {
    await loadAfterSales(maxPage)
  }
}

const loadAll = async () => {
  loading.value = true
  clearNotice()
  try {
    await loadShop()
    await loadAddresses()
    await loadShippingAddresses()
    await loadProducts()
    await loadOrders()
    await loadAfterSales()
  } catch (err: any) {
    error.value = parseErr(err, '商家控制台加载失败')
  } finally {
    loading.value = false
  }
}

watch(orderFilter, async () => {
  orderPage.value = 1
  if (!loading.value) {
    await loadOrders(1)
  }
})

watch(afterSalesFilter, async () => {
  afterSalesPage.value = 1
  if (!loading.value) {
    await loadAfterSales(1)
  }
})

const handleAddressPageChange = async (nextPage: number) => {
  await loadAddresses(nextPage)
}

const handleProductPageChange = async (nextPage: number) => {
  await loadProducts(nextPage)
}

const handleOrderPageChange = async (nextPage: number) => {
  await loadOrders(nextPage)
}

const handleAfterSalesPageChange = async (nextPage: number) => {
  await loadAfterSales(nextPage)
}

const createProduct = async () => {
  clearNotice()
  actionLoading.value = true
  try {
    await api.post('/merchant/products', {
      name: productForm.name,
      category: productForm.category || null,
      sku_code: productForm.sku_code || null,
      brand: productForm.brand || null,
      model: productForm.model || null,
      price: Number(productForm.price),
      original_price: Number(productForm.original_price) || null,
      rating: Number(productForm.rating),
      review_count: Number(productForm.review_count),
      monthly_sales: Number(productForm.monthly_sales),
      ship_in_hours: Number(productForm.ship_in_hours),
      warranty_days: Number(productForm.warranty_days),
      stock: Number(productForm.stock),
      image_url: productForm.image_url || null,
      description: productForm.description || null,
      tags: splitMultiValue(productForm.tags),
      spec_highlights: splitMultiValue(productForm.spec_highlights),
      is_active: true
    })
    success.value = '商品已上架'
    productForm.name = ''
    productForm.category = ''
    productForm.sku_code = ''
    productForm.brand = ''
    productForm.model = ''
    productForm.price = 0
    productForm.original_price = 0
    productForm.rating = 4.5
    productForm.review_count = 0
    productForm.monthly_sales = 0
    productForm.ship_in_hours = 24
    productForm.warranty_days = 365
    productForm.stock = 0
    productForm.image_url = ''
    productForm.description = ''
    productForm.tags = ''
    productForm.spec_highlights = ''
    productPage.value = 1
    await loadProducts(1)
  } catch (err: any) {
    error.value = parseErr(err, '商品上架失败')
  } finally {
    actionLoading.value = false
  }
}

const saveShopProfile = async () => {
  clearNotice()
  actionLoading.value = true
  try {
    const response = await api.patch('/merchant/shop', {
      logo_url: shopForm.logo_url || null,
      description: shopForm.description || null,
      contact_email: shopForm.contact_email || null,
      contact_phone: shopForm.contact_phone || null,
      shipping_city: shopForm.shipping_city || null,
      featured_categories: splitMultiValue(shopForm.featured_categories),
      service_tags: splitMultiValue(shopForm.service_tags)
    })
    shop.value = response.data
    fillShopForm(shop.value)
    success.value = '店铺资料已更新'
  } catch (err: any) {
    error.value = parseErr(err, '更新店铺资料失败')
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
    await loadProducts(productPage.value)
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
    addressPage.value = 1
    await loadAddresses(1)
    await loadShippingAddresses()
    await loadOrders(orderPage.value)
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
    await loadAddresses(addressPage.value)
    await loadShippingAddresses()
    await loadOrders(orderPage.value)
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
    await loadOrders(orderPage.value)
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
    await loadOrders(orderPage.value)
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
    await loadAfterSales(afterSalesPage.value)
    await loadOrders(orderPage.value)
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
        await Promise.all([
          loadProducts(productPage.value),
          loadOrders(orderPage.value),
          loadAfterSales(afterSalesPage.value)
        ])
        return
      }
      if (target === 'orders') {
        await loadOrders(orderPage.value)
        return
      }
      if (target === 'products') {
        await loadProducts(productPage.value)
        return
      }
      await loadAfterSales(afterSalesPage.value)
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

    <PageHero
      eyebrow="Merchant Workspace"
      :title="shopDisplay"
      description="把订单履约、商品维护、地址管理和售后处理收进同一块运营工作台，保持操作节奏与信息层级一致。"
      accent="gold"
    >
      <template #actions>
        <Badge v-if="shop" variant="default">评分 {{ formatScore(shop.rating) }}</Badge>
        <Badge v-if="shop" variant="info">物流 {{ formatScore(shop.logistics_score) }}</Badge>
        <Badge v-if="shop" variant="success">售后 {{ formatScore(shop.after_sales_score) }}</Badge>
      </template>
    </PageHero>

    <div class="tabs">
      <Button :variant="activeTab === 'orders' ? 'default' : 'outline'" size="sm" @click="activeTab = 'orders'">订单</Button>
      <Button :variant="activeTab === 'products' ? 'default' : 'outline'" size="sm" @click="activeTab = 'products'">商品</Button>
      <Button :variant="activeTab === 'addresses' ? 'default' : 'outline'" size="sm" @click="activeTab = 'addresses'">地址</Button>
      <Button :variant="activeTab === 'afterSales' ? 'default' : 'outline'" size="sm" @click="activeTab = 'afterSales'">售后</Button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="success" class="success">{{ success }}</p>

    <div v-if="loading" class="state-card">加载中...</div>

    <template v-else>
      <section v-if="activeTab === 'orders'" class="panel">
        <div class="panel-head">
          <h2>订单</h2>
          <div class="filter-row">
            <select v-model="orderFilter">
              <option value="pending_shipment">待发货</option>
              <option value="shipped">已发货</option>
              <option value="all">全部</option>
            </select>
            <button @click="loadOrders(orderPage)">刷新</button>
          </div>
        </div>

        <div class="list-surface">
          <div v-if="orders.length === 0" class="empty-shell">
            <p class="empty-shell-eyebrow">Order Queue</p>
            <h3>当前筛选下没有订单</h3>
            <p>列表壳层保持不变，后续有订单进入时会直接在这里延续显示和分页。</p>
          </div>

          <template v-else>
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
                  <option v-for="addr in shippingAddresses" :key="addr.id" :value="addr.id">
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

            <ListPager
              :page="orderPage"
              :total-pages="orderTotalPages"
              :total-items="orderTotal"
              @change="handleOrderPageChange"
            />
          </template>
        </div>
      </section>

      <section v-if="activeTab === 'afterSales'" class="panel">
        <div class="panel-head">
          <h2>售后处理</h2>
          <div class="filter-row">
            <select v-model="afterSalesFilter">
              <option value="open">进行中</option>
              <option value="submitted">待处理</option>
              <option value="merchant_approved">已同意</option>
              <option value="processing">处理中</option>
              <option value="merchant_rejected">已拒绝</option>
              <option value="completed">已完成</option>
              <option value="all">全部</option>
            </select>
            <button @click="loadAfterSales(afterSalesPage)">刷新</button>
          </div>
        </div>

        <div class="list-surface">
          <div v-if="afterSalesItems.length === 0" class="empty-shell">
            <p class="empty-shell-eyebrow">After Sales</p>
            <h3>当前没有售后申请</h3>
            <p>后续出现退换货请求时，会在当前面板中保持同样的布局和分页位置。</p>
          </div>

          <template v-else>
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

            <ListPager
              :page="afterSalesPage"
              :total-pages="afterSalesTotalPages"
              :total-items="afterSalesTotal"
              @change="handleAfterSalesPageChange"
            />
          </template>
        </div>
      </section>

      <section v-if="activeTab === 'products'" class="panel merchant-editor-panel">
        <div class="panel-head">
          <h2>店铺资料</h2>
          <div class="score-tags" v-if="shop">
            <span class="badge">评分 {{ formatScore(shop.rating) }}</span>
            <span class="badge">服务 {{ formatScore(shop.service_score) }}</span>
            <span class="badge">物流 {{ formatScore(shop.logistics_score) }}</span>
            <span class="badge">售后 {{ formatScore(shop.after_sales_score) }}</span>
          </div>
        </div>
        <div v-if="shop" class="shop-meta">
          <article class="shop-meta-card">
            <strong>{{ shop.shipping_city || '未设置发货城市' }}</strong>
            <p class="muted">发货城市</p>
          </article>
          <article class="shop-meta-card">
            <strong>{{ shop.featured_categories?.length ? shop.featured_categories.join(' / ') : '未设置主营类目' }}</strong>
            <p class="muted">主营类目</p>
          </article>
          <article class="shop-meta-card">
            <strong>{{ shop.service_tags?.length ? shop.service_tags.join(' / ') : '未设置服务标签' }}</strong>
            <p class="muted">服务标签</p>
          </article>
        </div>
        <article class="editor-card">
          <div class="editor-intro">
            <div>
              <h3>店铺资料编辑</h3>
              <p class="muted">核心信息直接展示给买家，高级信息折叠收起，减少误填。</p>
            </div>
            <span class="editor-tip">多值字段支持中文逗号 / 英文逗号 / 换行</span>
          </div>
          <form class="merchant-editor-form" @submit.prevent="saveShopProfile">
            <section class="form-block">
              <div class="block-head">
                <h4>核心信息</h4>
                <p>用于店铺页展示、商品详情页展示和物流预期提示。</p>
              </div>
              <div class="form-grid">
                <label class="field-card">
                  <span class="field-label">联系邮箱</span>
                  <span class="field-help">售后、订单异常或客服回访时使用，例如 `support@example.com`。</span>
                  <input v-model="shopForm.contact_email" type="email" placeholder="support@example.com">
                </label>
                <label class="field-card">
                  <span class="field-label">联系电话</span>
                  <span class="field-help">建议填写买家可联系到的店铺电话，例如 `400-800-1234`。</span>
                  <input v-model="shopForm.contact_phone" placeholder="400-800-1234">
                </label>
                <label class="field-card">
                  <span class="field-label">发货城市</span>
                  <span class="field-help">会在商品列表和详情页直接展示，例如 `杭州`、`深圳`。</span>
                  <input v-model="shopForm.shipping_city" placeholder="杭州">
                </label>
                <label class="field-card field-card-wide">
                  <span class="field-label">店铺简介</span>
                  <span class="field-help">一句话说明主营方向、服务承诺或品牌定位，建议 20-80 字。</span>
                  <textarea
                    v-model="shopForm.description"
                    rows="3"
                    placeholder="例如：专注办公数码与企业采购，支持正规发票与次日出库。"
                  ></textarea>
                </label>
              </div>
            </section>

            <details class="advanced-panel">
              <summary>高级店铺信息</summary>
              <div class="advanced-body">
                <div class="form-grid">
                  <label class="field-card">
                    <span class="field-label">店铺 Logo URL</span>
                    <span class="field-help">可选，用于品牌识别与视觉展示。</span>
                    <input v-model="shopForm.logo_url" placeholder="https://example.com/logo.png">
                  </label>
                  <label class="field-card field-card-wide">
                    <span class="field-label">主营类目</span>
                    <span class="field-help">支持中文逗号、英文逗号或换行分隔。</span>
                    <span class="field-example">示例：显示器，办公电脑，键鼠套装</span>
                    <textarea v-model="shopForm.featured_categories" rows="3" placeholder="显示器，办公电脑，键鼠套装"></textarea>
                  </label>
                  <label class="field-card field-card-wide">
                    <span class="field-label">服务标签</span>
                    <span class="field-help">建议填写买家最关心的履约承诺与服务能力。</span>
                    <span class="field-example">示例：次日达，官方质保，企业采购，7 天无理由</span>
                    <textarea v-model="shopForm.service_tags" rows="3" placeholder="次日达，官方质保，企业采购"></textarea>
                  </label>
                </div>
              </div>
            </details>

            <div class="form-actions">
              <button :disabled="actionLoading" type="submit">保存店铺资料</button>
            </div>
          </form>
        </article>

        <article class="editor-card">
          <div class="editor-intro">
            <div>
              <h3>商品录入</h3>
              <p class="muted">先录入影响上架与履约的核心字段，高级字段按需补充，用于比较展示与推荐。</p>
            </div>
            <span class="editor-tip">SKU、本地库存与发货时效建议优先维护</span>
          </div>
          <form class="merchant-editor-form" @submit.prevent="createProduct">
            <section class="form-block">
              <div class="block-head">
                <h4>核心字段</h4>
                <p>这些信息直接决定商品是否易于识别、下单与履约。</p>
              </div>
              <div class="form-grid">
                <label class="field-card">
                  <span class="field-label">商品名称</span>
                  <span class="field-help">建议包含品类、系列或关键规格，例如 `27 英寸 4K 办公显示器`。</span>
                  <input v-model="productForm.name" required placeholder="27 英寸 4K 办公显示器">
                </label>
                <label class="field-card">
                  <span class="field-label">分类</span>
                  <span class="field-help">用于商品筛选与归类，例如 `显示器`、`笔记本电脑`。</span>
                  <input v-model="productForm.category" placeholder="显示器">
                </label>
                <label class="field-card">
                  <span class="field-label">SKU 编码</span>
                  <span class="field-help">便于内部管理与检索，支持字母、数字和短横线。</span>
                  <input v-model="productForm.sku_code" placeholder="OFFICE-27-4K-001">
                </label>
                <label class="field-card">
                  <span class="field-label">售价</span>
                  <span class="field-help">买家实际下单价格。</span>
                  <input v-model.number="productForm.price" min="0" step="0.01" type="number" required placeholder="1999">
                </label>
                <label class="field-card">
                  <span class="field-label">库存</span>
                  <span class="field-help">当前可售库存，缺货时会直接影响购买按钮状态。</span>
                  <input v-model.number="productForm.stock" min="0" step="1" type="number" required placeholder="120">
                </label>
                <label class="field-card">
                  <span class="field-label">发货时效（小时）</span>
                  <span class="field-help">例如 `24` 表示 24 小时内发货，`0` 表示即时发货。</span>
                  <input v-model.number="productForm.ship_in_hours" min="0" step="1" type="number" placeholder="24">
                </label>
                <label class="field-card field-card-wide">
                  <span class="field-label">图片 URL</span>
                  <span class="field-help">建议使用稳定可访问的主图地址。</span>
                  <input v-model="productForm.image_url" placeholder="https://example.com/product-cover.jpg">
                </label>
                <label class="field-card field-card-wide">
                  <span class="field-label">商品描述</span>
                  <span class="field-help">一句话说明定位、适用场景或核心卖点，建议 30-120 字。</span>
                  <textarea
                    v-model="productForm.description"
                    rows="3"
                    placeholder="例如：面向日常办公与轻度设计，支持 Type-C 一线连接与低蓝光护眼。"
                  ></textarea>
                </label>
              </div>
            </section>

            <details class="advanced-panel">
              <summary>高级商品信息</summary>
              <div class="advanced-body">
                <div class="form-grid">
                  <label class="field-card">
                    <span class="field-label">品牌</span>
                    <span class="field-help">用于商品比较与品牌筛选。</span>
                    <input v-model="productForm.brand" placeholder="Acer">
                  </label>
                  <label class="field-card">
                    <span class="field-label">型号</span>
                    <span class="field-help">建议填写官方型号，便于买家对比。</span>
                    <input v-model="productForm.model" placeholder="VG270K">
                  </label>
                  <label class="field-card">
                    <span class="field-label">原价</span>
                    <span class="field-help">用于展示优惠力度，可留空。</span>
                    <input v-model.number="productForm.original_price" min="0" step="0.01" type="number" placeholder="2399">
                  </label>
                  <label class="field-card">
                    <span class="field-label">评分</span>
                    <span class="field-help">范围 0-5，例如 `4.7`。</span>
                    <input v-model.number="productForm.rating" min="0" max="5" step="0.1" type="number" placeholder="4.7">
                  </label>
                  <label class="field-card">
                    <span class="field-label">评价数</span>
                    <span class="field-help">已有评价条数，用于口碑展示。</span>
                    <input v-model.number="productForm.review_count" min="0" step="1" type="number" placeholder="385">
                  </label>
                  <label class="field-card">
                    <span class="field-label">月销量</span>
                    <span class="field-help">用于销量排序与推荐展示。</span>
                    <input v-model.number="productForm.monthly_sales" min="0" step="1" type="number" placeholder="268">
                  </label>
                  <label class="field-card">
                    <span class="field-label">保修天数</span>
                    <span class="field-help">例如 `365` 表示一年保修。</span>
                    <input v-model.number="productForm.warranty_days" min="0" step="1" type="number" placeholder="365">
                  </label>
                  <label class="field-card field-card-wide">
                    <span class="field-label">标签</span>
                    <span class="field-help">支持中文逗号、英文逗号或换行分隔。</span>
                    <span class="field-example">示例：低蓝光，Type-C，升降支架，办公推荐</span>
                    <textarea v-model="productForm.tags" rows="3" placeholder="低蓝光，Type-C，升降支架"></textarea>
                  </label>
                  <label class="field-card field-card-wide">
                    <span class="field-label">核心参数</span>
                    <span class="field-help">建议拆成 3-6 个短条目，方便详情页展示。</span>
                    <span class="field-example">示例：27 英寸 4K，IPS 面板，65W 反向供电</span>
                    <textarea v-model="productForm.spec_highlights" rows="3" placeholder="27 英寸 4K，IPS 面板，65W 反向供电"></textarea>
                  </label>
                </div>
              </div>
            </details>

            <div class="form-actions">
              <button :disabled="actionLoading" type="submit">上架商品</button>
            </div>
          </form>
        </article>

        <div class="list-block">
          <div class="list-block-head">
            <h3>商品列表</h3>
            <span class="list-meta">共 {{ productTotal }} 个商品</span>
          </div>
          <div class="list-surface">
            <div v-if="products.length === 0" class="empty-shell">
              <p class="empty-shell-eyebrow">Product Shelf</p>
              <h3>当前还没有商品</h3>
              <p>上架后的商品会直接进入同一块列表区域，避免表单区与列表区在空态和有内容时视觉断层。</p>
            </div>

            <template v-else>
              <div class="table-list">
                <article v-for="item in products" :key="item.id" class="product-row">
                  <div>
                    <strong>{{ item.name }}</strong>
                    <p class="muted">{{ item.brand || '未设品牌' }} {{ item.model || '' }} · SKU {{ item.sku_code || '-' }}</p>
                    <p class="muted">评分 {{ formatScore(item.rating) }} · 月销 {{ item.monthly_sales }} · {{ formatShipHours(item.ship_in_hours) }}</p>
                    <p class="muted" v-if="item.spec_highlights?.length">{{ item.spec_highlights.join(' / ') }}</p>
                    <p class="muted" v-if="item.tags?.length">{{ item.tags.join(' / ') }}</p>
                    <p class="muted">{{ item.category || '未分类' }} · 库存 {{ item.stock }} · ¥ {{ item.price.toFixed(2) }}</p>
                    <p class="muted">保修 {{ item.warranty_days }} 天<span v-if="item.original_price && item.original_price > item.price"> · 原价 ¥ {{ item.original_price.toFixed(2) }}</span></p>
                  </div>
                  <button :disabled="actionLoading" @click="toggleProductActive(item)">
                    {{ item.is_active ? '下架' : '上架' }}
                  </button>
                </article>
              </div>

              <ListPager
                :page="productPage"
                :total-pages="productTotalPages"
                :total-items="productTotal"
                @change="handleProductPageChange"
              />
            </template>
          </div>
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

        <div class="list-block">
          <div class="list-block-head">
            <h3>地址列表</h3>
            <span class="list-meta">共 {{ addressTotal }} 个地址</span>
          </div>
          <div class="list-surface">
            <div v-if="addresses.length === 0" class="empty-shell">
              <p class="empty-shell-eyebrow">Address Book</p>
              <h3>当前还没有发货地址</h3>
              <p>新增地址后会直接补齐到当前面板中，发货订单也会继续复用这里的地址选择。</p>
            </div>

            <template v-else>
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

              <ListPager
                :page="addressPage"
                :total-pages="addressTotalPages"
                :total-items="addressTotal"
                @change="handleAddressPageChange"
              />
            </template>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.merchant-page {
  display: grid;
  gap: 16px;
}

.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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

.list-block {
  display: grid;
  gap: 10px;
}

.list-block-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.list-block-head h3 {
  margin: 0;
  color: #312819;
}

.list-meta {
  color: #7c6a4d;
  font-size: 13px;
}

.list-surface {
  min-height: 260px;
  border: 1px solid #eadbc1;
  border-radius: 16px;
  padding: 14px;
  background: linear-gradient(180deg, #fffdf8 0%, #fff7ea 100%);
  display: grid;
  gap: 10px;
  align-content: start;
}

.empty-shell {
  min-height: 230px;
  border-radius: 14px;
  border: 1px dashed #dbc8aa;
  background: rgba(255, 252, 245, 0.9);
  display: grid;
  place-items: center;
  text-align: center;
  padding: 28px 20px;
}

.empty-shell-eyebrow {
  margin: 0 0 6px;
  color: #9a6c2c;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 11px;
}

.empty-shell h3 {
  margin: 0;
  color: #3c2d14;
}

.empty-shell p:last-child {
  margin: 8px 0 0;
  color: #6f6657;
  line-height: 1.7;
}

.score-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.shop-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.shop-meta-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  background: #fffcf6;
  display: grid;
  gap: 4px;
}

.shop-meta-card strong {
  color: #3f3017;
  font-size: 14px;
  line-height: 1.5;
}

.merchant-editor-panel {
  gap: 14px;
}

.editor-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  background: #fffdf7;
  display: grid;
  gap: 14px;
}

.editor-intro {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.editor-intro h3 {
  margin: 0 0 4px;
  color: #312819;
}

.editor-tip {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #f5ecda;
  color: #6b5128;
  font-size: 12px;
  white-space: nowrap;
}

.merchant-editor-form {
  display: grid;
  gap: 12px;
}

.form-block {
  display: grid;
  gap: 10px;
}

.block-head h4 {
  margin: 0 0 4px;
  color: #3f3017;
}

.block-head p {
  margin: 0;
  color: #6f6657;
  font-size: 13px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.field-card {
  border: 1px solid #eadbc1;
  border-radius: 12px;
  padding: 12px;
  background: linear-gradient(180deg, #fffdf8 0%, #fff8eb 100%);
  display: grid;
  gap: 8px;
}

.field-card-wide {
  grid-column: 1 / -1;
}

.field-label {
  color: #41331b;
  font-size: 14px;
  font-weight: 700;
}

.field-help,
.field-example {
  color: #6f6657;
  font-size: 12px;
  line-height: 1.5;
}

.field-example {
  color: #87602b;
}

.advanced-panel {
  border: 1px solid #e5d8bf;
  border-radius: 12px;
  background: #fff8ed;
  overflow: hidden;
}

.advanced-panel summary {
  cursor: pointer;
  list-style: none;
  background: #fcf2df;
  color: #4d3a18;
  font-weight: 700;
}

.advanced-panel summary::-webkit-details-marker {
  display: none;
}

.advanced-body {
  padding: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
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
.merchant-editor-form input,
.merchant-editor-form textarea,
.merchant-editor-form button,
.advanced-panel summary,
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
.merchant-editor-form button,
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
  min-height: 160px;
  background: linear-gradient(180deg, #fffdf8 0%, #fff7ea 100%);
  border: 1px dashed #d7c9af;
  text-align: center;
  display: grid;
  place-items: center;
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
  .form-grid,
  .grid-form {
    grid-template-columns: 1fr;
  }

  .editor-intro,
  .shop-meta,
  .ship-row,
  .product-row,
  .address-row,
  .panel-head,
  .list-block-head {
    grid-template-columns: 1fr;
    display: grid;
  }

  .editor-tip {
    white-space: normal;
  }
}
</style>

