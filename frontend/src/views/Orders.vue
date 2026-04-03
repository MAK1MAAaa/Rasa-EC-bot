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
}

interface OrderDetailItem {
  id: string
  product_id: string
  product_name: string
  unit_price: number
  quantity: number
  subtotal: number
}

interface OrderDetail {
  id: string
  status: string
  address: string
  contact_email: string
  total_amount: number
  created_at: string
  items: OrderDetailItem[]
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

    <div v-if="loading" class="state-card">正在加载订单...</div>
    <div v-else-if="orders.length === 0" class="state-card">还没有订单，先去下单吧。</div>

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
            <span>{{ order.item_count }} 件商品</span>
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
        <p><strong>状态：</strong>{{ selectedOrder.status }}</p>
        <p><strong>地址：</strong>{{ selectedOrder.address }}</p>
        <p><strong>联系邮箱：</strong>{{ selectedOrder.contact_email }}</p>

        <h3>商品明细</h3>
        <ul>
          <li v-for="item in selectedOrder.items" :key="item.id">
            <span>{{ item.product_name }} × {{ item.quantity }}</span>
            <strong>¥ {{ item.subtotal.toFixed(2) }}</strong>
          </li>
        </ul>

        <div class="total">订单总额 ¥ {{ selectedOrder.total_amount.toFixed(2) }}</div>
      </aside>
      <aside class="detail-card" v-else>
        请选择左侧订单查看详情。
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
  color: #16395f;
}

.error {
  color: #dc2626;
}

.state-card {
  background: #fff;
  border: 1px dashed #bfd2e6;
  border-radius: 16px;
  padding: 30px;
  text-align: center;
  color: #5c738c;
}

.orders-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 16px;
}

.order-list {
  display: grid;
  gap: 10px;
}

.order-card {
  background: #fff;
  border: 1px solid #d8e5f1;
  border-radius: 14px;
  padding: 14px;
  cursor: pointer;
  display: grid;
  gap: 8px;
}

.order-card.active {
  border-color: #0ea5e9;
  box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.14);
}

.row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.row.muted {
  color: #5f7691;
  font-size: 13px;
}

.status {
  background: #dff2ff;
  color: #0b5aa6;
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.addr {
  color: #4f6680;
}

.price {
  color: #0b5aa6;
}

.detail-card {
  background: #fff;
  border: 1px solid #d8e5f1;
  border-radius: 14px;
  padding: 16px;
  height: fit-content;
  color: #36526f;
}

.detail-card h2 {
  margin: 0 0 12px;
  color: #17395f;
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
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.total {
  margin-top: 10px;
  border-top: 1px dashed #c6d8eb;
  padding-top: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #0b5aa6;
}

@media (max-width: 980px) {
  .orders-layout {
    grid-template-columns: 1fr;
  }
}
</style>
