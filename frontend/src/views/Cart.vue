<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ListPager from '@/components/ListPager.vue'
import { useCartStore } from '@/stores/cart'
import { useAuthStore } from '@/stores/auth'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import PageHero from '@/components/shared/PageHero.vue'
import EmptyState from '@/components/shared/EmptyState.vue'

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

const openProductDetail = (productId: string) => {
  if (!productId) {
    return
  }
  router.push(`/products/${productId}`)
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
  <section class="page-shell cart-page">
    <PageHero
      eyebrow="Cart Overview"
      title="购物车"
      accent="gold"
    >
      <template #actions>
        <Button variant="ghost" size="md" @click="router.push('/products')">继续购物</Button>
      </template>
    </PageHero>

    <div class="page-grid-two">
      <section class="panel-surface cart-surface">
        <div class="surface-header">
          <div class="surface-title">
            <h2>待结算商品</h2>
            <p>按页查看购物车条目，数量修改会实时同步，并尽量保留当前浏览上下文。</p>
          </div>
          <Badge variant="default">{{ cartStore.items.length }} 个商品条目</Badge>
        </div>

        <div v-if="loading" class="state-card">加载中...</div>

        <EmptyState
          v-else-if="cartStore.items.length === 0"
          eyebrow="Nothing Here Yet"
          title="购物车还是空的"
          description="浏览商品并加入购物车后，这里会按当前卡片结构展示，结算区也会同步更新。"
        >
          <Button variant="outline" @click="router.push('/products')">去逛商品</Button>
        </EmptyState>

        <div v-else class="item-list-wrap">
          <article v-for="item in pagedItems" :key="item.id" class="item-card">
            <button type="button" class="item-cover" @click="openProductDetail(item.product_id)">
              <img
                :src="item.product_image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=400&q=80'"
                :alt="item.product_name"
              >
            </button>
            <div class="item-main">
              <button type="button" class="item-title" @click="openProductDetail(item.product_id)">
                <h3>{{ item.product_name }}</h3>
              </button>
              <p>单价 ¥ {{ item.unit_price.toFixed(2) }}</p>
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

          <ListPager
            :page="page"
            :total-pages="totalPages"
            :total-items="cartStore.items.length"
            @change="handlePageChange"
          />
        </div>
      </section>

      <aside class="panel-surface summary-card">
        <div class="summary-head">
          <p class="summary-eyebrow">Checkout Snapshot</p>
          <h2>结算概览</h2>
        </div>
        <div class="sum-row">
          <span>商品件数</span>
          <strong>{{ cartStore.totalItems }}</strong>
        </div>
        <div class="sum-row">
          <span>商品条目</span>
          <strong>{{ cartStore.items.length }}</strong>
        </div>
        <div class="sum-row total">
          <span>合计</span>
          <strong>¥ {{ cartStore.totalAmount.toFixed(2) }}</strong>
        </div>
        <Button size="lg" block :disabled="cartStore.items.length === 0" @click="router.push('/checkout')">去结算</Button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.cart-page {
  display: grid;
  gap: 18px;
}

.cart-surface,
.summary-card {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.item-list-wrap {
  display: grid;
  gap: 14px;
}

.item-list {
  display: grid;
  gap: 12px;
}

.item-card {
  border: 1px solid rgba(149, 114, 62, 0.12);
  border-radius: 24px;
  padding: 14px;
  background: rgba(255, 253, 248, 0.9);
  display: grid;
  gap: 14px;
  grid-template-columns: 108px minmax(0, 1fr) auto auto;
  align-items: center;
}

.item-cover {
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
}

.item-card img {
  width: 108px;
  height: 88px;
  object-fit: cover;
  border-radius: 14px;
}

.item-main {
  min-width: 0;
}

.item-title {
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: inherit;
  width: 100%;
}

.item-main h3 {
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  min-height: calc(24px * 1.25 * 2);
}

.item-main p {
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  align-content: start;
}

.summary-eyebrow {
  color: var(--text-soft);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.summary-head {
  display: grid;
  gap: 6px;
}

.summary-card h2 {
  margin: 0;
  font-size: 36px;
}

.sum-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  color: var(--text-muted);
}

.sum-row.total {
  padding-top: 12px;
  border-top: 1px dashed rgba(106, 81, 47, 0.2);
  color: var(--text);
}

@media (max-width: 760px) {
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
