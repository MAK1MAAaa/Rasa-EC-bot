<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'

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
  <section class="detail-page">
    <button class="back-btn" type="button" @click="handleBack()">← 返回</button>

    <div v-if="loading" class="state-card">加载中...</div>
    <div v-else-if="error" class="state-card error">{{ error }}</div>

    <article v-else-if="product" class="detail-card">
      <img :src="product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1000&q=80'" :alt="product.name" class="cover">

      <div class="info">
        <span class="category">{{ product.category || '未分类' }}</span>
        <h1>{{ product.name }}</h1>
        <div class="headline-meta">
          <span v-if="product.brand">{{ product.brand }}</span>
          <span v-if="product.model">{{ product.model }}</span>
          <span v-if="product.sku_code">SKU {{ product.sku_code }}</span>
        </div>
        <button class="shop-btn" type="button" @click="jumpToShop">{{ product.shop_name }}</button>
        <p v-if="product.description" class="summary">{{ product.description }}</p>
        <div v-if="product.tags?.length" class="tag-list">
          <span v-for="tag in product.tags" :key="tag" class="tag-chip">{{ tag }}</span>
        </div>

        <div class="price-row">
          <div class="price-stack">
            <span class="price">¥ {{ product.price.toFixed(2) }}</span>
            <span v-if="product.original_price && product.original_price > product.price" class="original-price">
              ¥ {{ product.original_price.toFixed(2) }}
            </span>
          </div>
          <span class="stock">库存 {{ product.stock }}</span>
        </div>

        <div class="score-row">
          <span>{{ formatRating(product.rating) }}</span>
          <span>{{ product.review_count }} 条评价</span>
          <span>月销 {{ product.monthly_sales }}</span>
        </div>

        <div class="buy-box">
          <label>数量</label>
          <input v-model.number="quantity" type="number" min="1" :max="product.stock" class="qty">
          <button type="button" :disabled="!canBuy" @click="addToCart">
            {{ canBuy ? '加入购物车' : authStore.isMerchant ? '商家账号不可购买' : '已售罄' }}
          </button>
        </div>

        <div class="detail-sections">
          <section class="detail-block">
            <h2>核心参数</h2>
            <ul class="detail-list">
              <li v-for="item in product.spec_highlights" :key="item">{{ item }}</li>
            </ul>
          </section>

          <section class="detail-block">
            <h2>服务保障</h2>
            <ul class="detail-list">
              <li>{{ formatShipHours(product.ship_in_hours) }}</li>
              <li>{{ product.warranty_days }} 天保修</li>
              <li>库存 {{ product.stock }}</li>
            </ul>
          </section>

          <section class="detail-block">
            <h2>店铺画像</h2>
            <div class="shop-profile">
              <img
                v-if="product.shop_logo_url"
                :src="product.shop_logo_url"
                :alt="product.shop_name"
                class="shop-logo"
              >
              <div class="shop-copy">
                <p>{{ product.shop_description || '店铺暂未补充简介。' }}</p>
                <p v-if="product.shop_shipping_city">{{ product.shop_shipping_city }} 发货</p>
              </div>
            </div>
            <div class="score-grid">
              <span v-for="item in shopScores" :key="item.label">{{ item.label }}：{{ formatRating(item.value) }}</span>
            </div>
            <div v-if="product.shop_service_tags?.length" class="tag-list">
              <span v-for="tag in product.shop_service_tags" :key="tag" class="tag-chip">{{ tag }}</span>
            </div>
            <div v-if="product.shop_featured_categories?.length" class="category-line">
              主营类目：{{ product.shop_featured_categories.join(' / ') }}
            </div>
          </section>
        </div>
      </div>
    </article>
  </section>
</template>

<style scoped>
.detail-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 18px 38px;
}

.back-btn {
  border: none;
  background: #efe0c3;
  color: #4b3a20;
  border-radius: 999px;
  padding: 8px 14px;
  margin-bottom: 14px;
}

.state-card {
  background: var(--surface-strong);
  border: 1px dashed #d8cbb5;
  border-radius: 16px;
  padding: 30px;
  text-align: center;
}

.state-card.error {
  color: var(--danger);
}

.detail-card {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 18px;
  overflow: hidden;
  display: grid;
  grid-template-columns: 1.1fr 1fr;
}

.cover {
  width: 100%;
  height: 100%;
  min-height: 360px;
  object-fit: cover;
}

.info {
  padding: 24px;
  display: grid;
  gap: 12px;
}

.headline-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #6f624c;
  font-size: 13px;
}

.category {
  color: #836e47;
  font-weight: 700;
  font-size: 13px;
}

.info h1 {
  margin: 0;
  color: #2c2316;
}

.shop-btn {
  width: fit-content;
  border: none;
  border-radius: 999px;
  background: #efe2c9;
  color: #4a3a20;
  padding: 6px 10px;
}

.summary {
  margin: 0;
  color: #5e564a;
  line-height: 1.6;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-chip {
  background: #f6ead0;
  color: #5d4724;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
}

.price-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.price-stack {
  display: grid;
  gap: 2px;
}

.price {
  font-size: 30px;
  color: #3f2b10;
  font-weight: 700;
}

.original-price {
  color: #9a8b74;
  text-decoration: line-through;
  font-size: 13px;
}

.stock {
  color: #756b5d;
}

.score-row {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: #625847;
  font-size: 13px;
}

.buy-box {
  margin-top: 8px;
  display: grid;
  gap: 10px;
}

.buy-box label {
  color: #534a3d;
  font-weight: 600;
}

.qty {
  width: 130px;
  border: 1px solid #d8ccb5;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fffcf5;
}

.buy-box button {
  width: 220px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #2f2413, #765322);
  color: #fff7ea;
  font-weight: 600;
  padding: 10px 12px;
}

.buy-box button:disabled {
  background: #b3aa9d;
}

.detail-sections {
  display: grid;
  gap: 14px;
}

.detail-block {
  border: 1px solid #e4d7c2;
  border-radius: 14px;
  padding: 14px;
  background: #fffbf4;
}

.detail-block h2 {
  margin: 0 0 10px;
  font-size: 16px;
  color: #352816;
}

.detail-list {
  margin: 0;
  padding-left: 18px;
  color: #5c5245;
  display: grid;
  gap: 6px;
}

.shop-profile {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.shop-logo {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  object-fit: cover;
}

.shop-copy p {
  margin: 0 0 6px;
  color: #5c5245;
  line-height: 1.5;
}

.score-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  color: #5a5245;
  font-size: 13px;
}

.category-line {
  color: #5c5245;
  font-size: 13px;
}

@media (max-width: 860px) {
  .detail-card {
    grid-template-columns: 1fr;
  }

  .cover {
    min-height: 220px;
  }

  .score-grid {
    grid-template-columns: 1fr;
  }
}
</style>


