<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import EmptyState from '@/components/shared/EmptyState.vue'

interface Product {
  id: string
  shop_id: string
  shop_name: string
  shop_description?: string | null
  shop_logo_url?: string | null
  shop_rating?: number | null
  shop_service_score?: number | null
  shop_logistics_score?: number | null
  shop_after_sales_score?: number | null
  shop_shipping_city?: string | null
  shop_featured_categories: string[]
  shop_service_tags: string[]
  name: string
  description?: string
  image_url?: string
  category?: string
  brand?: string
  model?: string
  sku_code?: string
  price: number
  original_price?: number | null
  rating?: number | null
  review_count: number
  monthly_sales: number
  ship_in_hours: number
  warranty_days: number
  tags: string[]
  spec_highlights: string[]
  stock: number
  created_at: string
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const cartStore = useCartStore()

const loading = ref(false)
const error = ref('')
const product = ref<Product | null>(null)
const quantity = ref(1)
const historyTrackedProductId = ref('')
let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

const canBuy = computed(() => Boolean(product.value && product.value.stock > 0 && authStore.isCustomer))
const fromSource = computed(() => (typeof route.query.from === 'string' ? route.query.from.trim() : ''))
const shopScores = computed(() => {
  if (!product.value) return []
  return [
    { label: '店铺评分', value: product.value.shop_rating },
    { label: '服务', value: product.value.shop_service_score },
    { label: '物流', value: product.value.shop_logistics_score },
    { label: '售后', value: product.value.shop_after_sales_score }
  ]
})

const formatRating = (value?: number | null) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '暂无评分'
  return `${value.toFixed(1)} 分`
}

const formatShipHours = (value: number) => {
  if (!Number.isFinite(value) || value <= 0) return '时效待补充'
  if (value < 24) return `${value} 小时内发货`
  if (value % 24 === 0) return `${value / 24} 天内发货`
  return `${value} 小时内发货`
}

const loadProduct = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get(`/products/${route.params.id}`)
    product.value = response.data
  } catch {
    error.value = '商品不存在或已下架'
  } finally {
    loading.value = false
  }
}

const recordProductViewHistory = async () => {
  if (!authStore.isCustomer || !authStore.user?.id || !product.value) {
    return
  }
  if (historyTrackedProductId.value === product.value.id) {
    return
  }

  try {
    await api.post(`/products/${product.value.id}/history`)
    historyTrackedProductId.value = product.value.id
  } catch {
    // 历史浏览记录失败不影响详情页主流程
  }
}

const addToCart = async () => {
  if (!product.value) return
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  if (!authStore.isCustomer) {
    error.value = '商家账号不能加入购物车'
    return
  }

  const safeQuantity = Math.min(Math.max(1, Number(quantity.value) || 1), product.value.stock)
  quantity.value = safeQuantity

  try {
    await cartStore.addToCart(product.value.id, safeQuantity)
    router.push('/cart')
  } catch (err: any) {
    alert(err.response?.data?.detail || '加入购物车失败')
  }
}

const jumpToShop = () => {
  if (!product.value) return
  router.push({ path: '/products', query: { shop_id: product.value.shop_id } })
}

const handleBack = () => {
  if (fromSource.value === 'chat') {
    router.push('/chat')
    return
  }
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/products')
}

const scheduleRealtimeRefresh = () => {
  if (realtimeRefreshTimer) {
    return
  }
  realtimeRefreshTimer = setTimeout(async () => {
    realtimeRefreshTimer = null
    await loadProduct()
  }, 320)
}

const handleRealtimeEvent = (event: RealtimeEvent) => {
  if (!product.value) {
    return
  }

  if (event.event !== 'inventory_changed' && event.event !== 'order_changed') {
    return
  }

  const rawIds = Array.isArray(event.data?.product_ids) ? event.data?.product_ids : []
  const touchedCurrent = rawIds.some((item) => String(item) === product.value?.id)
  if (rawIds.length === 0 || touchedCurrent) {
    scheduleRealtimeRefresh()
  }
}

onMounted(async () => {
  await loadProduct()
  realtimeClient = createRealtimeClient({
    token: authStore.token,
    onEvent: handleRealtimeEvent
  })
  await recordProductViewHistory()
})

onBeforeUnmount(() => {
  if (realtimeRefreshTimer) {
    clearTimeout(realtimeRefreshTimer)
    realtimeRefreshTimer = null
  }
  realtimeClient?.close()
  realtimeClient = null
})

watch(
  () => authStore.user?.id,
  async () => {
    await recordProductViewHistory()
  }
)

watch(
  () => route.params.id,
  async (nextId, previousId) => {
    if (nextId === previousId) return
    historyTrackedProductId.value = ''
    await loadProduct()
    await recordProductViewHistory()
  }
)
</script>

<template>
  <section class="page-shell detail-page">
    <div class="detail-top">
      <Button variant="outline" @click="handleBack()">返回上一页</Button>
      <Badge v-if="fromSource === 'chat'" variant="info">来自客服推荐</Badge>
    </div>

    <div v-if="loading" class="state-card">加载中...</div>
    <p v-else-if="error" class="status-banner error">{{ error }}</p>

    <EmptyState
      v-else-if="!product"
      eyebrow="Unavailable"
      title="商品不存在或已下架"
      description="可能已被商家下架，或者当前访问链接已失效。"
    >
      <Button variant="outline" @click="router.push('/products')">返回商品页</Button>
    </EmptyState>

    <article v-else class="detail-layout">
      <section class="detail-media panel-surface">
        <div class="media-frame">
          <img :src="product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1000&q=80'" :alt="product.name" class="cover">
        </div>
      </section>

      <section class="detail-summary panel-surface">
        <div class="summary-head">
          <div class="summary-tags">
            <Badge variant="muted">{{ product.category || '未分类' }}</Badge>
            <Badge v-if="product.brand" variant="default">{{ product.brand }}</Badge>
            <Badge v-if="product.model" variant="warn">{{ product.model }}</Badge>
            <Badge v-if="product.sku_code" variant="info">SKU {{ product.sku_code }}</Badge>
          </div>
          <h1>{{ product.name }}</h1>
          <p class="summary-copy">{{ product.description || '暂无商品描述，建议查看核心参数与店铺画像获取更多信息。' }}</p>
          <button class="shop-link" type="button" @click="jumpToShop">{{ product.shop_name }}</button>
        </div>

        <div v-if="product.tags?.length" class="tag-row">
          <Badge v-for="tag in product.tags" :key="tag" variant="warn">{{ tag }}</Badge>
        </div>

        <div class="price-panel">
          <div class="price-stack">
            <strong>¥ {{ product.price.toFixed(2) }}</strong>
            <span v-if="product.original_price && product.original_price > product.price">¥ {{ product.original_price.toFixed(2) }}</span>
          </div>
          <Badge :variant="product.stock > 0 ? 'success' : 'danger'">
            {{ product.stock > 0 ? `库存 ${product.stock}` : '已售罄' }}
          </Badge>
        </div>

        <div class="score-row">
          <div class="score-card">
            <span>评分</span>
            <strong>{{ formatRating(product.rating) }}</strong>
          </div>
          <div class="score-card">
            <span>评价</span>
            <strong>{{ product.review_count }}</strong>
          </div>
          <div class="score-card">
            <span>月销</span>
            <strong>{{ product.monthly_sales }}</strong>
          </div>
        </div>

        <div class="buy-box">
          <label>
            <span>购买数量</span>
            <input v-model.number="quantity" class="field-input qty" type="number" min="1" :max="product.stock">
          </label>
          <Button size="lg" block :disabled="!canBuy" @click="addToCart">
            {{ canBuy ? '加入购物车' : authStore.isMerchant ? '商家账号不可购买' : '当前无货' }}
          </Button>
        </div>
      </section>

      <section class="detail-block section-card">
        <div class="block-head">
          <h2>核心参数</h2>
          <p>把最重要的卖点放在前面，便于快速比较与客服推荐引用。</p>
        </div>
        <ul class="detail-list">
          <li v-for="item in product.spec_highlights" :key="item">{{ item }}</li>
        </ul>
      </section>

      <section class="detail-block section-card">
        <div class="block-head">
          <h2>服务保障</h2>
          <p>履约承诺、保修信息和发货时效统一放在购买决策附近。</p>
        </div>
        <div class="service-grid">
          <div class="service-item">
            <span>发货时效</span>
            <strong>{{ formatShipHours(product.ship_in_hours) }}</strong>
          </div>
          <div class="service-item">
            <span>保修</span>
            <strong>{{ product.warranty_days }} 天</strong>
          </div>
          <div class="service-item">
            <span>库存</span>
            <strong>{{ product.stock }}</strong>
          </div>
        </div>
      </section>

      <section class="detail-block section-card shop-block">
        <div class="block-head">
          <h2>店铺画像</h2>
          <p>帮助买家快速了解店铺实力、发货城市与服务能力。</p>
        </div>

        <div class="shop-profile">
          <img v-if="product.shop_logo_url" :src="product.shop_logo_url" :alt="product.shop_name" class="shop-logo">
          <div class="shop-copy">
            <strong>{{ product.shop_name }}</strong>
            <p>{{ product.shop_description || '店铺暂未补充简介。' }}</p>
            <p v-if="product.shop_shipping_city">{{ product.shop_shipping_city }} 发货</p>
          </div>
        </div>

        <div class="score-grid">
          <div v-for="item in shopScores" :key="item.label" class="service-item">
            <span>{{ item.label }}</span>
            <strong>{{ formatRating(item.value) }}</strong>
          </div>
        </div>

        <div v-if="product.shop_service_tags?.length" class="tag-row">
          <Badge v-for="tag in product.shop_service_tags" :key="tag" variant="info">{{ tag }}</Badge>
        </div>

        <p v-if="product.shop_featured_categories?.length" class="category-line">
          主营类目：{{ product.shop_featured_categories.join(' / ') }}
        </p>
      </section>
    </article>
  </section>
</template>

<style scoped>
.detail-page {
  display: grid;
  gap: 16px;
}

.detail-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.state-card {
  min-height: 320px;
  border-radius: 28px;
  border: 1px dashed rgba(106, 81, 47, 0.18);
  display: grid;
  place-items: center;
  color: var(--text-muted);
}

.detail-layout {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 18px;
  align-items: start;
}

.detail-media,
.detail-summary {
  min-height: 100%;
  padding: 20px;
}

.media-frame {
  border-radius: 28px;
  overflow: hidden;
  min-height: 560px;
}

.cover {
  width: 100%;
  height: 100%;
  min-height: 560px;
  object-fit: cover;
}

.detail-summary {
  display: grid;
  gap: 16px;
}

.summary-head {
  display: grid;
  gap: 10px;
}

.summary-tags,
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-head h1 {
  margin: 0;
  font-size: clamp(34px, 4.2vw, 56px);
  line-height: 0.96;
}

.summary-copy {
  color: var(--text-muted);
  line-height: 1.8;
}

.shop-link {
  width: fit-content;
  border: none;
  border-radius: 999px;
  background: rgba(47, 95, 89, 0.08);
  color: var(--accent);
  padding: 8px 14px;
  font-weight: 700;
}

.price-panel {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 14px;
  padding: 18px;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(255, 251, 243, 0.96), rgba(248, 238, 221, 0.92));
  border: 1px solid rgba(178, 122, 50, 0.14);
}

.price-stack {
  display: grid;
  gap: 4px;
}

.price-stack strong {
  font-size: clamp(38px, 4vw, 52px);
  color: #342313;
  line-height: 0.95;
}

.price-stack span {
  color: var(--text-soft);
  text-decoration: line-through;
  font-size: 13px;
}

.score-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.score-card,
.service-item {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 20px;
  border: 1px solid rgba(106, 81, 47, 0.14);
  background: rgba(255, 252, 247, 0.88);
}

.score-card span,
.service-item span {
  color: var(--text-muted);
  font-size: 12px;
}

.score-card strong,
.service-item strong {
  color: var(--text);
  font-size: 18px;
}

.buy-box {
  display: grid;
  gap: 12px;
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(106, 81, 47, 0.14);
  background: rgba(255, 252, 247, 0.88);
}

.buy-box label {
  display: grid;
  gap: 8px;
}

.buy-box span {
  color: #5a4d3f;
  font-size: 13px;
  font-weight: 700;
}

.qty {
  width: 130px;
}

.detail-block {
  padding: 20px;
  display: grid;
  gap: 14px;
}

.block-head {
  display: grid;
  gap: 6px;
}

.block-head h2 {
  margin: 0;
  font-size: 34px;
}

.block-head p,
.category-line,
.shop-copy p {
  color: var(--text-muted);
  line-height: 1.7;
}

.detail-list {
  margin: 0;
  padding-left: 18px;
  color: #5b4e3f;
  display: grid;
  gap: 10px;
  line-height: 1.7;
}

.service-grid,
.score-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.shop-block {
  grid-column: 1 / -1;
}

.shop-profile {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.shop-logo {
  width: 68px;
  height: 68px;
  border-radius: 20px;
  object-fit: cover;
}

.shop-copy {
  display: grid;
  gap: 6px;
}

.shop-copy strong {
  font-size: 22px;
  color: var(--text);
}

@media (max-width: 860px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .score-row,
  .service-grid,
  .score-grid {
    grid-template-columns: 1fr;
  }

  .media-frame,
  .cover {
    min-height: 320px;
  }
}
</style>


