<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'

const router = useRouter()
const authStore = useAuthStore()
const cartStore = useCartStore()
const loading = ref(false)
let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

const loadCart = async () => {
  loading.value = true
  try {
    await cartStore.refreshCart()
  } finally {
    loading.value = false
  }
}

const increase = async (itemId: string, quantity: number) => {
  try {
    await cartStore.updateItem(itemId, quantity + 1)
  } catch (err: any) {
    alert(err.response?.data?.detail || '更新数量失败')
  }
}

const decrease = async (itemId: string, quantity: number) => {
  try {
    await cartStore.updateItem(itemId, Math.max(0, quantity - 1))
  } catch (err: any) {
    alert(err.response?.data?.detail || '更新数量失败')
  }
}

const remove = async (itemId: string) => {
  try {
    await cartStore.removeItem(itemId)
  } catch (err: any) {
    alert(err.response?.data?.detail || '移除商品失败')
  }
}

const scheduleRealtimeRefresh = () => {
  if (realtimeRefreshTimer) {
    return
  }
  realtimeRefreshTimer = setTimeout(async () => {
    realtimeRefreshTimer = null
    await loadCart()
  }, 300)
}

const handleRealtimeEvent = (event: RealtimeEvent) => {
  if (event.event === 'cart_changed' || event.event === 'order_changed') {
    scheduleRealtimeRefresh()
  }
}

onMounted(async () => {
  await loadCart()
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
  <section class="cart-page">
    <div class="header-row">
      <h1>购物车</h1>
      <button type="button" class="ghost" @click="router.push('/products')">继续购物</button>
    </div>

    <div v-if="loading" class="state-card">加载中...</div>

    <div v-else-if="cartStore.items.length === 0" class="state-card">
      购物车为空
    </div>

    <div v-else class="cart-layout">
      <div class="item-list">
        <article v-for="item in cartStore.items" :key="item.id" class="item-card">
          <img :src="item.product_image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=400&q=80'" :alt="item.product_name">
          <div class="item-main">
            <h3>{{ item.product_name }}</h3>
            <p>¥ {{ item.unit_price.toFixed(2) }}</p>
          </div>
          <div class="qty-box">
            <button @click="decrease(item.id, item.quantity)">-</button>
            <span>{{ item.quantity }}</span>
            <button @click="increase(item.id, item.quantity)">+</button>
          </div>
          <div class="right-col">
            <strong>¥ {{ item.subtotal.toFixed(2) }}</strong>
            <button class="text-btn" @click="remove(item.id)">移除</button>
          </div>
        </article>
      </div>

      <aside class="summary-card">
        <h2>结算</h2>
        <div class="sum-row"><span>件数</span><span>{{ cartStore.totalItems }}</span></div>
        <div class="sum-row total"><span>合计</span><span>¥ {{ cartStore.totalAmount.toFixed(2) }}</span></div>
        <button type="button" @click="router.push('/checkout')">去结算</button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.cart-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 18px 38px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.header-row h1 {
  margin: 0;
  color: #2d2517;
}

.ghost {
  border: 1px solid #d5c7ad;
  background: #f3e6cf;
  color: #4a3b20;
  border-radius: 999px;
  padding: 8px 14px;
}

.state-card {
  background: var(--surface-strong);
  border: 1px dashed #d8ccb6;
  border-radius: 16px;
  padding: 28px;
  text-align: center;
  color: #6b6254;
}

.cart-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
}

.item-list {
  display: grid;
  gap: 12px;
}

.item-card {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  display: grid;
  gap: 12px;
  grid-template-columns: 96px 1fr auto auto;
  align-items: center;
}

.item-card img {
  width: 96px;
  height: 80px;
  object-fit: cover;
  border-radius: 10px;
}

.item-main h3 {
  margin: 0;
  color: #2e2517;
}

.item-main p {
  margin: 6px 0 0;
  color: #746b5c;
}

.qty-box {
  display: inline-flex;
  align-items: center;
  border: 1px solid #d8cab2;
  border-radius: 999px;
  overflow: hidden;
}

.qty-box button {
  border: none;
  width: 32px;
  height: 32px;
  background: #f2e4cb;
  color: #513f24;
}

.qty-box span {
  min-width: 34px;
  text-align: center;
}

.right-col {
  display: grid;
  justify-items: end;
  gap: 6px;
}

.right-col strong {
  color: #3f2d12;
}

.text-btn {
  border: none;
  background: transparent;
  color: var(--danger);
  cursor: pointer;
}

.summary-card {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
  height: fit-content;
}

.summary-card h2 {
  margin: 0 0 14px;
  color: #2f2618;
  font-size: 18px;
}

.sum-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #5e5547;
}

.sum-row.total {
  font-size: 18px;
  font-weight: 700;
  color: #3d2b11;
  border-top: 1px dashed #d6c8ae;
  padding-top: 10px;
}

.summary-card button {
  width: 100%;
  margin-top: 12px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #2f2413, #765322);
  color: #fff6ea;
  padding: 11px;
  font-weight: 600;
}

@media (max-width: 900px) {
  .cart-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .item-card {
    grid-template-columns: 96px 1fr;
  }

  .qty-box,
  .right-col {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
