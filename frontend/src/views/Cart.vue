<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ListPager from '@/components/ListPager.vue'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'

const router = useRouter()
const authStore = useAuthStore()
const cartStore = useCartStore()

const loading = ref(false)
const page = ref(1)
const pageSize = 6

let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

const totalPages = computed(() => Math.max(1, Math.ceil(cartStore.items.length / pageSize)))
const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize
  return cartStore.items.slice(start, start + pageSize)
})

watch(
  () => cartStore.items.length,
  (length) => {
    if (length === 0) {
      page.value = 1
      return
    }
    if (page.value > totalPages.value) {
      page.value = totalPages.value
    }
  },
  { immediate: true }
)

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

const handlePageChange = (nextPage: number) => {
  page.value = nextPage
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
    <header class="hero">
      <div>
        <p class="hero-eyebrow">Cart Overview</p>
        <h1>购物车</h1>
        <p class="hero-copy">商品为空时也保持同一块内容面板，回到有商品的状态不会突然跳变。</p>
      </div>
      <button type="button" class="ghost" @click="router.push('/products')">继续购物</button>
    </header>

    <div class="cart-layout">
      <section class="content-surface">
        <div class="surface-head">
          <div>
            <h2>待结算商品</h2>
            <p>按页查看购物车条目，调整数量后保持当前浏览位置。</p>
          </div>
          <span class="surface-badge">{{ cartStore.items.length }} 个商品条目</span>
        </div>

        <div v-if="loading" class="surface-state">加载中...</div>

        <div v-else-if="cartStore.items.length === 0" class="empty-state">
          <p class="empty-eyebrow">Nothing Here Yet</p>
          <h3>购物车还是空的</h3>
          <p>浏览商品并加入购物车后，这里会按同样的卡片结构展示，结算区也会同步更新。</p>
          <button type="button" class="empty-action" @click="router.push('/products')">去逛商品</button>
        </div>

        <div v-else class="item-list-wrap">
          <div class="item-list">
            <article v-for="item in pagedItems" :key="item.id" class="item-card">
              <img
                :src="item.product_image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=400&q=80'"
                :alt="item.product_name"
              >
              <div class="item-main">
                <h3>{{ item.product_name }}</h3>
                <p class="unit-price">¥ {{ item.unit_price.toFixed(2) }}</p>
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

          <ListPager
            :page="page"
            :total-pages="totalPages"
            :total-items="cartStore.items.length"
            @change="handlePageChange"
          />
        </div>
      </section>

      <aside class="summary-card">
        <p class="summary-eyebrow">Checkout Snapshot</p>
        <h2>结算概览</h2>
        <div class="sum-row">
          <span>商品件数</span>
          <span>{{ cartStore.totalItems }}</span>
        </div>
        <div class="sum-row">
          <span>商品条目</span>
          <span>{{ cartStore.items.length }}</span>
        </div>
        <div class="sum-row total">
          <span>合计</span>
          <span>¥ {{ cartStore.totalAmount.toFixed(2) }}</span>
        </div>
        <button
          type="button"
          class="checkout-btn"
          :disabled="cartStore.items.length === 0"
          @click="router.push('/checkout')"
        >
          去结算
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.cart-page {
  --page-accent: #7b5520;
  --page-accent-soft: rgba(123, 85, 32, 0.14);
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 18px 40px;
}

.hero {
  margin-bottom: 18px;
  padding: 22px 24px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(255, 245, 226, 0.92), transparent 34%),
    linear-gradient(135deg, #2c2010 0%, #6f4c1f 58%, #ad7b3b 100%);
  color: #fff7eb;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-end;
}

.hero-eyebrow,
.summary-eyebrow,
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
  color: rgba(255, 246, 231, 0.82);
  line-height: 1.7;
}

.ghost {
  border: 1px solid rgba(255, 243, 224, 0.42);
  background: rgba(255, 249, 238, 0.14);
  color: #fff8ef;
  border-radius: 999px;
  padding: 10px 16px;
  backdrop-filter: blur(10px);
}

.cart-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: start;
}

.content-surface,
.summary-card {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 254, 250, 0.96), rgba(251, 245, 233, 0.92)),
    var(--surface-strong);
  border: 1px solid rgba(129, 94, 43, 0.14);
  border-radius: 24px;
  box-shadow: 0 18px 40px rgba(73, 52, 22, 0.08);
}

.content-surface::before,
.summary-card::before {
  content: '';
  position: absolute;
  inset: 0 auto auto 0;
  width: 180px;
  height: 180px;
  background: radial-gradient(circle, rgba(255, 223, 168, 0.32), transparent 70%);
  pointer-events: none;
}

.content-surface {
  padding: 20px;
  min-height: 560px;
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
.summary-card h2,
.empty-state h3 {
  margin: 0;
  color: #2f2313;
}

.surface-head p,
.empty-state p {
  margin: 8px 0 0;
  color: #6d6254;
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
.item-list-wrap {
  min-height: 100%;
  border-radius: 20px;
  border: 1px solid rgba(146, 111, 58, 0.12);
  background: linear-gradient(180deg, rgba(255, 253, 248, 0.92), rgba(255, 248, 236, 0.88));
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
.checkout-btn {
  border: none;
  border-radius: 999px;
  padding: 12px 18px;
  background: #2f2413;
  color: #fff7ea;
  cursor: pointer;
}

.item-list-wrap {
  padding: 16px;
  display: grid;
  gap: 12px;
  align-content: start;
}

.item-list {
  display: grid;
  gap: 12px;
}

.item-card {
  border: 1px solid rgba(149, 114, 62, 0.14);
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 253, 248, 0.96);
  display: grid;
  gap: 14px;
  grid-template-columns: 108px minmax(0, 1fr) auto auto;
  align-items: center;
}

.item-card img {
  width: 108px;
  height: 88px;
  object-fit: cover;
  border-radius: 14px;
}

.item-main h3 {
  margin: 0;
  color: #2e2517;
}

.unit-price {
  margin: 8px 0 0;
  color: #746b5c;
}

.qty-box {
  display: inline-flex;
  align-items: center;
  border: 1px solid #d8cab2;
  border-radius: 999px;
  overflow: hidden;
  background: #fff6e6;
}

.qty-box button {
  border: none;
  width: 34px;
  height: 34px;
  background: #f2e4cb;
  color: #513f24;
  cursor: pointer;
}

.qty-box span {
  min-width: 36px;
  text-align: center;
}

.right-col {
  display: grid;
  justify-items: end;
  gap: 8px;
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
  padding: 20px;
  min-height: 320px;
  display: grid;
  align-content: start;
  gap: 14px;
}

.summary-eyebrow {
  color: #896431;
}

.sum-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #5e5547;
}

.sum-row.total {
  padding-top: 14px;
  border-top: 1px dashed #d9c9ae;
  font-size: 20px;
  color: #342714;
}

.checkout-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 980px) {
  .cart-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero,
  .surface-head {
    display: grid;
    align-items: start;
  }

  .content-surface {
    min-height: 480px;
  }

  .item-card {
    grid-template-columns: 88px 1fr;
  }

  .qty-box,
  .right-col {
    grid-column: 2;
    justify-self: start;
  }

  .right-col {
    justify-items: start;
  }
}
</style>
