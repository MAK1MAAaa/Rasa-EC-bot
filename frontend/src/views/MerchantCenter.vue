<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import api from '@/api/client'
import ListPager from '@/components/ListPager.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Checkbox from '@/components/ui/Checkbox.vue'
import PageHero from '@/components/shared/PageHero.vue'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'
import { Package2 } from 'lucide-vue-next'

interface ShopInfo { id: string; name: string; description?: string | null; contact_email?: string | null; contact_phone?: string | null; logo_url?: string | null; rating?: number | null; service_score?: number | null; logistics_score?: number | null; after_sales_score?: number | null; shipping_city?: string | null; featured_categories: string[]; service_tags: string[] }
interface AddressItem { id: string; shop_id: string; label: string; contact_name: string; contact_phone: string; province: string; city: string; district: string; address_line: string; postal_code?: string | null; is_default: boolean }
interface MerchantProduct { id: string; shop_id: string; shop_name: string; name: string; description?: string; image_url?: string; category?: string; brand?: string; model?: string; sku_code?: string; price: number; original_price?: number | null; rating?: number | null; review_count: number; monthly_sales: number; ship_in_hours: number; warranty_days: number; tags: string[]; spec_highlights: string[]; stock: number; is_active: boolean }
interface MerchantOrderItem { id: string; product_id: string; product_name: string; quantity: number; subtotal: number; product_link: string }
interface MerchantLogistics { tracking_no?: string | null; status: string; current_location?: string | null; estimated_delivery_at?: string | null; route_plan: string[] }
interface MerchantAfterSalesBrief { id: string; order_id: string; type: string; reason?: string | null; status: string; created_at: string }
interface MerchantOrder { id: string; status: string; address: string; contact_email: string; total_amount: number; created_at: string; items: MerchantOrderItem[]; logistics?: MerchantLogistics | null; after_sales: MerchantAfterSalesBrief[] }
interface MerchantAfterSalesItem { id: string; order_id: string; type: string; reason?: string | null; status: string; created_at: string; order_status: string; contact_email: string; order_link: string }
interface Paged<T> { items: T[]; total: number; page: number; page_size: number }
interface ProductForm { name: string; category: string; sku_code: string; brand: string; model: string; price: number; original_price: number; rating: number; review_count: number; monthly_sales: number; ship_in_hours: number; warranty_days: number; stock: number; image_url: string; description: string; tags: string; spec_highlights: string; is_active: boolean }
interface AddressForm { label: string; contact_name: string; contact_phone: string; province: string; city: string; district: string; address_line: string; postal_code: string; is_default: boolean }

type TabKey = 'workspace' | 'productManage' | 'productCreate' | 'shopProfile' | 'addressManage'
type ToastKind = 'success' | 'error'
type OrderFilter = 'pending_shipment' | 'shipped' | 'all'
type AfterSalesFilter = 'open' | 'submitted' | 'merchant_approved' | 'processing' | 'merchant_rejected' | 'completed' | 'all'

const authStore = useAuthStore()
const activeTab = ref<TabKey>('workspace')
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
const productKeyword = ref('')
const productSelection = ref<Record<string, boolean>>({})
const editingProductId = ref<string | null>(null)

const orders = ref<MerchantOrder[]>([])
const orderPage = ref(1)
const orderPageSize = 6
const orderTotal = ref(0)
const orderFilter = ref<OrderFilter>('pending_shipment')
const orderSectionLoading = ref(false)
const shipAddressByOrder = ref<Record<string, string>>({})
const shippingOrderState = ref<Record<string, boolean>>({})
const advancingLogisticsState = ref<Record<string, boolean>>({})
const shippingSlowHintState = ref<Record<string, boolean>>({})
const advancingSlowHintState = ref<Record<string, boolean>>({})
const slowHintTimers = ref<Record<string, ReturnType<typeof setTimeout>>>({})

const afterSalesItems = ref<MerchantAfterSalesItem[]>([])
const afterSalesPage = ref(1)
const afterSalesPageSize = 6
const afterSalesTotal = ref(0)
const afterSalesFilter = ref<AfterSalesFilter>('open')
const afterSalesSectionLoading = ref(false)
const afterSalesActionState = ref<Record<string, boolean>>({})
const orderItemsDialogOrder = ref<MerchantOrder | null>(null)

const editingAddressId = ref<string | null>(null)

const pageToast = ref<{ visible: boolean; type: ToastKind; message: string }>({ visible: false, type: 'success', message: '' })
let pageToastTimer: ReturnType<typeof setTimeout> | null = null
let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

const SLOW_HINT_DELAY_MS = 1200
const SLOW_SHIPMENT_HOURS = 24
const tabs = [
  { key: 'workspace', label: '工作台' },
  { key: 'productManage', label: '商品管理' },
  { key: 'productCreate', label: '添加商品' },
  { key: 'shopProfile', label: '店铺资料' },
  { key: 'addressManage', label: '地址管理' }
] as const

const emptyProduct = (): ProductForm => ({ name: '', category: '', sku_code: '', brand: '', model: '', price: 0, original_price: 0, rating: 4.5, review_count: 0, monthly_sales: 0, ship_in_hours: 24, warranty_days: 365, stock: 0, image_url: '', description: '', tags: '', spec_highlights: '', is_active: true })
const emptyAddress = (): AddressForm => ({ label: '', contact_name: '', contact_phone: '', province: '', city: '', district: '', address_line: '', postal_code: '', is_default: false })

const productForm = reactive<ProductForm>(emptyProduct())
const productEditForm = reactive<ProductForm>(emptyProduct())
const addressForm = reactive<AddressForm>(emptyAddress())
const addressEditForm = reactive<AddressForm>(emptyAddress())
const shopForm = reactive({ logo_url: '', description: '', contact_email: '', contact_phone: '', shipping_city: '', featured_categories: '', service_tags: '' })

const shopDisplay = computed(() => shop.value?.name || authStore.user?.shop?.name || '商家工作台')
const addressTotalPages = computed(() => Math.max(1, Math.ceil(addressTotal.value / addressPageSize)))
const productTotalPages = computed(() => Math.max(1, Math.ceil(productTotal.value / productPageSize)))
const orderTotalPages = computed(() => Math.max(1, Math.ceil(orderTotal.value / orderPageSize)))
const afterSalesTotalPages = computed(() => Math.max(1, Math.ceil(afterSalesTotal.value / afterSalesPageSize)))
const selectedProductIds = computed(() => products.value.filter((item) => productSelection.value[item.id]).map((item) => item.id))
const selectedActiveProductIds = computed(() => products.value.filter((item) => productSelection.value[item.id] && item.is_active).map((item) => item.id))
const allVisibleProductsSelected = computed(() => products.value.length > 0 && products.value.every((item) => productSelection.value[item.id]))

const splitMultiValue = (raw: string) => raw.split(/\r?\n|,|，/).map((item) => item.trim()).filter(Boolean)
const joinMultiValue = (items?: string[] | null) => (items || []).join('，')
const formatCurrency = (value?: number | null) => `¥ ${Number(value || 0).toFixed(2)}`
const formatScore = (value?: number | null) => Number.isFinite(Number(value)) ? Number(value).toFixed(1) : '-'
const formatDate = (value?: string | null) => !value ? '-' : new Date(value).toLocaleString()
const formatShipHours = (value?: number | null) => Number(value) === 0 ? '即时发货' : `${Number(value || 0)} 小时内`
const formatAddress = (item: Pick<AddressItem, 'province' | 'city' | 'district' | 'address_line'>) => `${item.province}${item.city}${item.district}${item.address_line}`
const orderItemsPreview = (items: MerchantOrderItem[]) => {
  if (items.length === 0) return '当前订单暂无商品'
  if (items.length === 1) return items[0].product_name
  return `${items[0].product_name} 等 ${items.length} 件商品`
}
const closeOrderItemsDialog = () => { orderItemsDialogOrder.value = null }
const openOrderItemsDialog = (order: MerchantOrder) => { orderItemsDialogOrder.value = order }

const assignProduct = (target: ProductForm, source?: Partial<MerchantProduct> | null) => {
  const base = emptyProduct()
  target.name = source?.name || base.name
  target.category = source?.category || base.category
  target.sku_code = source?.sku_code || base.sku_code
  target.brand = source?.brand || base.brand
  target.model = source?.model || base.model
  target.price = Number(source?.price ?? base.price)
  target.original_price = Number(source?.original_price ?? base.original_price)
  target.rating = Number(source?.rating ?? base.rating)
  target.review_count = Number(source?.review_count ?? base.review_count)
  target.monthly_sales = Number(source?.monthly_sales ?? base.monthly_sales)
  target.ship_in_hours = Number(source?.ship_in_hours ?? base.ship_in_hours)
  target.warranty_days = Number(source?.warranty_days ?? base.warranty_days)
  target.stock = Number(source?.stock ?? base.stock)
  target.image_url = source?.image_url || base.image_url
  target.description = source?.description || base.description
  target.tags = Array.isArray(source?.tags) ? joinMultiValue(source.tags) : base.tags
  target.spec_highlights = Array.isArray(source?.spec_highlights) ? joinMultiValue(source.spec_highlights) : base.spec_highlights
  target.is_active = typeof source?.is_active === 'boolean' ? source.is_active : base.is_active
}
const assignAddress = (target: AddressForm, source?: Partial<AddressItem> | null) => {
  const base = emptyAddress()
  target.label = source?.label || base.label
  target.contact_name = source?.contact_name || base.contact_name
  target.contact_phone = source?.contact_phone || base.contact_phone
  target.province = source?.province || base.province
  target.city = source?.city || base.city
  target.district = source?.district || base.district
  target.address_line = source?.address_line || base.address_line
  target.postal_code = source?.postal_code || base.postal_code
  target.is_default = Boolean(source?.is_default)
}
const fillShopForm = (value: ShopInfo | null) => {
  shopForm.logo_url = value?.logo_url || ''
  shopForm.description = value?.description || ''
  shopForm.contact_email = value?.contact_email || ''
  shopForm.contact_phone = value?.contact_phone || ''
  shopForm.shipping_city = value?.shipping_city || ''
  shopForm.featured_categories = joinMultiValue(value?.featured_categories)
  shopForm.service_tags = joinMultiValue(value?.service_tags)
}

const clearNotice = () => { error.value = ''; success.value = '' }
const parseErr = (err: any, fallback: string) => {
  const detail = err?.response?.data?.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || JSON.stringify(item)).join('，')
  return JSON.stringify(detail)
}
const showToast = (type: ToastKind, message: string) => {
  if (pageToastTimer) clearTimeout(pageToastTimer)
  pageToast.value = { visible: true, type, message }
  pageToastTimer = setTimeout(() => { pageToast.value.visible = false }, 2600)
}

const productPayload = (form: ProductForm) => ({ name: form.name, category: form.category || null, sku_code: form.sku_code || null, brand: form.brand || null, model: form.model || null, price: Number(form.price), original_price: Number(form.original_price) || null, rating: Number(form.rating), review_count: Number(form.review_count), monthly_sales: Number(form.monthly_sales), ship_in_hours: Number(form.ship_in_hours), warranty_days: Number(form.warranty_days), stock: Number(form.stock), image_url: form.image_url || null, description: form.description || null, tags: splitMultiValue(form.tags), spec_highlights: splitMultiValue(form.spec_highlights), is_active: form.is_active })
const addressPayload = (form: AddressForm) => ({ label: form.label, contact_name: form.contact_name, contact_phone: form.contact_phone, province: form.province, city: form.city, district: form.district, address_line: form.address_line, postal_code: form.postal_code || null, is_default: form.is_default })

const orderStatusLabel = (status: string) => status === 'pending_shipment' ? '待发货' : status === 'shipped' ? '已发货' : status === 'cancelled' ? '已取消' : status
const logisticsStatusLabel = (status: string) => status === 'in_transit' ? '运输中' : status === 'delivered' ? '已送达' : status || '-'
const afterSalesTypeLabel = (type: string) => type === 'return' ? '退货' : type === 'exchange' ? '换货' : type
const afterSalesStatusLabel = (status: string) => status === 'submitted' ? '待处理' : status === 'merchant_approved' ? '已同意' : status === 'processing' ? '处理中' : status === 'merchant_rejected' ? '已拒绝' : status === 'completed' ? '已完成' : status === 'cancelled' ? '已取消' : status
const statusVariant = (kind: 'order' | 'afterSales' | 'product', value: string | boolean): 'default' | 'muted' | 'success' | 'info' | 'warn' | 'danger' => {
  if (kind === 'product') return value ? 'success' : 'muted'
  if (kind === 'order') return value === 'pending_shipment' ? 'warn' : value === 'shipped' ? 'info' : 'muted'
  return value === 'submitted' ? 'warn' : value === 'merchant_approved' ? 'info' : value === 'processing' ? 'default' : value === 'merchant_rejected' ? 'danger' : value === 'completed' ? 'success' : 'muted'
}
const afterSalesActions = (item: MerchantAfterSalesItem) => item.status === 'submitted' ? [{ key: 'approve', label: '同意' }, { key: 'reject', label: '驳回' }] : item.status === 'merchant_approved' ? [{ key: 'processing', label: '处理中' }, { key: 'complete', label: '完成' }] : item.status === 'processing' ? [{ key: 'complete', label: '完成' }] : []

const isShippingOrder = (id: string) => Boolean(shippingOrderState.value[id])
const isAdvancingLogistics = (id: string) => Boolean(advancingLogisticsState.value[id])
const isAfterSalesActing = (id: string) => Boolean(afterSalesActionState.value[id])
const isSlowShipment = (order: MerchantOrder) => order.status === 'pending_shipment' && (Date.now() - new Date(order.created_at).getTime()) / 36e5 >= SLOW_SHIPMENT_HOURS
const pendingHoursLabel = (createdAt: string) => {
  const hours = Math.max(0, Math.floor((Date.now() - new Date(createdAt).getTime()) / 36e5))
  return hours >= 24 ? `${Math.floor(hours / 24)}d ${hours % 24}h` : `${hours}h`
}
const clearSlowHintTimer = (key: string) => { const timer = slowHintTimers.value[key]; if (timer) { clearTimeout(timer); delete slowHintTimers.value[key] } }
const startSlowHintTimer = (key: string, state: { value: Record<string, boolean> }, orderId: string) => {
  clearSlowHintTimer(key)
  state.value[orderId] = false
  slowHintTimers.value[key] = setTimeout(() => { state.value[orderId] = true; delete slowHintTimers.value[key] }, SLOW_HINT_DELAY_MS)
}

const loadShop = async () => { const { data } = await api.get('/merchant/shop'); shop.value = data; fillShopForm(shop.value) }
const loadAddresses = async (targetPage = addressPage.value) => {
  const { data } = await api.get<Paged<AddressItem>>('/merchant/addresses', { params: { page: targetPage, page_size: addressPageSize } })
  addresses.value = data.items || []; addressTotal.value = Number(data.total || 0); addressPage.value = Number(data.page || targetPage)
  const maxPage = Math.max(1, Math.ceil(addressTotal.value / addressPageSize))
  if (addressTotal.value > 0 && addressPage.value > maxPage) await loadAddresses(maxPage)
}
const loadShippingAddresses = async () => {
  const { data } = await api.get<Paged<AddressItem>>('/merchant/addresses', { params: { page: 1, page_size: 100 } })
  shippingAddresses.value = data.items || []
}
const loadProducts = async (targetPage = productPage.value) => {
  const { data } = await api.get<Paged<MerchantProduct>>('/merchant/products', { params: { page: targetPage, page_size: productPageSize, keyword: productKeyword.value.trim() || undefined } })
  products.value = data.items || []; productTotal.value = Number(data.total || 0); productPage.value = Number(data.page || targetPage)
  const maxPage = Math.max(1, Math.ceil(productTotal.value / productPageSize))
  if (productTotal.value > 0 && productPage.value > maxPage) await loadProducts(maxPage)
}
const loadOrders = async (targetPage = orderPage.value, showLoading = !loading.value) => {
  if (showLoading) orderSectionLoading.value = true
  try {
    const { data } = await api.get<Paged<MerchantOrder>>('/merchant/orders', { params: { status_filter: orderFilter.value, page: targetPage, page_size: orderPageSize } })
    orders.value = data.items || []; orderTotal.value = Number(data.total || 0); orderPage.value = Number(data.page || targetPage)
    const maxPage = Math.max(1, Math.ceil(orderTotal.value / orderPageSize))
    if (orderTotal.value > 0 && orderPage.value > maxPage) { await loadOrders(maxPage, false); return }
    const defaultAddress = shippingAddresses.value.find((item) => item.is_default)
    for (const order of orders.value) if (!shipAddressByOrder.value[order.id] && defaultAddress) shipAddressByOrder.value[order.id] = defaultAddress.id
  } finally {
    if (showLoading) orderSectionLoading.value = false
  }
}
const loadAfterSales = async (targetPage = afterSalesPage.value, showLoading = !loading.value) => {
  if (showLoading) afterSalesSectionLoading.value = true
  try {
    const { data } = await api.get<Paged<MerchantAfterSalesItem>>('/merchant/after-sales', { params: { status_filter: afterSalesFilter.value, page: targetPage, page_size: afterSalesPageSize } })
    afterSalesItems.value = data.items || []; afterSalesTotal.value = Number(data.total || 0); afterSalesPage.value = Number(data.page || targetPage)
    const maxPage = Math.max(1, Math.ceil(afterSalesTotal.value / afterSalesPageSize))
    if (afterSalesTotal.value > 0 && afterSalesPage.value > maxPage) await loadAfterSales(maxPage, false)
  } finally {
    if (showLoading) afterSalesSectionLoading.value = false
  }
}
const loadAll = async () => {
  loading.value = true; clearNotice()
  try { await loadShop(); await loadAddresses(); await loadShippingAddresses(); await loadProducts(); await loadOrders(orderPage.value, false); await loadAfterSales(afterSalesPage.value, false) } catch (err: any) { error.value = parseErr(err, '商家中心加载失败') } finally { loading.value = false }
}

watch(orderFilter, async () => { orderPage.value = 1; if (!loading.value) await loadOrders(1) })
watch(afterSalesFilter, async () => { afterSalesPage.value = 1; if (!loading.value) await loadAfterSales(1) })
watch(products, (items) => {
  const ids = new Set(items.map((item) => item.id))
  productSelection.value = Object.fromEntries(Object.entries(productSelection.value).filter(([id]) => ids.has(id)))
  if (editingProductId.value && !ids.has(editingProductId.value)) { editingProductId.value = null; assignProduct(productEditForm) }
})
watch(addresses, (items) => {
  const ids = new Set(items.map((item) => item.id))
  if (editingAddressId.value && !ids.has(editingAddressId.value)) { editingAddressId.value = null; assignAddress(addressEditForm) }
})
watch(activeTab, clearNotice)

const applyProductSearch = async () => { productPage.value = 1; await loadProducts(1) }
const clearProductSearch = async () => { if (!productKeyword.value) return; productKeyword.value = ''; productPage.value = 1; await loadProducts(1) }
const setAllVisibleProductsSelected = (checked: boolean) => { for (const item of products.value) productSelection.value[item.id] = checked }
const setProductSelected = (productId: string, checked: boolean) => { productSelection.value[productId] = checked }
const startEditProduct = (item: MerchantProduct) => { editingProductId.value = item.id; assignProduct(productEditForm, item) }
const cancelProductEdit = () => { editingProductId.value = null; assignProduct(productEditForm) }
const startEditAddress = (item: AddressItem) => { editingAddressId.value = item.id; assignAddress(addressEditForm, item) }
const cancelAddressEdit = () => { editingAddressId.value = null; assignAddress(addressEditForm) }

const createProduct = async () => {
  clearNotice(); actionLoading.value = true
  try { await api.post('/merchant/products', productPayload(productForm)); assignProduct(productForm); success.value = '商品已创建'; activeTab.value = 'productManage'; await loadProducts(1) } catch (err: any) { error.value = parseErr(err, '商品创建失败') } finally { actionLoading.value = false }
}
const saveProductEdit = async () => {
  if (!editingProductId.value) return
  clearNotice(); actionLoading.value = true
  try { const { data } = await api.patch(`/merchant/products/${editingProductId.value}`, productPayload(productEditForm)); assignProduct(productEditForm, data); success.value = '商品信息已更新'; await loadProducts(productPage.value) } catch (err: any) { error.value = parseErr(err, '更新商品失败') } finally { actionLoading.value = false }
}
const toggleProductActive = async (item: MerchantProduct) => {
  clearNotice(); actionLoading.value = true
  try { await api.patch(`/merchant/products/${item.id}`, { is_active: !item.is_active }); success.value = item.is_active ? '商品已下架' : '商品已重新上架'; if (editingProductId.value === item.id) productEditForm.is_active = !item.is_active; await loadProducts(productPage.value) } catch (err: any) { error.value = parseErr(err, '更新商品状态失败') } finally { actionLoading.value = false }
}
const bulkDeactivateProducts = async () => {
  if (selectedActiveProductIds.value.length === 0) { error.value = '请先选择在售商品'; return }
  clearNotice(); actionLoading.value = true
  try {
    const results = await Promise.allSettled(selectedActiveProductIds.value.map((id) => api.patch(`/merchant/products/${id}`, { is_active: false })))
    const ok = results.filter((item) => item.status === 'fulfilled').length
    const fail = results.length - ok
    productSelection.value = {}
    if (ok) success.value = `已下架 ${ok} 个商品`
    if (fail) error.value = `有 ${fail} 个商品下架失败`
    await loadProducts(productPage.value)
  } finally { actionLoading.value = false }
}
const saveShopProfile = async () => {
  clearNotice(); actionLoading.value = true
  try { const { data } = await api.patch('/merchant/shop', { logo_url: shopForm.logo_url || null, description: shopForm.description || null, contact_email: shopForm.contact_email || null, contact_phone: shopForm.contact_phone || null, shipping_city: shopForm.shipping_city || null, featured_categories: splitMultiValue(shopForm.featured_categories), service_tags: splitMultiValue(shopForm.service_tags) }); shop.value = data; fillShopForm(shop.value); success.value = '店铺资料已更新' } catch (err: any) { error.value = parseErr(err, '更新店铺资料失败') } finally { actionLoading.value = false }
}
const createAddress = async () => {
  clearNotice(); actionLoading.value = true
  try { await api.post('/merchant/addresses', addressPayload(addressForm)); assignAddress(addressForm); success.value = '发货地址已新增'; await loadAddresses(1); await loadShippingAddresses(); await loadOrders(orderPage.value) } catch (err: any) { error.value = parseErr(err, '新增地址失败') } finally { actionLoading.value = false }
}
const saveAddressEdit = async () => {
  if (!editingAddressId.value) return
  clearNotice(); actionLoading.value = true
  try { await api.patch(`/merchant/addresses/${editingAddressId.value}`, addressPayload(addressEditForm)); success.value = '地址已更新'; await loadAddresses(addressPage.value); await loadShippingAddresses(); await loadOrders(orderPage.value) } catch (err: any) { error.value = parseErr(err, '更新地址失败') } finally { actionLoading.value = false }
}
const setDefaultAddress = async (addressId: string) => {
  clearNotice(); actionLoading.value = true
  try { await api.patch(`/merchant/addresses/${addressId}`, { is_default: true }); success.value = '默认地址已更新'; await loadAddresses(addressPage.value); await loadShippingAddresses(); await loadOrders(orderPage.value) } catch (err: any) { error.value = parseErr(err, '更新默认地址失败') } finally { actionLoading.value = false }
}
const deleteAddress = async (item: AddressItem) => {
  if (!window.confirm(`确认删除地址“${item.label}”吗？`)) return
  clearNotice(); actionLoading.value = true
  try { await api.delete(`/merchant/addresses/${item.id}`); if (editingAddressId.value === item.id) cancelAddressEdit(); success.value = '地址已删除'; await loadAddresses(addressPage.value); await loadShippingAddresses(); await loadOrders(orderPage.value) } catch (err: any) { error.value = parseErr(err, '删除地址失败') } finally { actionLoading.value = false }
}

const shipOrder = async (order: MerchantOrder) => {
  if (isShippingOrder(order.id)) return
  startSlowHintTimer(`ship:${order.id}`, shippingSlowHintState, order.id)
  shippingOrderState.value[order.id] = true
  try { await api.post(`/merchant/orders/${order.id}/ship`, { ship_from_address_id: shipAddressByOrder.value[order.id] || null }, { timeout: 60000 }); showToast('success', `订单 ${order.id} 已发货`); await loadOrders(orderPage.value, false) } catch (err: any) { showToast('error', parseErr(err, '发货失败')) } finally { clearSlowHintTimer(`ship:${order.id}`); shippingSlowHintState.value[order.id] = false; shippingOrderState.value[order.id] = false }
}
const advanceLogistics = async (order: MerchantOrder) => {
  if (isAdvancingLogistics(order.id)) return
  startSlowHintTimer(`advance:${order.id}`, advancingSlowHintState, order.id)
  advancingLogisticsState.value[order.id] = true
  try { await api.post(`/merchant/orders/${order.id}/logistics/advance`); showToast('success', `订单 ${order.id} 物流已推进`); await loadOrders(orderPage.value, false) } catch (err: any) { showToast('error', parseErr(err, '推进物流失败')) } finally { clearSlowHintTimer(`advance:${order.id}`); advancingSlowHintState.value[order.id] = false; advancingLogisticsState.value[order.id] = false }
}
const handleAfterSales = async (item: MerchantAfterSalesItem, action: string) => {
  if (isAfterSalesActing(item.id)) return
  afterSalesActionState.value[item.id] = true
  try { await api.patch(`/merchant/after-sales/${item.id}`, { action }); showToast('success', `售后 ${item.order_id} 已更新`); await loadAfterSales(afterSalesPage.value, false); await loadOrders(orderPage.value, false) } catch (err: any) { showToast('error', parseErr(err, '售后处理失败')) } finally { afterSalesActionState.value[item.id] = false }
}

const scheduleRealtimeRefresh = (target: 'orders' | 'products' | 'after_sales' | 'all') => {
  if (realtimeRefreshTimer) return
  realtimeRefreshTimer = setTimeout(async () => {
    realtimeRefreshTimer = null
    try {
      if (target === 'all') await Promise.all([loadProducts(productPage.value), loadOrders(orderPage.value, false), loadAfterSales(afterSalesPage.value, false)])
      else if (target === 'orders') await loadOrders(orderPage.value, false)
      else if (target === 'products') await loadProducts(productPage.value)
      else await loadAfterSales(afterSalesPage.value, false)
    } catch {}
  }, 320)
}
const handleRealtimeEvent = (event: RealtimeEvent) => {
  const eventShopId = typeof event.data?.shop_id === 'string' ? event.data.shop_id : ''
  if (eventShopId && shop.value?.id && eventShopId !== shop.value.id) return
  if (event.event === 'inventory_changed') scheduleRealtimeRefresh(activeTab.value === 'productManage' || activeTab.value === 'productCreate' ? 'products' : 'all')
  else if (event.event === 'order_changed') scheduleRealtimeRefresh(activeTab.value === 'workspace' ? 'orders' : 'all')
  else if (event.event === 'after_sales_changed') scheduleRealtimeRefresh(activeTab.value === 'workspace' ? 'all' : 'after_sales')
}

onMounted(async () => { await loadAll(); realtimeClient = createRealtimeClient({ token: authStore.token, onEvent: handleRealtimeEvent }) })
onBeforeUnmount(() => {
  for (const key of Object.keys(slowHintTimers.value)) clearSlowHintTimer(key)
  if (pageToastTimer) clearTimeout(pageToastTimer)
  if (realtimeRefreshTimer) clearTimeout(realtimeRefreshTimer)
  realtimeClient?.close(); realtimeClient = null
})
</script>

<template>
  <section class="merchant-page app-page">
    <transition name="toast-fade">
      <div v-if="pageToast.visible" class="ship-toast" :class="pageToast.type">{{ pageToast.message }}</div>
    </transition>

    <PageHero eyebrow="Merchant Workspace" :title="shopDisplay" accent="gold" />

    <AppDialog
      :open="Boolean(orderItemsDialogOrder)"
      title="商品清单"
      :description="orderItemsDialogOrder ? orderItemsPreview(orderItemsDialogOrder.items) : ''"
      width-class="max-w-2xl"
      @close="closeOrderItemsDialog"
    >
      <div class="dialog-items-shell">
        <div class="dialog-items-head">
          <Badge variant="muted">{{ orderItemsDialogOrder?.items.length || 0 }} 件商品</Badge>
          <span class="meta">{{ orderItemsDialogOrder ? formatCurrency(orderItemsDialogOrder.total_amount) : '' }}</span>
        </div>
        <ul class="dialog-items-list">
          <li v-for="item in orderItemsDialogOrder?.items || []" :key="item.id" class="dialog-item-row">
            <div class="dialog-item-main">
              <strong class="item-name truncate1">{{ item.product_name }}</strong>
              <span class="meta">数量 x {{ item.quantity }}</span>
            </div>
            <strong>{{ formatCurrency(item.subtotal) }}</strong>
          </li>
        </ul>
      </div>
    </AppDialog>

    <div class="merchant-tabs panel-surface">
      <Button v-for="tab in tabs" :key="tab.key" :variant="activeTab === tab.key ? 'default' : 'outline'" size="sm" @click="activeTab = tab.key">
        {{ tab.label }}
      </Button>
    </div>

    <p v-if="error" class="notice error">{{ error }}</p>
    <p v-if="success" class="notice success">{{ success }}</p>
    <div v-if="loading" class="state-card panel-surface">加载中...</div>

    <template v-else>
      <section v-if="activeTab === 'workspace'" class="tab-panel">
        <div class="overview-grid">
          <article class="overview-card">
            <p class="meta">待发货</p>
            <div class="stat-row">
              <strong>{{ orderFilter === 'pending_shipment' ? orderTotal : orders.filter((o) => o.status === 'pending_shipment').length }}</strong>
              <Badge variant="warn">待发货</Badge>
            </div>
          </article>
          <article class="overview-card">
            <p class="meta">当前订单</p>
            <div class="stat-row">
              <strong>{{ orderTotal }}</strong>
              <Badge variant="info">订单</Badge>
            </div>
          </article>
          <article class="overview-card">
            <p class="meta">进行中售后</p>
            <div class="stat-row">
              <strong>{{ afterSalesFilter === 'open' ? afterSalesTotal : afterSalesItems.filter((i) => i.status !== 'completed').length }}</strong>
              <Badge variant="danger">售后</Badge>
            </div>
          </article>
          <article class="overview-card">
            <p class="meta">默认地址</p>
            <div class="stat-row">
              <strong>{{ shippingAddresses.find((i) => i.is_default)?.label || '未设置' }}</strong>
              <Badge variant="default">地址</Badge>
            </div>
          </article>
        </div>

        <div class="workspace-grid">
          <article class="surface-card">
            <div class="surface-head">
              <div>
                <p class="eyebrow">Orders</p>
                <h2>订单</h2>
              </div>
              <div class="toolbar">
                <select v-model="orderFilter" class="control-select">
                  <option value="pending_shipment">待发货</option>
                  <option value="shipped">已发货</option>
                  <option value="all">全部</option>
                </select>
                <Button variant="outline" size="sm" @click="loadOrders(orderPage)">刷新</Button>
              </div>
            </div>

            <div v-if="orderSectionLoading" class="loading-panel">
              <div v-for="item in 3" :key="item" class="loading-card">
                <div class="loading-row">
                  <span class="loading-pill w-28"></span>
                  <span class="loading-pill w-20"></span>
                </div>
                <span class="loading-line w-40"></span>
                <span class="loading-line w-full"></span>
                <span class="loading-line w-32"></span>
                <div class="loading-box"></div>
              </div>
            </div>
            <div v-else-if="orders.length === 0" class="empty-shell">
              <p class="eyebrow">Order Queue</p>
              <h3>当前筛选下没有订单</h3>
            </div>
            <div v-else class="card-stack">
              <article v-for="order in orders" :key="order.id" class="order-card">
                <div class="card-head">
                  <div class="toolbar">
                    <Badge :variant="statusVariant('order', order.status)">{{ orderStatusLabel(order.status) }}</Badge>
                    <span v-if="order.status === 'pending_shipment'" class="meta">
                      待处理 {{ pendingHoursLabel(order.created_at) }}<span v-if="isSlowShipment(order)"> · 超时</span>
                    </span>
                  </div>
                  <strong>{{ formatCurrency(order.total_amount) }}</strong>
                </div>
                <p class="meta">{{ formatDate(order.created_at) }}</p>
                <p class="meta truncate1">收货地址：{{ order.address }}</p>
                <p class="meta">售后申请：{{ order.after_sales?.length || 0 }} 条</p>

                <div class="items-hover">
                  <button class="items-toggle" type="button" @click="openOrderItemsDialog(order)">
                    <div class="items-toggle-main">
                      <span class="items-toggle-icon">
                        <Package2 :size="16" />
                      </span>
                      <div class="items-toggle-copy">
                        <strong>商品清单</strong>
                        <span class="meta truncate1">{{ orderItemsPreview(order.items) }}</span>
                      </div>
                    </div>
                    <Badge variant="muted">点击查看</Badge>
                  </button>
                </div>

                <div class="toolbar" v-if="order.after_sales?.length">
                  <Badge v-for="asItem in order.after_sales" :key="asItem.id" :variant="statusVariant('afterSales', asItem.status)">
                    {{ afterSalesTypeLabel(asItem.type) }} · {{ afterSalesStatusLabel(asItem.status) }}
                  </Badge>
                </div>

                <div v-if="order.status === 'pending_shipment'" class="ship-row">
                  <select v-model="shipAddressByOrder[order.id]" class="control-select">
                    <option value="">默认发货地址</option>
                    <option v-for="addr in shippingAddresses" :key="addr.id" :value="addr.id">
                      {{ addr.label }} · {{ formatAddress(addr) }}
                    </option>
                  </select>
                  <Button size="sm" :disabled="actionLoading || isShippingOrder(order.id)" @click="shipOrder(order)">
                    {{ isShippingOrder(order.id) ? '发货中...' : '发货' }}
                  </Button>
                </div>
                <p v-if="shippingSlowHintState[order.id]" class="slow">正在联系仓库并同步物流，请稍候...</p>

                <div v-if="order.logistics" class="metrics">
                  <p><span>运单号</span>{{ order.logistics.tracking_no || '待生成' }}</p>
                  <p><span>物流状态</span>{{ logisticsStatusLabel(order.logistics.status) }}</p>
                  <p><span>当前位置</span>{{ order.logistics.current_location || '-' }}</p>
                  <p><span>预计送达</span>{{ formatDate(order.logistics.estimated_delivery_at) }}</p>
                </div>
                <p v-if="order.logistics" class="route truncate1">路径：{{ (order.logistics.route_plan || []).join(' -> ') || '-' }}</p>
                <div v-if="order.logistics" class="action-row">
                  <Button variant="outline" size="sm" :disabled="actionLoading || isAdvancingLogistics(order.id) || order.logistics.status === 'delivered'" @click="advanceLogistics(order)">
                    {{ isAdvancingLogistics(order.id) ? '推进中...' : order.logistics.status === 'delivered' ? '已送达' : '推进到下一站' }}
                  </Button>
                  <p v-if="advancingSlowHintState[order.id]" class="slow">正在同步下一站轨迹，请稍候...</p>
                </div>
              </article>
              <ListPager :page="orderPage" :total-pages="orderTotalPages" :total-items="orderTotal" @change="loadOrders" />
            </div>
          </article>

          <article class="surface-card">
            <div class="surface-head">
              <div>
                <p class="eyebrow">After Sales</p>
                <h2>售后</h2>
              </div>
              <div class="toolbar">
                <select v-model="afterSalesFilter" class="control-select">
                  <option value="open">进行中</option>
                  <option value="submitted">待处理</option>
                  <option value="merchant_approved">已同意</option>
                  <option value="processing">处理中</option>
                  <option value="merchant_rejected">已拒绝</option>
                  <option value="completed">已完成</option>
                  <option value="all">全部</option>
                </select>
                <Button variant="outline" size="sm" @click="loadAfterSales(afterSalesPage)">刷新</Button>
              </div>
            </div>

            <div v-if="afterSalesSectionLoading" class="loading-panel">
              <div v-for="item in 3" :key="item" class="loading-card">
                <div class="loading-row">
                  <span class="loading-pill w-24"></span>
                  <span class="loading-pill w-24"></span>
                </div>
                <span class="loading-line w-32"></span>
                <span class="loading-line w-full"></span>
                <span class="loading-line w-28"></span>
              </div>
            </div>
            <div v-else-if="afterSalesItems.length === 0" class="empty-shell">
              <p class="eyebrow">After Sales</p>
              <h3>当前没有售后申请</h3>
            </div>
            <div v-else class="card-stack">
              <article v-for="item in afterSalesItems" :key="item.id" class="after-card">
                <div class="card-head">
                  <div class="toolbar">
                    <Badge :variant="statusVariant('afterSales', item.status)">{{ afterSalesStatusLabel(item.status) }}</Badge>
                    <span class="meta">{{ afterSalesTypeLabel(item.type) }}</span>
                  </div>
                  <span class="meta">{{ formatDate(item.created_at) }}</span>
                </div>
                <p class="meta">订单状态：{{ orderStatusLabel(item.order_status) }}</p>
                <p class="truncate2">{{ item.reason || '买家未填写售后说明' }}</p>
                <a class="meta order-link" :href="item.order_link" target="_blank" rel="noreferrer">查看订单</a>
                <div class="action-row" v-if="afterSalesActions(item).length">
                  <Button v-for="action in afterSalesActions(item)" :key="action.key" :variant="action.key === 'reject' ? 'outline' : 'default'" size="sm" :disabled="isAfterSalesActing(item.id)" @click="handleAfterSales(item, action.key)">
                    {{ isAfterSalesActing(item.id) ? '处理中...' : action.label }}
                  </Button>
                </div>
              </article>
              <ListPager :page="afterSalesPage" :total-pages="afterSalesTotalPages" :total-items="afterSalesTotal" @change="loadAfterSales" />
            </div>
          </article>
        </div>
      </section>
      <section v-if="activeTab === 'productManage'" class="tab-panel">
        <div class="overview-grid">
          <article class="overview-card">
            <p class="meta">当前页在售</p>
            <div class="stat-row">
              <strong>{{ products.filter((item) => item.is_active).length }}</strong>
              <Badge variant="success">在售</Badge>
            </div>
          </article>
          <article class="overview-card">
            <p class="meta">当前页已下架</p>
            <div class="stat-row">
              <strong>{{ products.filter((item) => !item.is_active).length }}</strong>
              <Badge variant="muted">已下架</Badge>
            </div>
          </article>
          <article class="overview-card">
            <p class="meta">已选商品</p>
            <div class="stat-row">
              <strong>{{ selectedProductIds.length }}</strong>
              <Badge variant="info">多选</Badge>
            </div>
          </article>
          <article class="overview-card">
            <p class="meta">当前页库存</p>
            <div class="stat-row">
              <strong>{{ products.reduce((sum, item) => sum + Number(item.stock || 0), 0) }}</strong>
              <Badge variant="default">库存</Badge>
            </div>
          </article>
        </div>

        <div class="manage-grid">
          <article class="surface-card">
            <div class="surface-head">
              <div>
                <p class="eyebrow">Catalog</p>
                <h2>当前商品</h2>
              </div>
              <div class="toolbar">
                <input v-model="productKeyword" class="control-input" type="text" placeholder="搜索商品名 / 品牌 / SKU" @keyup.enter="applyProductSearch">
                <Button variant="outline" size="sm" @click="applyProductSearch">搜索</Button>
                <Button variant="outline" size="sm" @click="clearProductSearch">清空</Button>
              </div>
            </div>

            <div class="bulk-row">
              <Checkbox :model-value="allVisibleProductsSelected" @update:model-value="setAllVisibleProductsSelected">
                全选当前页
              </Checkbox>
              <div class="action-row">
                <span class="meta">已选 {{ selectedProductIds.length }} 项</span>
                <Button variant="danger" size="sm" :disabled="actionLoading || selectedActiveProductIds.length === 0" @click="bulkDeactivateProducts">批量下架</Button>
              </div>
            </div>

            <div v-if="products.length === 0" class="empty-shell">
              <p class="eyebrow">Catalog</p>
              <h3>没有匹配的商品</h3>
            </div>
            <div v-else class="card-stack">
              <article v-for="item in products" :key="item.id" class="product-card" :class="{ selected: productSelection[item.id] }">
                <Checkbox :model-value="Boolean(productSelection[item.id])" class="card-checkbox" @update:model-value="(checked) => setProductSelected(item.id, checked)" />
                <img v-if="item.image_url" :src="item.image_url" :alt="item.name">
                <div v-else class="thumb">无图</div>
                <div class="card-stack" style="gap:10px">
                  <div class="card-head">
                    <div>
                      <h3 class="title truncate2">{{ item.name }}</h3>
                      <p class="meta truncate1">{{ item.brand || '未填品牌' }} · {{ item.category || '未分类' }} · SKU {{ item.sku_code || '未填' }}</p>
                    </div>
                    <Badge :variant="statusVariant('product', item.is_active)">{{ item.is_active ? '在售' : '已下架' }}</Badge>
                  </div>
                  <p class="meta truncate2">{{ item.description || '暂无描述' }}</p>
                  <div class="metrics">
                    <p><span>售价</span>{{ formatCurrency(item.price) }}</p>
                    <p><span>库存</span>{{ item.stock }}</p>
                    <p><span>评分</span>{{ formatScore(item.rating) }}</p>
                    <p><span>发货</span>{{ formatShipHours(item.ship_in_hours) }}</p>
                  </div>
                  <div class="action-row">
                    <Button size="sm" @click="startEditProduct(item)">编辑详情</Button>
                    <Button variant="outline" size="sm" :disabled="actionLoading" @click="toggleProductActive(item)">{{ item.is_active ? '下架' : '重新上架' }}</Button>
                  </div>
                </div>
              </article>
              <ListPager :page="productPage" :total-pages="productTotalPages" :total-items="productTotal" @change="loadProducts" />
            </div>
          </article>

          <article class="surface-card">
            <div class="surface-head">
              <div>
                <p class="eyebrow">Editor</p>
                <h2>商品编辑</h2>
              </div>
              <Button v-if="editingProductId" variant="ghost" size="sm" @click="cancelProductEdit">清空</Button>
            </div>

            <div v-if="!editingProductId" class="placeholder">
              <h3>选择左侧商品</h3>
              <p>可在这里修改价格、库存、描述、标签和上架状态。</p>
            </div>
            <form v-else class="editor-stack" @submit.prevent="saveProductEdit">
              <div class="form-grid">
                <label class="field wide"><span>商品名称</span><input v-model="productEditForm.name" class="field-input" required></label>
                <label class="field"><span>分类</span><input v-model="productEditForm.category" class="field-input"></label>
                <label class="field"><span>SKU</span><input v-model="productEditForm.sku_code" class="field-input"></label>
                <label class="field"><span>品牌</span><input v-model="productEditForm.brand" class="field-input"></label>
                <label class="field"><span>型号</span><input v-model="productEditForm.model" class="field-input"></label>
                <label class="field"><span>售价</span><input v-model.number="productEditForm.price" class="field-input" type="number" min="0" step="0.01" required></label>
                <label class="field"><span>原价</span><input v-model.number="productEditForm.original_price" class="field-input" type="number" min="0" step="0.01"></label>
                <label class="field"><span>库存</span><input v-model.number="productEditForm.stock" class="field-input" type="number" min="0" step="1" required></label>
                <label class="field"><span>评分</span><input v-model.number="productEditForm.rating" class="field-input" type="number" min="0" max="5" step="0.1"></label>
                <label class="field"><span>评价数</span><input v-model.number="productEditForm.review_count" class="field-input" type="number" min="0" step="1"></label>
                <label class="field"><span>月销</span><input v-model.number="productEditForm.monthly_sales" class="field-input" type="number" min="0" step="1"></label>
                <label class="field"><span>发货时效</span><input v-model.number="productEditForm.ship_in_hours" class="field-input" type="number" min="0" step="1"></label>
                <label class="field"><span>保修天数</span><input v-model.number="productEditForm.warranty_days" class="field-input" type="number" min="0" step="1"></label>
                <label class="field"><span>上架状态</span><select v-model="productEditForm.is_active" class="field-select"><option :value="true">在售</option><option :value="false">已下架</option></select></label>
                <label class="field wide"><span>图片 URL</span><input v-model="productEditForm.image_url" class="field-input"></label>
                <label class="field wide"><span>商品描述</span><textarea v-model="productEditForm.description" class="field-textarea" rows="4"></textarea></label>
                <label class="field wide"><span>标签</span><textarea v-model="productEditForm.tags" class="field-textarea" rows="3" placeholder="支持逗号或换行"></textarea></label>
                <label class="field wide"><span>核心参数</span><textarea v-model="productEditForm.spec_highlights" class="field-textarea" rows="3" placeholder="支持逗号或换行"></textarea></label>
              </div>
              <div class="form-actions">
                <Button variant="outline" type="button" @click="cancelProductEdit">取消</Button>
                <Button type="submit" :disabled="actionLoading">保存修改</Button>
              </div>
            </form>
          </article>
        </div>
      </section>
      <section v-if="activeTab === 'productCreate'" class="tab-panel">
        <article class="surface-card">
          <div class="surface-head">
            <div>
              <p class="eyebrow">New Product</p>
              <h2>添加商品</h2>
            </div>
            <Badge variant="info">支持多值标签</Badge>
          </div>

          <form class="editor-stack" @submit.prevent="createProduct">
            <div class="form-grid">
              <label class="field wide"><span>商品名称</span><input v-model="productForm.name" class="field-input" required placeholder="27 英寸 4K 办公显示器"></label>
              <label class="field"><span>分类</span><input v-model="productForm.category" class="field-input" placeholder="显示器"></label>
              <label class="field"><span>SKU</span><input v-model="productForm.sku_code" class="field-input" placeholder="OFFICE-27-4K-001"></label>
              <label class="field"><span>品牌</span><input v-model="productForm.brand" class="field-input"></label>
              <label class="field"><span>型号</span><input v-model="productForm.model" class="field-input"></label>
              <label class="field"><span>售价</span><input v-model.number="productForm.price" class="field-input" type="number" min="0" step="0.01" required></label>
              <label class="field"><span>原价</span><input v-model.number="productForm.original_price" class="field-input" type="number" min="0" step="0.01"></label>
              <label class="field"><span>库存</span><input v-model.number="productForm.stock" class="field-input" type="number" min="0" step="1" required></label>
              <label class="field"><span>评分</span><input v-model.number="productForm.rating" class="field-input" type="number" min="0" max="5" step="0.1"></label>
              <label class="field"><span>评价数</span><input v-model.number="productForm.review_count" class="field-input" type="number" min="0" step="1"></label>
              <label class="field"><span>月销</span><input v-model.number="productForm.monthly_sales" class="field-input" type="number" min="0" step="1"></label>
              <label class="field"><span>发货时效</span><input v-model.number="productForm.ship_in_hours" class="field-input" type="number" min="0" step="1"></label>
              <label class="field"><span>保修天数</span><input v-model.number="productForm.warranty_days" class="field-input" type="number" min="0" step="1"></label>
              <label class="field wide"><span>图片 URL</span><input v-model="productForm.image_url" class="field-input"></label>
              <label class="field wide"><span>商品描述</span><textarea v-model="productForm.description" class="field-textarea" rows="4"></textarea></label>
              <label class="field wide"><span>标签</span><textarea v-model="productForm.tags" class="field-textarea" rows="3" placeholder="支持逗号或换行"></textarea></label>
              <label class="field wide"><span>核心参数</span><textarea v-model="productForm.spec_highlights" class="field-textarea" rows="3" placeholder="支持逗号或换行"></textarea></label>
            </div>
            <div class="form-actions">
              <Button variant="outline" type="button" @click="assignProduct(productForm)">重置</Button>
              <Button type="submit" :disabled="actionLoading">创建商品</Button>
            </div>
          </form>
        </article>
      </section>
      <section v-if="activeTab === 'shopProfile'" class="tab-panel">
        <div class="overview-grid">
          <article class="overview-card">
            <p class="meta">店铺评分</p>
            <div class="stat-row"><strong>{{ formatScore(shop?.rating) }}</strong><Badge variant="default">综合</Badge></div>
          </article>
          <article class="overview-card">
            <p class="meta">服务评分</p>
            <div class="stat-row"><strong>{{ formatScore(shop?.service_score) }}</strong><Badge variant="info">服务</Badge></div>
          </article>
          <article class="overview-card">
            <p class="meta">物流评分</p>
            <div class="stat-row"><strong>{{ formatScore(shop?.logistics_score) }}</strong><Badge variant="info">物流</Badge></div>
          </article>
          <article class="overview-card">
            <p class="meta">售后评分</p>
            <div class="stat-row"><strong>{{ formatScore(shop?.after_sales_score) }}</strong><Badge variant="success">售后</Badge></div>
          </article>
        </div>

        <article class="surface-card">
          <div class="surface-head">
            <div>
              <p class="eyebrow">Shop Profile</p>
              <h2>店铺资料</h2>
            </div>
            <Badge variant="default">{{ shop?.shipping_city || '未设置发货城市' }}</Badge>
          </div>

          <form class="editor-stack" @submit.prevent="saveShopProfile">
            <div class="form-grid">
              <label class="field"><span>联系邮箱</span><input v-model="shopForm.contact_email" class="field-input" type="email"></label>
              <label class="field"><span>联系电话</span><input v-model="shopForm.contact_phone" class="field-input"></label>
              <label class="field"><span>发货城市</span><input v-model="shopForm.shipping_city" class="field-input"></label>
              <label class="field wide"><span>店铺简介</span><textarea v-model="shopForm.description" class="field-textarea" rows="4"></textarea></label>
              <label class="field wide"><span>Logo URL</span><input v-model="shopForm.logo_url" class="field-input"></label>
              <label class="field wide"><span>主营类目</span><textarea v-model="shopForm.featured_categories" class="field-textarea" rows="3" placeholder="支持逗号或换行"></textarea></label>
              <label class="field wide"><span>服务标签</span><textarea v-model="shopForm.service_tags" class="field-textarea" rows="3" placeholder="支持逗号或换行"></textarea></label>
            </div>
            <div class="form-actions">
              <Button type="submit" :disabled="actionLoading">保存店铺资料</Button>
            </div>
          </form>
        </article>
      </section>
      <section v-if="activeTab === 'addressManage'" class="tab-panel">
        <div class="manage-grid">
          <article class="surface-card">
            <div class="surface-head">
              <div>
                <p class="eyebrow">Addresses</p>
                <h2>已保存地址</h2>
              </div>
              <Button variant="outline" size="sm" @click="loadAddresses(addressPage)">刷新</Button>
            </div>

            <div v-if="addresses.length === 0" class="empty-shell">
              <p class="eyebrow">Addresses</p>
              <h3>还没有发货地址</h3>
            </div>
            <div v-else class="card-stack">
              <article v-for="item in addresses" :key="item.id" class="address-card">
                <div class="card-head">
                  <h3 class="title truncate1">{{ item.label }}</h3>
                  <Badge :variant="item.is_default ? 'success' : 'muted'">{{ item.is_default ? '默认地址' : '普通地址' }}</Badge>
                </div>
                <p class="meta">{{ item.contact_name }} · {{ item.contact_phone }}</p>
                <p class="meta truncate1">{{ item.province }} {{ item.city }} {{ item.district }}</p>
                <p class="truncate2">{{ item.address_line }}</p>
                <p class="meta">邮编 {{ item.postal_code || '-' }}</p>
                <div class="action-row">
                  <Button size="sm" @click="startEditAddress(item)">编辑</Button>
                  <Button variant="outline" size="sm" :disabled="actionLoading || item.is_default" @click="setDefaultAddress(item.id)">设为默认</Button>
                  <Button variant="danger" size="sm" :disabled="actionLoading" @click="deleteAddress(item)">删除</Button>
                </div>
              </article>
              <ListPager :page="addressPage" :total-pages="addressTotalPages" :total-items="addressTotal" @change="loadAddresses" />
            </div>
          </article>

          <div class="editor-stack">
            <article class="surface-card">
              <div class="surface-head">
                <div>
                  <p class="eyebrow">Create</p>
                  <h2>新增地址</h2>
                </div>
              </div>
              <form class="editor-stack" @submit.prevent="createAddress">
                <div class="form-grid">
                  <label class="field"><span>地址标签</span><input v-model="addressForm.label" class="field-input" required></label>
                  <label class="field"><span>联系人</span><input v-model="addressForm.contact_name" class="field-input" required></label>
                  <label class="field"><span>联系电话</span><input v-model="addressForm.contact_phone" class="field-input" required></label>
                  <label class="field"><span>省份</span><input v-model="addressForm.province" class="field-input" required></label>
                  <label class="field"><span>城市</span><input v-model="addressForm.city" class="field-input" required></label>
                  <label class="field"><span>区县</span><input v-model="addressForm.district" class="field-input" required></label>
                  <label class="field wide"><span>详细地址</span><textarea v-model="addressForm.address_line" class="field-textarea" rows="3" required></textarea></label>
                  <label class="field"><span>邮编</span><input v-model="addressForm.postal_code" class="field-input"></label>
                  <label class="field"><span>默认地址</span><select v-model="addressForm.is_default" class="field-select"><option :value="false">否</option><option :value="true">是</option></select></label>
                </div>
                <div class="form-actions">
                  <Button variant="outline" type="button" @click="assignAddress(addressForm)">重置</Button>
                  <Button type="submit" :disabled="actionLoading">新增地址</Button>
                </div>
              </form>
            </article>

            <article class="surface-card">
              <div class="surface-head">
                <div>
                  <p class="eyebrow">Edit</p>
                  <h2>地址编辑</h2>
                </div>
                <Button v-if="editingAddressId" variant="ghost" size="sm" @click="cancelAddressEdit">清空</Button>
              </div>

              <div v-if="!editingAddressId" class="placeholder">
                <h3>选择左侧地址</h3>
                <p>可修改联系人、区域、详细地址，或切换默认地址。</p>
              </div>
              <form v-else class="editor-stack" @submit.prevent="saveAddressEdit">
                <div class="form-grid">
                  <label class="field"><span>地址标签</span><input v-model="addressEditForm.label" class="field-input" required></label>
                  <label class="field"><span>联系人</span><input v-model="addressEditForm.contact_name" class="field-input" required></label>
                  <label class="field"><span>联系电话</span><input v-model="addressEditForm.contact_phone" class="field-input" required></label>
                  <label class="field"><span>省份</span><input v-model="addressEditForm.province" class="field-input" required></label>
                  <label class="field"><span>城市</span><input v-model="addressEditForm.city" class="field-input" required></label>
                  <label class="field"><span>区县</span><input v-model="addressEditForm.district" class="field-input" required></label>
                  <label class="field wide"><span>详细地址</span><textarea v-model="addressEditForm.address_line" class="field-textarea" rows="3" required></textarea></label>
                  <label class="field"><span>邮编</span><input v-model="addressEditForm.postal_code" class="field-input"></label>
                  <label class="field"><span>默认地址</span><select v-model="addressEditForm.is_default" class="field-select"><option :value="false">否</option><option :value="true">是</option></select></label>
                </div>
                <div class="form-actions">
                  <Button variant="outline" type="button" @click="cancelAddressEdit">取消</Button>
                  <Button type="submit" :disabled="actionLoading">保存修改</Button>
                </div>
              </form>
            </article>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.merchant-page,.tab-panel,.editor-stack,.card-stack{display:grid;gap:18px}
.merchant-tabs{display:flex;flex-wrap:wrap;gap:10px;padding:16px}
.notice,.state-card,.surface-card,.overview-card{padding:16px;border-radius:var(--radius-md);border:1px solid var(--line);background:rgba(255,252,247,.9)}
.notice.error{color:var(--danger);border-color:rgba(182,60,55,.2)}
.notice.success{color:var(--success);border-color:rgba(31,122,99,.2)}
.surface-head,.toolbar,.bulk-row,.action-row,.form-actions,.card-head,.ship-row,.stat-row{display:flex;gap:10px;align-items:center}
.surface-head,.bulk-row,.card-head,.stat-row{justify-content:space-between}
.surface-head h2,.title{margin:0}
.eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--text-soft)}
.subtle,.meta{color:var(--text-muted);font-size:14px}
.overview-grid,.manage-grid,.workspace-grid,.form-grid,.metrics{display:grid;gap:14px}
.overview-grid{grid-template-columns:repeat(4,minmax(0,1fr))}
.workspace-grid,.manage-grid{grid-template-columns:minmax(0,1.4fr) minmax(320px,1fr)}
.form-grid,.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}
.field{display:grid;gap:8px;padding:14px;border-radius:var(--radius-md);border:1px solid var(--line);background:linear-gradient(180deg,rgba(255,252,247,.92),rgba(248,241,231,.9));box-shadow:inset 0 1px 0 rgba(255,255,255,.78),0 10px 24px rgba(39,27,12,.04);transition:border-color .18s ease,box-shadow .18s ease,transform .18s ease}
.field.wide{grid-column:1/-1}
.field span{font-size:13px;font-weight:700;color:var(--text-muted)}
.field:focus-within{border-color:rgba(178,122,50,.3);box-shadow:inset 0 1px 0 rgba(255,255,255,.82),0 14px 30px rgba(178,122,50,.1);transform:translateY(-1px)}
.empty-shell,.placeholder{display:grid;place-items:center;gap:8px;min-height:220px;text-align:center;border-radius:var(--radius-md);border:1px dashed var(--line-strong);background:rgba(250,246,240,.8);color:var(--text-muted)}
.loading-panel{display:grid;gap:12px}
.loading-card{display:grid;gap:12px;padding:16px;border-radius:var(--radius-md);border:1px solid var(--line);background:rgba(255,252,247,.92);overflow:hidden}
.loading-row{display:flex;justify-content:space-between;gap:10px}
.loading-pill,.loading-line,.loading-box{display:block;border-radius:999px;background:linear-gradient(90deg,rgba(235,225,209,.85) 0%,rgba(255,250,243,.96) 48%,rgba(235,225,209,.85) 100%);background-size:220% 100%;animation:loadingShimmer 1.2s linear infinite}
.loading-pill{height:12px}
.loading-line{height:10px}
.loading-box{height:58px;border-radius:18px}
.w-20{width:80px}
.w-24{width:96px}
.w-28{width:112px}
.w-32{width:128px}
.w-40{width:160px}
.w-full{width:100%}
.order-card,.after-card,.product-card,.address-card{padding:16px;border-radius:var(--radius-md);border:1px solid var(--line);background:rgba(255,252,247,.94)}
.items{display:grid;gap:10px;padding:0;list-style:none}
.items li{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px;padding:10px 12px;border-radius:14px;background:rgba(246,239,227,.72)}
.item-name,.truncate1{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.truncate2{display:-webkit-box;overflow:hidden;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.metrics p{display:grid;gap:4px;padding:12px;border-radius:14px;background:rgba(246,239,227,.72)}
.metrics span{font-size:12px;color:var(--text-soft)}
.product-card{display:grid;grid-template-columns:24px 84px minmax(0,1fr);gap:14px}
.product-card.selected{border-color:rgba(178,122,50,.3);box-shadow:0 14px 26px rgba(178,122,50,.12)}
.product-card img,.thumb{width:84px;height:84px;border-radius:18px;background:rgba(246,239,227,.9);object-fit:cover}
.thumb{display:grid;place-items:center;color:var(--text-soft);font-size:13px}
.route,.slow{font-size:13px;color:var(--text-soft)}
.control-input,.control-select{width:100%;min-height:46px;padding:0 14px;border:1px solid rgba(113,86,50,.18);border-radius:16px;color:var(--text);font-size:14px}
.control-input,.control-select,.field-input,.field-select,.field-textarea{background:linear-gradient(180deg,rgba(255,255,255,.96),rgba(247,240,230,.92));border-color:rgba(113,86,50,.18);box-shadow:inset 0 1px 0 rgba(255,255,255,.82),0 10px 22px rgba(39,27,12,.05)}
.control-input,.control-select{min-width:220px}
.control-select,.field-select{appearance:none;background-image:linear-gradient(45deg,transparent 50%,rgba(123,91,48,.85) 50%),linear-gradient(135deg,rgba(123,91,48,.85) 50%,transparent 50%),linear-gradient(180deg,rgba(195,170,134,.7),rgba(195,170,134,.7));background-position:calc(100% - 20px) calc(50% - 2px),calc(100% - 14px) calc(50% - 2px),calc(100% - 38px) 50%;background-size:6px 6px,6px 6px,1px 20px;background-repeat:no-repeat;padding-right:44px}
.control-input::placeholder,.field-input::placeholder,.field-textarea::placeholder{color:#a2917b}
.items-hover{position:relative;margin:12px 0 22px}
.items-toggle{display:flex;align-items:center;justify-content:space-between;gap:12px;width:100%;padding:12px 14px;border:1px solid rgba(113,86,50,.16);border-radius:16px;background:linear-gradient(180deg,rgba(251,247,241,.96),rgba(245,237,226,.94));box-shadow:inset 0 1px 0 rgba(255,255,255,.78),0 10px 24px rgba(39,27,12,.05);color:var(--text);cursor:pointer;text-align:left}
.items-toggle-main,.items-toggle-copy{display:flex;align-items:center;gap:10px}
.items-toggle-copy{min-width:0;flex-direction:column;align-items:flex-start;gap:2px}
.items-toggle-icon{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:12px;background:rgba(178,122,50,.12);color:var(--brand-strong);box-shadow:inset 0 1px 0 rgba(255,255,255,.6)}
.order-link{text-decoration:none;color:var(--brand-strong);font-weight:600}
.card-checkbox{align-self:start;margin-top:4px}
.dialog-items-shell{display:grid;gap:14px}
.dialog-items-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
.dialog-items-list{display:grid;gap:10px;margin:0;padding:0;list-style:none}
.dialog-item-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border-radius:16px;border:1px solid rgba(113,86,50,.14);background:linear-gradient(180deg,rgba(255,253,249,.98),rgba(246,239,229,.94))}
.dialog-item-main{display:grid;gap:4px;min-width:0}
.ship-toast{position:fixed;right:20px;bottom:20px;z-index:50;max-width:320px;padding:12px 16px;border-radius:16px;color:#fff;box-shadow:0 18px 40px rgba(39,27,12,.18)}
.ship-toast.success{background:linear-gradient(135deg,#175947,#1f7a63)}
.ship-toast.error{background:linear-gradient(135deg,#8d2d29,#b63c37)}
.toast-fade-enter-active,.toast-fade-leave-active{transition:opacity .18s ease,transform .18s ease}
.toast-fade-enter-from,.toast-fade-leave-to{opacity:0;transform:translateY(10px)}
@keyframes loadingShimmer{from{background-position:200% 0}to{background-position:-20% 0}}
@media (max-width:1100px){.overview-grid,.workspace-grid,.manage-grid{grid-template-columns:1fr}}
@media (max-width:720px){.merchant-page{gap:14px}.form-grid,.metrics{grid-template-columns:1fr}.surface-head,.toolbar,.bulk-row,.ship-row,.form-actions,.card-head,.items-toggle,.dialog-items-head,.dialog-item-row{flex-direction:column;align-items:stretch}.items li,.product-card{grid-template-columns:1fr}.product-card img,.thumb{display:none}.control-input,.control-select{min-width:0;width:100%}}
</style>
