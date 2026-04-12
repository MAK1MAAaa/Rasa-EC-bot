<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import ListPager from '@/components/ListPager.vue'
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

interface OrderListResponse {
  items: OrderListItem[]
  total: number
  page: number
  page_size: number
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const orders = ref<OrderListItem[]>([])
const error = ref('')
const page = ref(1)
const pageSize = 8
const total = ref(0)

let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const orderStatusLabel = (status: string) => {
  if (status === 'pending_shipment') return '待发货'
  if (status === 'shipped') return '已发货'
  if (status === 'cancelled') return '已取消'
  return status
}

const toOrderDetail = (orderId: string) => {
  router.push({ name: 'OrderDetail', params: { id: orderId } })
}

const loadOrders = async (targetPage = page.value) => {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get<OrderListResponse>('/orders', {
      params: { page: targetPage, page_size: pageSize }
    })
    orders.value = response.data.items || []
    total.value = Number(response.data.total || 0)
    page.value = Number(response.data.page || targetPage)

    const maxPage = Math.max(1, Math.ceil(total.value / pageSize))
    if (page.value > maxPage && total.value > 0) {
      await loadOrders(maxPage)
      return
    }

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

const handlePageChange = async (nextPage: number) => {
  if (nextPage === page.value) {
    return
  }
  await loadOrders(nextPage)
}

const scheduleRealtimeRefresh = () => {
  if (realtimeRefreshTimer) {
    return
  }
  realtimeRefreshTimer = setTimeout(async () => {
    realtimeRefreshTimer = null
    await loadOrders(page.value)
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
      <div>
        <p class="hero-eyebrow">Order Archive</p>
        <h1>我的订单</h1>
        <p class="hero-copy">订单为空时保留同一块列表背景，订单增多后仍延续相同的信息框架和节奏。</p>
      </div>
      <button type="button" class="ghost" @click="router.push('/products')">继续购物</button>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <section class="content-surface">
      <div class="surface-head">
        <div>
          <h2>订单列表</h2>
          <p>按时间倒序展示，点击卡片进入详情，分页时保留当前浏览上下文。</p>
        </div>
        <span class="surface-badge">共 {{ total }} 笔订单</span>
      </div>

      <div v-if="loading" class="surface-state">加载中...</div>

      <div v-else-if="orders.length === 0" class="empty-state">
        <p class="empty-eyebrow">No Orders Yet</p>
        <h3>还没有订单记录</h3>
        <p>完成下单后，这里会继续沿用当前面板样式展示订单、物流和售后入口。</p>
        <button type="button" class="empty-action" @click="router.push('/products')">去下单</button>
      </div>

      <div v-else class="list-wrap">
        <div class="order-grid">
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
              <span>{{ order.contact_email }}</span>
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

        <ListPager
          :page="page"
          :total-pages="totalPages"
          :total-items="total"
          @change="handlePageChange"
        />
      </div>
    </section>
  </section>
</template>

<style scoped>
.orders-page {
  --page-accent: #1f5e57;
  --page-accent-soft: rgba(31, 94, 87, 0.14);
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 18px 40px;
  display: grid;
  gap: 16px;
}

.hero {
  padding: 22px 24px;
  border-radius: 24px;
  background:
    radial-gradient(circle at right top, rgba(201, 247, 240, 0.28), transparent 28%),
    linear-gradient(135deg, #182624 0%, #1f5e57 52%, #8dc8be 100%);
  color: #f2fffd;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-end;
}

.hero-eyebrow,
.empty-eyebrow {
  margin: 0 0 6px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 11px;
}

.hero h1 {
  margin: 0;
  font-size: clamp(30px, 4vw, 38px);
}

.hero-copy {
  margin: 10px 0 0;
  max-width: 560px;
  color: rgba(242, 255, 253, 0.8);
  line-height: 1.7;
}

.ghost {
  border: 1px solid rgba(220, 255, 249, 0.42);
  background: rgba(255, 255, 255, 0.08);
  color: #f2fffd;
  border-radius: 999px;
  padding: 10px 16px;
}

.error {
  margin: 0;
  border-radius: 14px;
  padding: 12px 14px;
  background: #fff1f2;
  color: #be123c;
}

.content-surface {
  min-height: 560px;
  padding: 20px;
  border-radius: 24px;
  border: 1px solid rgba(31, 94, 87, 0.12);
  background:
    radial-gradient(circle at top left, rgba(188, 240, 230, 0.24), transparent 24%),
    linear-gradient(180deg, rgba(252, 255, 253, 0.96), rgba(240, 248, 246, 0.92));
  box-shadow: 0 18px 40px rgba(18, 55, 50, 0.08);
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 18px;
}

.surface-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.surface-head h2,
.empty-state h3 {
  margin: 0;
  color: #153732;
}

.surface-head p,
.empty-state p {
  margin: 8px 0 0;
  color: #62706d;
  line-height: 1.7;
}

.surface-badge {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--page-accent-soft);
  color: var(--page-accent);
  font-size: 12px;
  white-space: nowrap;
}

.surface-state,
.empty-state,
.list-wrap {
  min-height: 100%;
  border-radius: 20px;
  border: 1px solid rgba(31, 94, 87, 0.1);
  background: rgba(255, 255, 255, 0.72);
}

.surface-state,
.empty-state {
  display: grid;
  place-items: center;
  text-align: center;
  padding: 36px 24px;
}

.empty-state {
  justify-items: center;
  gap: 8px;
}

.empty-action,
.detail-btn {
  border: none;
  cursor: pointer;
}

.empty-action {
  padding: 12px 18px;
  border-radius: 999px;
  background: #1f5e57;
  color: #f2fffd;
}

.list-wrap {
  padding: 16px;
  display: grid;
  gap: 14px;
  align-content: start;
}

.order-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}

.order-card {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(31, 94, 87, 0.12);
  border-radius: 18px;
  padding: 16px;
  cursor: pointer;
  display: grid;
  gap: 10px;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.order-card:hover {
  border-color: #4b8b83;
  box-shadow: 0 12px 28px rgba(29, 87, 80, 0.12);
  transform: translateY(-1px);
}

.row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.row.muted {
  color: #687572;
  font-size: 13px;
}

.status {
  background: #dff5ef;
  color: #1b5a53;
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.addr {
  color: #37423f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price {
  color: #143632;
}

.card-footer {
  margin-top: 4px;
  display: flex;
  justify-content: flex-end;
}

.detail-btn {
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  background: #163f3b;
  color: #f2fffd;
}

@media (max-width: 760px) {
  .hero,
  .surface-head {
    display: grid;
    align-items: start;
  }

  .content-surface {
    min-height: 500px;
  }

  .row {
    flex-wrap: wrap;
  }

  .addr {
    white-space: normal;
  }
}
</style>
