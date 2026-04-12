<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'
import { isAmapEnabled, loadAmap } from '@/utils/amap'

interface OrderDetailItem {
  id: string
  product_id: string
  product_name: string
  unit_price: number
  quantity: number
  subtotal: number
  product_link: string
}

interface OrderLogistics {
  tracking_no?: string | null
  status: string
  current_location?: string | null
  current_lng?: number | null
  current_lat?: number | null
  estimated_delivery_at?: string | null
  updated_at?: string | null
  route_plan: string[]
  route_geo?: Array<{ name: string; lng: number; lat: number }>
}

interface AfterSalesItem {
  id: string
  order_id: string
  type: 'return' | 'exchange' | string
  reason?: string | null
  status: string
  created_at: string
}

interface LogisticsComplaintItem {
  id: string
  order_id: string
  reason: string
  status: string
  resolution_note?: string | null
  created_at: string
  updated_at: string
}

interface OrderDetail {
  id: string
  status: string
  address: string
  contact_email: string
  total_amount: number
  created_at: string
  shop_id: string
  shop_name: string
  items: OrderDetailItem[]
  logistics?: OrderLogistics | null
  after_sales: AfterSalesItem[]
  logistics_complaints: LogisticsComplaintItem[]
}

type AfterSalesStage = 'pending_shipment' | 'in_transit' | 'delivered' | 'unsupported'
type RouteNodeState = 'done' | 'current' | 'pending'
type RouteGeoPoint = { name: string; lng: number; lat: number }

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const order = ref<OrderDetail | null>(null)
const error = ref('')
let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null
const mapContainerRef = ref<HTMLElement | null>(null)
const mapLoading = ref(false)
const mapError = ref('')
const mapEnabled = isAmapEnabled()
let amapInstance: any | null = null

const afterSalesSubmitting = ref(false)
const afterSalesError = ref('')
const afterSalesSuccess = ref('')
const afterSalesForm = reactive({
  type: 'return' as 'return' | 'exchange',
  reason: ''
})
const orderActionLoading = ref(false)
const orderActionError = ref('')
const orderActionSuccess = ref('')
const shippingForm = reactive({
  address: '',
  contact_email: ''
})
const complaintSubmitting = ref(false)
const complaintError = ref('')
const complaintSuccess = ref('')
const complaintForm = reactive({
  reason: ''
})

const orderId = computed(() => String(route.params.id || '').trim())
const terminalAfterSalesStatus = new Set(['merchant_rejected', 'completed', 'cancelled'])
const terminalComplaintStatus = new Set(['resolved', 'rejected', 'cancelled'])

const hasActiveAfterSales = computed(() => {
  if (!order.value) return false
  return order.value.after_sales.some((item) => !terminalAfterSalesStatus.has(item.status))
})

const hasActiveComplaint = computed(() => {
  if (!order.value) return false
  return order.value.logistics_complaints.some((item) => !terminalComplaintStatus.has(item.status))
})

const logisticsStatus = computed(() => {
  return (order.value?.logistics?.status || '').trim().toLowerCase()
})

const canCancelOrder = computed(() => order.value?.status === 'pending_shipment')
const canUpdateShipping = computed(() => order.value?.status === 'pending_shipment')
const canCreateComplaint = computed(() => {
  if (!order.value?.logistics) return false
  return order.value.status === 'shipped' && !hasActiveComplaint.value
})

const afterSalesStage = computed<AfterSalesStage>(() => {
  if (!order.value) return 'unsupported'
  if (order.value.status === 'pending_shipment') return 'pending_shipment'
  if (order.value.status !== 'shipped') return 'unsupported'
  if (logisticsStatus.value === 'delivered') return 'delivered'
  return 'in_transit'
})

const availableAfterSalesTypes = computed<Array<'return' | 'exchange'>>(() => {
  if (afterSalesStage.value === 'pending_shipment') return ['return']
  if (afterSalesStage.value === 'delivered') return ['return', 'exchange']
  return []
})

const canApplyAfterSales = computed(() => {
  if (!order.value) return false
  return availableAfterSalesTypes.value.length > 0 && !hasActiveAfterSales.value
})

const afterSalesHint = computed(() => {
  if (!order.value) return '当前订单暂不支持售后申请'
  if (hasActiveAfterSales.value) return '当前已有进行中的售后申请，请等待商家处理'
  if (afterSalesStage.value === 'pending_shipment') return '商品未发货：可直接申请退货'
  if (afterSalesStage.value === 'in_transit') return '商品运输中：暂不支持退货，请签收后申请更多售后帮助'
  if (afterSalesStage.value === 'delivered') return '商品已送达：可申请退货或换货等售后帮助'
  return '当前订单暂不支持售后申请'
})

const logisticsStatusLabel = (status: string) => {
  if (status === 'in_transit') return '运输中'
  if (status === 'delivered') return '已送达'
  return status || '-'
}

const logisticsRouteNodes = computed<Array<{ point: string; state: RouteNodeState }>>(() => {
  const routePlan = order.value?.logistics?.route_plan || []
  if (!Array.isArray(routePlan) || routePlan.length === 0) return []

  const cleanedPlan = routePlan.map((item) => String(item || '').trim()).filter((item) => !!item)
  if (cleanedPlan.length === 0) return []

  const currentLocation = (order.value?.logistics?.current_location || '').trim()
  let currentIndex = cleanedPlan.findIndex((item) => item === currentLocation)
  if (logisticsStatus.value === 'delivered') {
    currentIndex = cleanedPlan.length - 1
  } else if (currentIndex < 0) {
    currentIndex = 0
  }

  return cleanedPlan.map((point, index) => {
    if (index < currentIndex) return { point, state: 'done' as RouteNodeState }
    if (index === currentIndex) return { point, state: 'current' as RouteNodeState }
    return { point, state: 'pending' as RouteNodeState }
  })
})

const logisticsRouteGeo = computed<RouteGeoPoint[]>(() => {
  const points = order.value?.logistics?.route_geo
  if (!Array.isArray(points)) return []
  return points
    .map((item) => ({
      name: String(item?.name || '').trim(),
      lng: Number(item?.lng),
      lat: Number(item?.lat)
    }))
    .filter((item) => item.name && Number.isFinite(item.lng) && Number.isFinite(item.lat))
})

const hasMapCoordinates = computed(() => logisticsRouteGeo.value.length > 0)

const logisticsRouteGeoSignature = computed(() =>
  logisticsRouteGeo.value.map((item) => `${item.name}:${item.lng}:${item.lat}`).join('|')
)

const currentMapCenter = computed<[number, number] | null>(() => {
  const lng = Number(order.value?.logistics?.current_lng)
  const lat = Number(order.value?.logistics?.current_lat)
  if (Number.isFinite(lng) && Number.isFinite(lat)) return [lng, lat]
  if (logisticsRouteGeo.value.length === 0) return null
  const last = logisticsRouteGeo.value[logisticsRouteGeo.value.length - 1]
  return [last.lng, last.lat]
})

const currentRouteGeoPoint = computed<RouteGeoPoint | null>(() => {
  const currentLocation = (order.value?.logistics?.current_location || '').trim()
  const matchedPoint = logisticsRouteGeo.value.find((item) => item.name === currentLocation)
  if (matchedPoint) return matchedPoint
  const center = currentMapCenter.value
  if (!center) return null
  return {
    name: currentLocation || '当前位置',
    lng: center[0],
    lat: center[1]
  }
})

const mapOverlayMessage = computed(() => {
  if (mapError.value) return mapError.value
  if (!hasMapCoordinates.value) return '暂无可用坐标，已使用文本轨迹展示。'
  return ''
})

const destroyLogisticsMap = () => {
  if (amapInstance) {
    amapInstance.destroy()
    amapInstance = null
  }
}

const createMapMarker = (AMap: any, position: [number, number], title: string, label: string) =>
  new AMap.Marker({
    position,
    title,
    label: {
      content: label,
      direction: 'top'
    }
  })

const renderLogisticsMap = async () => {
  if (!mapEnabled) return
  await nextTick()
  if (!mapContainerRef.value) return
  if (!order.value?.logistics) {
    mapError.value = ''
    destroyLogisticsMap()
    return
  }
  if (!hasMapCoordinates.value) {
    mapError.value = ''
    destroyLogisticsMap()
    return
  }
  mapLoading.value = true
  mapError.value = ''
  try {
    const AMap = await loadAmap()
    await nextTick()
    const mapContainer = mapContainerRef.value
    if (!mapContainer) return

    if (!amapInstance || amapInstance.getContainer?.() !== mapContainer) {
      destroyLogisticsMap()
      amapInstance = new AMap.Map(mapContainer, {
        zoom: 5,
        resizeEnable: true
      })
    } else {
      amapInstance.clearMap()
    }

    const path = logisticsRouteGeo.value.map((item) => [item.lng, item.lat])
    const overlays: any[] = []

    if (path.length > 1) {
      const polyline = new AMap.Polyline({
        path,
        strokeColor: '#315f58',
        strokeWeight: 6,
        strokeOpacity: 0.9
      })
      overlays.push(polyline)
    }

    const firstPoint = logisticsRouteGeo.value[0]
    if (firstPoint) {
      overlays.push(createMapMarker(AMap, [firstPoint.lng, firstPoint.lat], firstPoint.name, '起点'))
    }

    const lastPoint = logisticsRouteGeo.value[logisticsRouteGeo.value.length - 1]
    if (lastPoint) {
      overlays.push(createMapMarker(AMap, [lastPoint.lng, lastPoint.lat], lastPoint.name, '终点'))
    }

    const currentPoint = currentRouteGeoPoint.value
    if (currentPoint) {
      overlays.push(
        createMapMarker(
          AMap,
          [currentPoint.lng, currentPoint.lat],
          order.value.logistics.current_location || currentPoint.name,
          '当前位置'
        )
      )
    }

    if (overlays.length > 0) {
      amapInstance.add(overlays)
      amapInstance.setFitView(overlays, false, [32, 32, 32, 32], 12)
    } else if (currentMapCenter.value) {
      amapInstance.setCenter(currentMapCenter.value)
      amapInstance.setZoom(9)
    }
  } catch {
    destroyLogisticsMap()
    mapError.value = '地图加载失败，已自动降级为文本轨迹。'
  } finally {
    mapLoading.value = false
  }
}

const orderStatusLabel = (status: string) => {
  if (status === 'pending_shipment') return '待发货'
  if (status === 'shipped') return '已发货'
  if (status === 'cancelled') return '已取消'
  return status
}

const afterSalesTypeLabel = (type: string) => {
  if (type === 'return') return '退货'
  if (type === 'exchange') return '换货'
  return type
}

const afterSalesStatusLabel = (status: string) => {
  if (status === 'submitted') return '待商家处理'
  if (status === 'merchant_approved') return '商家已同意'
  if (status === 'processing') return '处理中'
  if (status === 'merchant_rejected') return '商家已拒绝'
  if (status === 'completed') return '已完成'
  if (status === 'cancelled') return '已取消'
  return status
}

const complaintStatusLabel = (status: string) => {
  if (status === 'submitted') return '待处理'
  if (status === 'processing') return '处理中'
  if (status === 'resolved') return '已解决'
  if (status === 'rejected') return '已驳回'
  if (status === 'cancelled') return '已取消'
  return status
}

const clearAfterSalesNotice = () => {
  afterSalesError.value = ''
  afterSalesSuccess.value = ''
}

const clearOrderActionNotice = () => {
  orderActionError.value = ''
  orderActionSuccess.value = ''
}

const clearComplaintNotice = () => {
  complaintError.value = ''
  complaintSuccess.value = ''
}

const parseErr = (err: any, fallback: string) => {
  const detail = err?.response?.data?.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || JSON.stringify(item)).join('；')
  }
  return JSON.stringify(detail)
}

const loadOrder = async (id: string) => {
  if (!id) {
    error.value = '订单 ID 无效'
    order.value = null
    return
  }

  loading.value = true
  error.value = ''
  clearAfterSalesNotice()

  try {
    const response = await api.get(`/orders/${id}`)
    order.value = {
      ...response.data,
      after_sales: response.data.after_sales || [],
      logistics_complaints: response.data.logistics_complaints || []
    }
    shippingForm.address = String(response.data.address || '')
    shippingForm.contact_email = String(response.data.contact_email || '')
  } catch (err: any) {
    order.value = null
    error.value = parseErr(err, '订单详情加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const submitAfterSales = async () => {
  if (!order.value) return
  clearAfterSalesNotice()
  if (!availableAfterSalesTypes.value.includes(afterSalesForm.type)) {
    afterSalesError.value = '当前阶段不支持该售后类型，请调整后重试'
    return
  }

  const reason = afterSalesForm.reason.trim()
  if (!reason) {
    afterSalesError.value = '请填写售后原因'
    return
  }

  afterSalesSubmitting.value = true
  try {
    await api.post(`/orders/${order.value.id}/after-sales`, {
      type: afterSalesForm.type,
      reason
    })
    afterSalesSuccess.value = '售后申请已提交'
    afterSalesForm.reason = ''
    await loadOrder(order.value.id)
  } catch (err: any) {
    afterSalesError.value = parseErr(err, '售后申请提交失败')
  } finally {
    afterSalesSubmitting.value = false
  }
}

const submitCancelOrder = async () => {
  if (!order.value || !canCancelOrder.value || orderActionLoading.value) return
  clearOrderActionNotice()
  if (!window.confirm(`确认取消订单 ${order.value.id} 吗？`)) return

  orderActionLoading.value = true
  try {
    const response = await api.post(`/orders/${order.value.id}/cancel`)
    order.value = response.data
    shippingForm.address = String(response.data.address || '')
    shippingForm.contact_email = String(response.data.contact_email || '')
    orderActionSuccess.value = '订单已取消'
  } catch (err: any) {
    orderActionError.value = parseErr(err, '取消订单失败')
  } finally {
    orderActionLoading.value = false
  }
}

const submitUpdateShipping = async () => {
  if (!order.value || !canUpdateShipping.value || orderActionLoading.value) return
  clearOrderActionNotice()

  const address = shippingForm.address.trim()
  const contactEmail = shippingForm.contact_email.trim()
  if (!address) {
    orderActionError.value = '请填写新的收货地址'
    return
  }
  if (!contactEmail) {
    orderActionError.value = '请填写联系邮箱'
    return
  }

  orderActionLoading.value = true
  try {
    const response = await api.patch(`/orders/${order.value.id}/shipping`, {
      address,
      contact_email: contactEmail
    })
    order.value = response.data
    shippingForm.address = String(response.data.address || '')
    shippingForm.contact_email = String(response.data.contact_email || '')
    orderActionSuccess.value = '收货信息已更新'
  } catch (err: any) {
    orderActionError.value = parseErr(err, '修改收货信息失败')
  } finally {
    orderActionLoading.value = false
  }
}

const submitLogisticsComplaint = async () => {
  if (!order.value || !canCreateComplaint.value || complaintSubmitting.value) return
  clearComplaintNotice()

  const reason = complaintForm.reason.trim()
  if (!reason) {
    complaintError.value = '请填写投诉原因'
    return
  }

  complaintSubmitting.value = true
  try {
    await api.post(`/orders/${order.value.id}/logistics-complaints`, { reason })
    complaintForm.reason = ''
    complaintSuccess.value = '物流投诉已提交'
    await loadOrder(order.value.id)
  } catch (err: any) {
    complaintError.value = parseErr(err, '提交物流投诉失败')
  } finally {
    complaintSubmitting.value = false
  }
}

const goBack = () => router.push('/orders')

const scheduleRealtimeRefresh = () => {
  if (realtimeRefreshTimer) {
    return
  }
  realtimeRefreshTimer = setTimeout(async () => {
    realtimeRefreshTimer = null
    await loadOrder(orderId.value)
  }, 320)
}

const handleRealtimeEvent = (event: RealtimeEvent) => {
  if (!order.value) {
    return
  }
  if (event.event !== 'order_changed' && event.event !== 'after_sales_changed' && event.event !== 'logistics_complaint_changed') {
    return
  }
  if (String(event.data?.order_id || '') !== order.value.id) {
    return
  }
  scheduleRealtimeRefresh()
}

watch(orderId, (id) => {
  loadOrder(id)
})

watch(availableAfterSalesTypes, (types) => {
  if (types.length === 0) return
  if (!types.includes(afterSalesForm.type)) {
    afterSalesForm.type = types[0]
  }
})

watch(
  () => [
    order.value?.id,
    order.value?.logistics?.updated_at,
    order.value?.logistics?.current_lng,
    order.value?.logistics?.current_lat,
    logisticsRouteGeoSignature.value
  ],
  () => {
    if (!mapEnabled) return
    void renderLogisticsMap()
  },
  { flush: 'post' }
)

onMounted(async () => {
  await loadOrder(orderId.value)
  if (mapEnabled) {
    await renderLogisticsMap()
  }
  realtimeClient = createRealtimeClient({
    token: authStore.token,
    onEvent: handleRealtimeEvent
  })
})

onBeforeUnmount(() => {
  if (realtimeRefreshTimer) {
    clearTimeout(realtimeRefreshTimer)
    realtimeRefreshTimer = null
  }
  destroyLogisticsMap()
  realtimeClient?.close()
  realtimeClient = null
})
</script>

<template>
  <section class="order-detail-page">
    <header class="page-top">
      <button type="button" class="back-btn" @click="goBack">返回列表</button>
      <h1>订单详情</h1>
    </header>

    <div v-if="loading" class="state-card">加载中...</div>
    <p v-else-if="error" class="error">{{ error }}</p>
    <div v-else-if="!order" class="state-card">订单不存在</div>

    <template v-else>
      <section class="summary-card">
        <div class="summary-grid">
          <p><strong>订单号：</strong>{{ order.id }}</p>
          <p><strong>店铺：</strong>{{ order.shop_name }}</p>
          <p><strong>状态：</strong>{{ orderStatusLabel(order.status) }}</p>
          <p><strong>下单时间：</strong>{{ new Date(order.created_at).toLocaleString() }}</p>
          <p><strong>联系邮箱：</strong>{{ order.contact_email }}</p>
          <p><strong>收货地址：</strong>{{ order.address }}</p>
        </div>
        <div class="summary-total">总金额：¥ {{ order.total_amount.toFixed(2) }}</div>
      </section>

      <section class="detail-layout">
        <article class="panel">
          <h2>订单操作</h2>
          <p v-if="orderActionError" class="error-text">{{ orderActionError }}</p>
          <p v-if="orderActionSuccess" class="success-text">{{ orderActionSuccess }}</p>

          <div class="action-stack">
            <button type="button" class="danger-btn" :disabled="!canCancelOrder || orderActionLoading" @click="submitCancelOrder">
              {{ orderActionLoading && canCancelOrder ? '处理中...' : '取消订单' }}
            </button>
            <p class="muted-small">
              {{ canCancelOrder ? '待发货订单可直接取消，系统会自动恢复库存。' : '当前订单状态不支持取消。' }}
            </p>
          </div>

          <form class="after-sales-form compact-form" @submit.prevent="submitUpdateShipping">
            <label>
              新收货地址
              <textarea
                v-model="shippingForm.address"
                rows="3"
                maxlength="300"
                :disabled="!canUpdateShipping || orderActionLoading"
                placeholder="请输入新的收货地址"
              ></textarea>
            </label>
            <label>
              联系邮箱
              <input
                v-model="shippingForm.contact_email"
                type="email"
                :disabled="!canUpdateShipping || orderActionLoading"
                placeholder="请输入联系邮箱"
              >
            </label>
            <button type="submit" :disabled="!canUpdateShipping || orderActionLoading">
              {{ orderActionLoading && canUpdateShipping ? '保存中...' : '修改收货信息' }}
            </button>
          </form>
        </article>

        <article class="panel panel-items">
          <h2>商品清单</h2>
          <ul class="item-list">
            <li v-for="item in order.items" :key="item.id">
              <a :href="`/products/${item.product_id}`" target="_blank">{{ item.product_name }}</a>
              <span>x {{ item.quantity }}</span>
              <strong>¥ {{ item.subtotal.toFixed(2) }}</strong>
            </li>
          </ul>
        </article>

        <article class="panel">
          <h2>物流轨迹</h2>
          <template v-if="order.logistics">
            <p><strong>运单号：</strong>{{ order.logistics.tracking_no || '-' }}</p>
            <p><strong>状态：</strong>{{ logisticsStatusLabel(order.logistics.status) }}</p>
            <p><strong>当前位置：</strong>{{ order.logistics.current_location || '-' }}</p>
            <p>
              <strong>预计送达：</strong>
              {{ order.logistics.estimated_delivery_at ? new Date(order.logistics.estimated_delivery_at).toLocaleString() : '-' }}
            </p>
            <div class="route-list">
              <span
                v-for="(node, idx) in logisticsRouteNodes"
                :key="`${node.point}-${idx}`"
                :class="['route-chip', `state-${node.state}`]"
              >
                {{ node.point }}
              </span>
              <span v-if="logisticsRouteNodes.length === 0" class="muted-small">暂无路线信息</span>
            </div>
            <div v-if="mapEnabled" class="map-card">
              <div class="map-headline">
                <p class="map-title">地图预览</p>
                <span class="map-badge">{{ hasMapCoordinates ? `${logisticsRouteGeo.length} 个站点` : '文本降级' }}</span>
              </div>
              <div class="map-stage">
                <div
                  ref="mapContainerRef"
                  class="map-container"
                  :class="{ 'is-muted': mapLoading || !!mapOverlayMessage }"
                ></div>
                <div v-if="mapLoading || !!mapOverlayMessage" class="map-overlay">
                  <div v-if="mapLoading" class="map-skeleton"></div>
                  <p v-else class="muted-small">{{ mapOverlayMessage }}</p>
                </div>
              </div>
              <p class="muted-small">文本轨迹始终保留，地图异常时自动降级。</p>
            </div>
          </template>
          <p v-else class="muted-small">订单暂未发货，暂无物流轨迹</p>
        </article>

        <article class="panel">
          <h2>物流投诉</h2>
          <p v-if="complaintError" class="error-text">{{ complaintError }}</p>
          <p v-if="complaintSuccess" class="success-text">{{ complaintSuccess }}</p>

          <div v-if="order.logistics_complaints.length === 0" class="muted-small">当前还没有物流投诉记录</div>
          <ul v-else class="after-sales-list">
            <li v-for="item in order.logistics_complaints" :key="item.id" class="after-sales-item">
              <div class="row">
                <strong>投诉 {{ item.id }}</strong>
                <span class="status">{{ complaintStatusLabel(item.status) }}</span>
              </div>
              <p class="muted-small">{{ new Date(item.updated_at || item.created_at).toLocaleString() }}</p>
              <p class="muted-small">{{ item.reason }}</p>
              <p v-if="item.resolution_note" class="muted-small">{{ item.resolution_note }}</p>
            </li>
          </ul>

          <p class="muted-small">
            {{ canCreateComplaint ? '如物流长时间未更新或配送异常，可提交物流投诉。' : '仅已发货且无进行中投诉的订单可提交物流投诉。' }}
          </p>
          <form class="after-sales-form compact-form" @submit.prevent="submitLogisticsComplaint">
            <label>
              投诉原因
              <textarea
                v-model="complaintForm.reason"
                rows="3"
                maxlength="300"
                :disabled="!canCreateComplaint || complaintSubmitting"
                placeholder="请说明物流问题，例如长时间未更新、派送异常等"
              ></textarea>
            </label>
            <button type="submit" :disabled="!canCreateComplaint || complaintSubmitting">
              {{ complaintSubmitting ? '提交中...' : '提交物流投诉' }}
            </button>
          </form>
        </article>

        <article class="panel">
          <h2>售后服务</h2>
          <p v-if="afterSalesError" class="error-text">{{ afterSalesError }}</p>
          <p v-if="afterSalesSuccess" class="success-text">{{ afterSalesSuccess }}</p>

          <div v-if="order.after_sales.length === 0" class="muted-small">暂无售后申请记录</div>
          <ul v-else class="after-sales-list">
            <li v-for="item in order.after_sales" :key="item.id" class="after-sales-item">
              <div class="row">
                <strong>{{ afterSalesTypeLabel(item.type) }}</strong>
                <span class="status">{{ afterSalesStatusLabel(item.status) }}</span>
              </div>
              <p class="muted-small">{{ new Date(item.created_at).toLocaleString() }}</p>
              <p class="muted-small">{{ item.reason || '无备注' }}</p>
            </li>
          </ul>

          <p class="muted-small">{{ afterSalesHint }}</p>
          <form v-if="canApplyAfterSales" class="after-sales-form" @submit.prevent="submitAfterSales">
            <label>
              售后类型
              <select v-model="afterSalesForm.type">
                <option v-if="availableAfterSalesTypes.includes('return')" value="return">退货</option>
                <option v-if="availableAfterSalesTypes.includes('exchange')" value="exchange">换货</option>
              </select>
            </label>
            <label>
              原因说明
              <textarea
                v-model="afterSalesForm.reason"
                rows="3"
                maxlength="300"
                placeholder="请填写退换货原因，便于商家快速处理"
              ></textarea>
            </label>
            <button type="submit" :disabled="afterSalesSubmitting">
              {{ afterSalesSubmitting ? '提交中...' : '提交售后申请' }}
            </button>
          </form>
        </article>
      </section>
    </template>
  </section>
</template>

<style scoped>
.order-detail-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 18px 38px;
  display: grid;
  gap: 14px;
}

.page-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-top h1 {
  margin: 0;
  color: #312819;
}

.back-btn {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  background: #2f2413;
  color: #fff6e8;
  cursor: pointer;
}

.error {
  color: var(--danger);
  margin: 0;
}

.state-card {
  background: var(--surface-strong);
  border: 1px dashed #d8cbb5;
  border-radius: 16px;
  padding: 30px;
  text-align: center;
  color: #6f6658;
}

.summary-card {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
  color: #4d4438;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 16px;
}

.summary-grid p {
  margin: 0;
}

.summary-total {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #d6c8ad;
  color: #3f2b10;
  font-size: 18px;
  font-weight: 700;
}

.detail-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.panel {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
  color: #4d4438;
}

.panel-items {
  grid-column: 1 / -1;
}

.panel h2 {
  margin: 0 0 10px;
  color: #32291a;
}

.item-list,
.after-sales-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.item-list li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
}

.item-list a {
  color: #5a421d;
  text-decoration: none;
}

.route-list {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.map-card {
  margin-top: 12px;
  border: 1px solid #d8cbb4;
  border-radius: 12px;
  background: #fffdf8;
  padding: 10px;
  display: grid;
  gap: 8px;
}

.map-title {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: #5b4f3a;
}

.map-headline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.map-badge {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: #315f58;
  background: #e7f6f2;
}

.map-stage {
  position: relative;
}

.map-container {
  width: 100%;
  height: 230px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #e6d9bf;
  background: linear-gradient(180deg, #fffaf0 0%, #f6eee0 100%);
}

.map-container.is-muted {
  opacity: 0.22;
  filter: saturate(0.4);
}

.map-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 14px;
}

.map-skeleton {
  width: 100%;
  height: 230px;
  border-radius: 10px;
  background: linear-gradient(90deg, #f6ede0 25%, #fff8eb 45%, #f6ede0 65%);
  background-size: 300% 100%;
  animation: map-shimmer 1.2s linear infinite;
}

@keyframes map-shimmer {
  from {
    background-position: 100% 0;
  }
  to {
    background-position: 0 0;
  }
}

.route-chip {
  border-radius: 999px;
  border: 1px solid #d8cbb4;
  background: #fff9ee;
  color: #5d523f;
  padding: 4px 10px;
  font-size: 12px;
}

.route-chip.state-done {
  background: #ecfdf3;
  border-color: #86efac;
  color: #166534;
}

.route-chip.state-current {
  background: #e0f2fe;
  border-color: #7dd3fc;
  color: #0c4a6e;
  font-weight: 700;
}

.row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.status {
  background: #f1dfbd;
  color: #54401f;
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.after-sales-item {
  border: 1px solid #eadbc2;
  border-radius: 10px;
  padding: 10px;
  background: #fff9ee;
  display: grid;
  gap: 6px;
}

.after-sales-form {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.action-stack {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}

.after-sales-form label {
  display: grid;
  gap: 6px;
  font-size: 13px;
  color: #5d523f;
}

.after-sales-form input,
.after-sales-form select,
.after-sales-form textarea,
.after-sales-form button {
  border: 1px solid #d8cbb4;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fffcf5;
}

.after-sales-form button {
  border: none;
  background: #2f2413;
  color: #fff7ea;
}

.danger-btn {
  border: none;
  border-radius: 10px;
  padding: 10px 12px;
  background: #9f1239;
  color: #fff7ea;
}

.danger-btn:disabled,
.after-sales-form button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.compact-form {
  margin-top: 0;
}

.muted-small {
  margin: 0;
  color: #71685a;
  font-size: 13px;
}

.error-text {
  margin: 0;
  color: #be123c;
  font-size: 13px;
}

.success-text {
  margin: 0;
  color: #0f766e;
  font-size: 13px;
}

@media (max-width: 980px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .detail-layout {
    grid-template-columns: 1fr;
  }

  .map-container,
  .map-skeleton {
    height: 190px;
  }
}
</style>

