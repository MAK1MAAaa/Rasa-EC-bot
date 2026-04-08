<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'

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
  estimated_delivery_at?: string | null
  route_plan: string[]
}

interface AfterSalesItem {
  id: string
  order_id: string
  type: 'return' | 'exchange' | string
  reason?: string | null
  status: string
  created_at: string
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
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const order = ref<OrderDetail | null>(null)
const error = ref('')
let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

const afterSalesSubmitting = ref(false)
const afterSalesError = ref('')
const afterSalesSuccess = ref('')
const afterSalesForm = reactive({
  type: 'return' as 'return' | 'exchange',
  reason: ''
})

const orderId = computed(() => String(route.params.id || '').trim())
const terminalAfterSalesStatus = new Set(['merchant_rejected', 'completed', 'cancelled'])

const hasActiveAfterSales = computed(() => {
  if (!order.value) return false
  return order.value.after_sales.some((item) => !terminalAfterSalesStatus.has(item.status))
})

const canApplyAfterSales = computed(() => {
  if (!order.value) return false
  return order.value.status === 'shipped' && !hasActiveAfterSales.value
})

const orderStatusLabel = (status: string) => {
  if (status === 'pending_shipment') return '待发货'
  if (status === 'shipped') return '已发货'
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

const clearAfterSalesNotice = () => {
  afterSalesError.value = ''
  afterSalesSuccess.value = ''
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
      after_sales: response.data.after_sales || []
    }
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
  if (event.event !== 'order_changed' && event.event !== 'after_sales_changed') {
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

onMounted(async () => {
  await loadOrder(orderId.value)
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

        <article class="panel" v-if="order.logistics">
          <h2>物流轨迹</h2>
          <p><strong>运单号：</strong>{{ order.logistics.tracking_no || '-' }}</p>
          <p><strong>状态：</strong>{{ order.logistics.status }}</p>
          <p><strong>当前位置：</strong>{{ order.logistics.current_location || '-' }}</p>
          <p>
            <strong>预计送达：</strong>
            {{ order.logistics.estimated_delivery_at ? new Date(order.logistics.estimated_delivery_at).toLocaleString() : '-' }}
          </p>
          <div class="route-list">
            <span v-for="(point, idx) in order.logistics.route_plan || []" :key="`${point}-${idx}`" class="route-chip">
              {{ point }}
            </span>
            <span v-if="!order.logistics.route_plan || order.logistics.route_plan.length === 0" class="muted-small">暂无路线信息</span>
          </div>
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

          <form v-if="canApplyAfterSales" class="after-sales-form" @submit.prevent="submitAfterSales">
            <label>
              售后类型
              <select v-model="afterSalesForm.type">
                <option value="return">退货</option>
                <option value="exchange">换货</option>
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
          <p v-else class="muted-small">
            {{ order.status !== 'shipped' ? '订单发货后才可申请退货/换货' : '当前已有进行中的售后申请，请等待商家处理' }}
          </p>
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

.route-chip {
  border-radius: 999px;
  border: 1px solid #d8cbb4;
  background: #fff9ee;
  color: #5d523f;
  padding: 4px 10px;
  font-size: 12px;
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

.after-sales-form label {
  display: grid;
  gap: 6px;
  font-size: 13px;
  color: #5d523f;
}

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
}
</style>
