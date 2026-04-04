<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

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
}

const route = useRoute()

const loading = ref(false)
const orders = ref<OrderListItem[]>([])
const selectedOrder = ref<OrderDetail | null>(null)
const selectedId = ref('')
const error = ref('')

const loadOrders = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/orders')
    orders.value = response.data.items
    const queryOrderId = typeof route.query.orderId === 'string' ? route.query.orderId : ''
    if (queryOrderId) {
      await viewOrder(queryOrderId)
    }
  } catch {
    error.value = '订单加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const viewOrder = async (orderId: string) => {
  selectedId.value = orderId
  try {
    const response = await api.get(`/orders/${orderId}`)
    selectedOrder.value = response.data
  } catch {
    selectedOrder.value = null
    alert('订单详情加载失败')
  }
}

onMounted(loadOrders)
</script>

<template>
  <section class="orders-page">
    <h1>我的订单</h1>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="loading" class="state-card">加载中...</div>
    <div v-else-if="orders.length === 0" class="state-card">暂无订单</div>

    <div v-else class="orders-layout">
      <div class="order-list">
        <article
          v-for="order in orders"
          :key="order.id"
          :class="selectedId === order.id ? 'order-card active' : 'order-card'"
          @click="viewOrder(order.id)"
        >
          <div class="row">
            <strong>{{ order.id }}</strong>
            <span class="status">{{ order.status }}</span>
          </div>
          <div class="row muted">
            <span>{{ new Date(order.created_at).toLocaleString() }}</span>
            <span>{{ order.item_count }} 件</span>
          </div>
          <div class="row muted">
            <span>{{ order.shop_name }}</span>
          </div>
          <div class="row">
            <span class="addr">{{ order.address }}</span>
            <strong class="price">¥ {{ order.total_amount.toFixed(2) }}</strong>
          </div>
        </article>
      </div>

      <aside class="detail-card" v-if="selectedOrder">
        <h2>订单详情</h2>
        <p><strong>订单号：</strong>{{ selectedOrder.id }}</p>
        <p><strong>店铺：</strong>{{ selectedOrder.shop_name }}</p>
        <p><strong>状态：</strong>{{ selectedOrder.status }}</p>
        <p><strong>地址：</strong>{{ selectedOrder.address }}</p>

        <h3>商品</h3>
        <ul>
          <li v-for="item in selectedOrder.items" :key="item.id">
            <a :href="`/products/${item.product_id}`" target="_blank">{{ item.product_name }}</a>
            <span>x {{ item.quantity }}</span>
            <strong>¥ {{ item.subtotal.toFixed(2) }}</strong>
          </li>
        </ul>

        <div v-if="selectedOrder.logistics" class="logistics">
          <h3>物流</h3>
          <p><strong>运单号：</strong>{{ selectedOrder.logistics.tracking_no || '-' }}</p>
          <p><strong>状态：</strong>{{ selectedOrder.logistics.status }}</p>
          <p><strong>当前位置：</strong>{{ selectedOrder.logistics.current_location || '-' }}</p>
          <p>
            <strong>预计送达：</strong>
            {{ selectedOrder.logistics.estimated_delivery_at ? new Date(selectedOrder.logistics.estimated_delivery_at).toLocaleString() : '-' }}
          </p>
          <p><strong>途径：</strong>{{ (selectedOrder.logistics.route_plan || []).join(' -> ') || '-' }}</p>
        </div>

        <div class="total">合计 ¥ {{ selectedOrder.total_amount.toFixed(2) }}</div>
      </aside>
      <aside class="detail-card" v-else>
        请选择订单
      </aside>
    </div>
  </section>
</template>

<style scoped>
.orders-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 18px 38px;
}

.orders-page h1 {
  margin: 0 0 14px;
  color: #312819;
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

.orders-layout {
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 16px;
}

.order-list {
  display: grid;
  gap: 10px;
}

.order-card {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  cursor: pointer;
  display: grid;
  gap: 8px;
}

.order-card.active {
  border-color: #b6863e;
  box-shadow: 0 0 0 3px rgba(182, 134, 62, 0.18);
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
}

.price {
  color: #3f2d12;
}

.detail-card {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
  height: fit-content;
  color: #4d4438;
}

.detail-card h2 {
  margin: 0 0 12px;
  color: #32291a;
}

.detail-card h3 {
  margin: 12px 0 8px;
}

.detail-card ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.detail-card li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
}

.detail-card a {
  color: #5a421d;
  text-decoration: none;
}

.logistics {
  margin-top: 10px;
  border-top: 1px dashed #d6c8ad;
  padding-top: 10px;
}

.total {
  margin-top: 10px;
  border-top: 1px dashed #d6c8ad;
  padding-top: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #3f2b10;
}

@media (max-width: 980px) {
  .orders-layout {
    grid-template-columns: 1fr;
  }
}
</style>
