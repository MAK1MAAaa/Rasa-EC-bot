<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import ListPager from '@/components/ListPager.vue'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import PageHero from '@/components/shared/PageHero.vue'
import EmptyState from '@/components/shared/EmptyState.vue'

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
  <section class="page-shell orders-page">
    <PageHero
      eyebrow="Order Archive"
      title="我的订单"
      accent="teal"
    >
      <template #actions>
        <Button variant="ghost" size="md" @click="router.push('/products')">继续购物</Button>
      </template>
    </PageHero>

    <p v-if="error" class="status-banner error">{{ error }}</p>

    <section class="panel-surface content-surface">
      <div class="surface-header">
        <div class="surface-title">
          <h2>订单列表</h2>
          <p>点击卡片进入详情，统一查看物流、售后和订单操作。</p>
        </div>
        <Badge variant="info">共 {{ total }} 笔订单</Badge>
      </div>

      <div v-if="loading" class="surface-state">加载中...</div>

      <EmptyState
        v-else-if="orders.length === 0"
        eyebrow="No Orders Yet"
        title="还没有订单记录"
        description="完成下单后，这里会继续沿用当前面板样式展示订单、物流和售后入口。"
      >
        <Button variant="outline" @click="router.push('/products')">去下单</Button>
      </EmptyState>

      <div v-else class="list-wrap">
        <div class="order-grid">
          <article v-for="order in orders" :key="order.id" class="order-card" @click="toOrderDetail(order.id)">
            <div class="row">
              <strong>{{ order.id }}</strong>
              <Badge variant="info">{{ orderStatusLabel(order.status) }}</Badge>
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
              <Button variant="outline" size="sm" @click.stop="toOrderDetail(order.id)">查看详情</Button>
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
.content-surface {
  padding: 20px;
  display: grid;
  gap: 18px;
}

.surface-state {
  min-height: 260px;
  display: grid;
  place-items: center;
  color: var(--text-muted);
}

.list-wrap {
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
  border: 1px solid rgba(31, 94, 87, 0.1);
  border-radius: 24px;
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

@media (max-width: 760px) {
  .row {
    flex-wrap: wrap;
  }

  .addr {
    white-space: normal;
  }
}
</style>
