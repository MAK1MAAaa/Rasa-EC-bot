<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'

interface OrderListItem {
  id: string
  status: string
  address: string
  contact_email: string
  total_amount: number
  item_count: number
  created_at: string
  shop_id: string
  shop_name: string
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const orders = ref<OrderListItem[]>([])
const error = ref('')
let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

const orderStatusLabel = (status: string) => {
  if (status === 'pending_shipment') return '待发货'
  if (status === 'shipped') return '已发货'
  return status
}

const toOrderDetail = (orderId: string) => {
  router.push({ name: 'OrderDetail', params: { id: orderId } })
}

const loadOrders = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/orders')
    orders.value = response.data.items || []

    // Keep compatibility with old links such as /orders?orderId=ORDxxx.
    const queryOrderId = typeof route.query.orderId === 'string' ? route.query.orderId.trim() : ''
    if (queryOrderId) {
      router.replace({ name: 'OrderDetail', params: { id: queryOrderId } })
    }
  } catch {
    error.value = '订单加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const scheduleRealtimeRefresh = () => {
  if (realtimeRefreshTimer) {
    return
  }
  realtimeRefreshTimer = setTimeout(async () => {
    realtimeRefreshTimer = null
    await loadOrders()
  }, 320)
}

const handleRealtimeEvent = (event: RealtimeEvent) => {
  if (event.event === 'order_changed' || event.event === 'after_sales_changed') {
    scheduleRealtimeRefresh()
  }
}

onMounted(async () => {
  await loadOrders()
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
  <section class="orders-page">
    <header class="hero">
      <h1>我的订单</h1>
      <p>点击订单卡片进入详情页，查看商品、物流与售后信息。</p>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="loading" class="state-card">加载中...</div>
    <div v-else-if="orders.length === 0" class="state-card">暂无订单</div>

    <div v-else class="order-grid">
      <article v-for="order in orders" :key="order.id" class="order-card" @click="toOrderDetail(order.id)">
        <div class="row">
          <strong>{{ order.id }}</strong>
          <span class="status">{{ orderStatusLabel(order.status) }}</span>
        </div>

        <div class="row muted">
          <span>{{ new Date(order.created_at).toLocaleString() }}</span>
          <span>{{ order.item_count }} 件商品</span>
        </div>

        <div class="row muted">
          <span>{{ order.shop_name }}</span>
        </div>

        <div class="row">
          <span class="addr">{{ order.address }}</span>
          <strong class="price">¥ {{ order.total_amount.toFixed(2) }}</strong>
        </div>

        <div class="card-footer">
          <button type="button" class="detail-btn" @click.stop="toOrderDetail(order.id)">查看详情</button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.orders-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 18px 38px;
}

.hero {
  margin-bottom: 16px;
}

.hero h1 {
  margin: 0;
  color: #312819;
}

.hero p {
  margin: 8px 0 0;
  color: #6d6458;
}

.error {
  color: var(--danger);
}

.state-card {
  background: var(--surface-strong);
  border: 1px dashed #d8cbb5;
  border-radius: 16px;
  padding: 30px;
  text-align: center;
  color: #6f6658;
}

.order-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}

.order-card {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  cursor: pointer;
  display: grid;
  gap: 8px;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.order-card:hover {
  border-color: #b6863e;
  box-shadow: 0 10px 28px rgba(64, 42, 14, 0.12);
  transform: translateY(-1px);
}

.row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.row.muted {
  color: #706759;
  font-size: 13px;
}

.status {
  background: #f1dfbd;
  color: #54401f;
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.addr {
  color: #4f463a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price {
  color: #3f2d12;
}

.card-footer {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}

.detail-btn {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  background: #2f2413;
  color: #fff6e8;
  cursor: pointer;
}
</style>
