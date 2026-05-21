<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { createRealtimeClient, type RealtimeEvent } from '@/utils/realtime'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import PageHero from '@/components/shared/PageHero.vue'
import EmptyState from '@/components/shared/EmptyState.vue'

interface Product {
  id: string
  shop_id: string
  shop_name: string
  shop_rating?: number | null
  shop_shipping_city?: string | null
  name: string
  description?: string
  image_url?: string
  category?: string
  brand?: string
  model?: string
  price: number
  original_price?: number | null
  rating?: number | null
  review_count: number
  monthly_sales: number
  ship_in_hours: number
  tags: string[]
  stock: number
}

interface FilterShopOption {
  id: string
  name: string
  rating?: number | null
  shipping_city?: string | null
  active_product_count: number
}

interface ProductFilterMetaResponse {
  categories: string[]
  brands: string[]
  shops: FilterShopOption[]
  price_min: number
  price_max: number
}

type SortBy = 'newest' | 'price_asc' | 'price_desc' | 'rating_desc' | 'sales_desc'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const cartStore = useCartStore()

const loading = ref(false)
const error = ref('')
const products = ref<Product[]>([])
const page = ref(1)
const pageSize = 12
const total = ref(0)

const keywordInput = ref('')
const keyword = ref('')

const fallbackCategories = ['手机', '电脑', '音频', '外设', '显示器', '穿戴']
const availableCategories = ref<string[]>([...fallbackCategories])
const selectedCategory = ref('')
const appliedCategory = ref('')
const availableBrands = ref<string[]>([])
const selectedBrand = ref('')
const appliedBrand = ref('')
const shopOptions = ref<FilterShopOption[]>([])

const showFilters = ref(false)
const minPriceInput = ref('')
const maxPriceInput = ref('')
const appliedMinPrice = ref<number | null>(null)
const appliedMaxPrice = ref<number | null>(null)
const onlyInStock = ref(false)
const sortBy = ref<SortBy>('newest')

const appliedShopId = ref('')
const appliedShopName = ref('')

const priceRange = ref({ min: 0, max: 0 })
let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

const categoryOptions = computed(() => ['全部', ...availableCategories.value])
const brandOptions = computed(() => ['全部品牌', ...availableBrands.value])
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const hasActiveFilters = computed(
  () =>
    !!appliedCategory.value ||
    !!appliedBrand.value ||
    appliedMinPrice.value !== null ||
    appliedMaxPrice.value !== null ||
    onlyInStock.value ||
    sortBy.value !== 'newest' ||
    !!appliedShopId.value
)

const parsePrice = (value: string): number | null | 'invalid' => {
  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }
  const parsed = Number(trimmed)
  if (!Number.isFinite(parsed) || parsed < 0) {
    return 'invalid'
  }
  return Number(parsed.toFixed(2))
}

const loadFilterMeta = async () => {
  try {
    const response = await api.get<ProductFilterMetaResponse>('/products/filters')
    const categories = Array.isArray(response.data.categories)
      ? response.data.categories.filter((item) => typeof item === 'string' && item.trim().length > 0)
      : []
    availableCategories.value = categories.length > 0 ? categories : [...fallbackCategories]
    availableBrands.value = Array.isArray(response.data.brands)
      ? response.data.brands.filter((item) => typeof item === 'string' && item.trim().length > 0)
      : []
    shopOptions.value = Array.isArray(response.data.shops) ? response.data.shops : []

    const rangeMin = Number(response.data.price_min ?? 0)
    const rangeMax = Number(response.data.price_max ?? 0)
    if (Number.isFinite(rangeMin) && Number.isFinite(rangeMax) && rangeMax >= rangeMin) {
      priceRange.value = { min: rangeMin, max: rangeMax }
    }
    if (appliedShopId.value) {
      const matched = shopOptions.value.find((item) => item.id === appliedShopId.value)
      appliedShopName.value = matched?.name || appliedShopName.value
    }
  } catch {
    availableCategories.value = [...fallbackCategories]
    availableBrands.value = []
    shopOptions.value = []
  }
}

const loadProducts = async () => {
  loading.value = true
  error.value = ''

  try {
    const params: Record<string, string | number | boolean> = {
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value,
      category: appliedCategory.value,
      brand: appliedBrand.value,
      in_stock: onlyInStock.value,
      sort_by: sortBy.value
    }
    if (appliedMinPrice.value !== null) {
      params.min_price = appliedMinPrice.value
    }
    if (appliedMaxPrice.value !== null) {
      params.max_price = appliedMaxPrice.value
    }
    if (appliedShopId.value) {
      params.shop_id = appliedShopId.value
    }

    const response = await api.get('/products', { params })
    products.value = response.data.items
    total.value = response.data.total
  } catch (err: any) {
    error.value = err.response?.data?.detail || '商品加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const search = () => {
  keyword.value = keywordInput.value.trim()
  page.value = 1
  loadProducts()
}

const selectCategory = (value: string) => {
  selectedCategory.value = value === '全部' ? '' : value
}

const applyFilters = () => {
  const minPrice = parsePrice(minPriceInput.value)
  const maxPrice = parsePrice(maxPriceInput.value)

  if (minPrice === 'invalid' || maxPrice === 'invalid') {
    error.value = '价格请输入大于等于 0 的数字'
    return
  }
  if (minPrice !== null && maxPrice !== null && minPrice > maxPrice) {
    error.value = '最低价不能高于最高价'
    return
  }

  appliedCategory.value = selectedCategory.value
  appliedBrand.value = selectedBrand.value
  appliedMinPrice.value = minPrice
  appliedMaxPrice.value = maxPrice
  page.value = 1
  if (appliedShopId.value) {
    const matched = shopOptions.value.find((item) => item.id === appliedShopId.value)
    appliedShopName.value = matched?.name || appliedShopName.value
  }
  router.replace({ path: '/products', query: appliedShopId.value ? { shop_id: appliedShopId.value } : {} })
  loadProducts()
}

const resetFilters = () => {
  selectedCategory.value = ''
  appliedCategory.value = ''
  selectedBrand.value = ''
  appliedBrand.value = ''
  minPriceInput.value = ''
  maxPriceInput.value = ''
  appliedMinPrice.value = null
  appliedMaxPrice.value = null
  onlyInStock.value = false
  sortBy.value = 'newest'
  appliedShopId.value = ''
  appliedShopName.value = ''
  page.value = 1
  error.value = ''
  router.replace({ path: '/products' })
  loadProducts()
}

const filterByShop = (shopId: string, shopName: string) => {
  appliedShopId.value = shopId
  appliedShopName.value = shopName
  page.value = 1
  router.replace({ path: '/products', query: { shop_id: shopId } })
  loadProducts()
}

const openProductDetail = (productId: string) => {
  router.push(`/products/${productId}`)
}

const formatRating = (value?: number | null) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '暂无评分'
  return `${value.toFixed(1)} 分`
}

const formatShipHours = (value: number) => {
  if (!Number.isFinite(value) || value <= 0) return '时效待补充'
  if (value < 24) return `${value} 小时发货`
  if (value % 24 === 0) return `${value / 24} 天内发货`
  return `${value} 小时发货`
}

const formatCardSummary = (product: Product) => {
  const text = (product.description || '').replace(/\s+/g, ' ').trim()
  if (!text) {
    return product.model ? `型号 ${product.model}` : '点击查看完整规格与店铺信息'
  }
  return text.length > 34 ? `${text.slice(0, 34)}...` : text
}

const formatIdentityLine = (product: Product) => {
  const parts = [product.brand, product.model].filter(Boolean)
  return parts.length > 0 ? parts.join(' · ') : product.category || '精选商品'
}

const formatShopLine = (product: Product) => {
  const parts = [product.shop_name]
  if (product.shop_shipping_city) {
    parts.push(`${product.shop_shipping_city} 发货`)
  }
  return parts.join(' · ')
}

const addCart = async (productId: string) => {
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  if (!authStore.isCustomer) {
    error.value = '商家账号不能加入购物车，请切换用户账号'
    return
  }
  try {
    await cartStore.addToCart(productId, 1)
  } catch (err: any) {
    alert(err.response?.data?.detail || '加入购物车失败')
  }
}

const jumpPage = (value: number) => {
  if (value < 1 || value > totalPages.value || value === page.value) {
    return
  }
  page.value = value
  loadProducts()
}

const scheduleRealtimeRefresh = () => {
  if (realtimeRefreshTimer) {
    return
  }
  realtimeRefreshTimer = setTimeout(async () => {
    realtimeRefreshTimer = null
    await Promise.all([loadFilterMeta(), loadProducts()])
  }, 360)
}

const handleRealtimeEvent = (event: RealtimeEvent) => {
  if (event.event === 'inventory_changed' || event.event === 'order_changed') {
    scheduleRealtimeRefresh()
  }
}

watch(
  () => route.query.shop_id,
  (shopId) => {
    if (typeof shopId === 'string' && shopId.trim()) {
      appliedShopId.value = shopId
      const matched = shopOptions.value.find((item) => item.id === shopId)
      appliedShopName.value = matched?.name || appliedShopName.value
      page.value = 1
      loadProducts()
    } else {
      appliedShopId.value = ''
      appliedShopName.value = ''
    }
  }
)

onMounted(async () => {
  await loadFilterMeta()
  selectedCategory.value = appliedCategory.value
  selectedBrand.value = appliedBrand.value

  const queryShopId = typeof route.query.shop_id === 'string' ? route.query.shop_id : ''
  if (queryShopId) {
    appliedShopId.value = queryShopId
    const matched = shopOptions.value.find((item) => item.id === queryShopId)
    appliedShopName.value = matched?.name || ''
  }

  await loadProducts()
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
  <section class="page-shell products-page">
    <PageHero
      eyebrow="Curated Selection"
      title="精选商品"
      accent="gold"
    >
      <template #actions>
        <Button variant="ghost" size="md" @click="showFilters = !showFilters">{{ showFilters ? '收起筛选' : '打开筛选' }}</Button>
      </template>
    </PageHero>

    <section class="panel-surface surface-block">
      <div class="surface-head">
        <div class="surface-title">
          <h2>商品列表</h2>
          <p>支持搜索、分类、品牌、店铺、价格和库存筛选，并保留商品比较所需的主要指标。</p>
        </div>
        <div class="result-meta">
          <Badge variant="default">{{ total }} 件商品</Badge>
          <Badge v-if="hasActiveFilters" variant="info">已应用筛选</Badge>
          <Badge v-if="appliedShopName" variant="muted">{{ appliedShopName }}</Badge>
        </div>
      </div>

      <div class="search-row">
        <input v-model="keywordInput" class="field-input search-input" type="text" placeholder="搜商品、品牌或店铺" @keyup.enter="search">
        <Button size="lg" @click="search">搜索</Button>
      </div>

      <transition name="expand">
        <div v-if="showFilters" class="filter-panel">
          <div class="category-row">
            <button
              v-for="item in categoryOptions"
              :key="item"
              type="button"
              class="filter-pill"
              :class="{ active: selectedCategory === (item === '全部' ? '' : item) }"
              @click="selectCategory(item)"
            >
              {{ item }}
            </button>
          </div>

          <div class="filter-grid">
            <label class="filter-field">
              <span>品牌</span>
              <select v-model="selectedBrand" class="field-select">
                <option v-for="item in brandOptions" :key="item" :value="item === '全部品牌' ? '' : item">
                  {{ item }}
                </option>
              </select>
            </label>
            <label class="filter-field">
              <span>店铺</span>
              <select v-model="appliedShopId" class="field-select">
                <option value="">全部店铺</option>
                <option v-for="item in shopOptions" :key="item.id" :value="item.id">
                  {{ item.name }} · {{ item.active_product_count }} 件
                </option>
              </select>
            </label>
            <label class="filter-field">
              <span>最低价</span>
              <input
                v-model="minPriceInput"
                class="field-input"
                type="number"
                min="0"
                step="0.01"
                :placeholder="`¥${priceRange.min.toFixed(0)}`"
              >
            </label>
            <label class="filter-field">
              <span>最高价</span>
              <input
                v-model="maxPriceInput"
                class="field-input"
                type="number"
                min="0"
                step="0.01"
                :placeholder="`¥${priceRange.max.toFixed(0)}`"
              >
            </label>
            <label class="filter-field">
              <span>排序</span>
              <select v-model="sortBy" class="field-select">
                <option value="newest">最新</option>
                <option value="price_asc">价格低到高</option>
                <option value="price_desc">价格高到低</option>
                <option value="rating_desc">评分优先</option>
                <option value="sales_desc">销量优先</option>
              </select>
            </label>
          </div>

          <label class="stock-check">
            <input v-model="onlyInStock" type="checkbox">
            <span>仅看有货</span>
          </label>

          <div class="filter-actions">
            <Button size="sm" @click="applyFilters">应用筛选</Button>
            <Button variant="outline" size="sm" @click="resetFilters">重置</Button>
          </div>
        </div>
      </transition>

      <p v-if="error" class="status-banner error">{{ error }}</p>

      <div v-if="loading" class="catalog-state">加载中...</div>

      <EmptyState
        v-else-if="products.length === 0"
        eyebrow="Catalog Empty"
        title="当前筛选下没有商品"
        description="可以尝试切换分类、品牌或价格范围，或者回到默认筛选查看全部商品。"
      >
        <Button variant="outline" @click="resetFilters">重置筛选</Button>
      </EmptyState>

      <div v-else class="catalog-grid">
        <article v-for="product in products" :key="product.id" class="catalog-card">
          <div class="card-media" @click="openProductDetail(product.id)">
            <img :src="product.image_url || '/demo-assets/products/default.svg'" :alt="product.name">
            <div class="media-fade"></div>
          </div>

          <div class="card-body">
            <div class="card-headline">
              <Badge variant="muted">{{ product.category || '未分类' }}</Badge>
              <Badge v-if="product.brand" variant="default">{{ product.brand }}</Badge>
              <Badge v-if="product.stock <= 0" variant="danger">售罄</Badge>
            </div>

            <div class="copy-stack">
              <h3 @click="openProductDetail(product.id)">{{ product.name }}</h3>
              <p class="identity-line">{{ formatIdentityLine(product) }}</p>
              <p class="summary-line">{{ formatCardSummary(product) }}</p>
            </div>

            <button class="shop-link" type="button" @click="filterByShop(product.shop_id, product.shop_name)">
              {{ formatShopLine(product) }}
            </button>

            <div class="metrics compact">
              <span>{{ formatRating(product.rating) }}</span>
              <span>月销 {{ product.monthly_sales }}</span>
              <span>{{ formatShipHours(product.ship_in_hours) }}</span>
            </div>

            <div v-if="product.tags?.length" class="tags">
              <Badge v-for="tag in product.tags.slice(0, 3)" :key="tag" variant="warn">{{ tag }}</Badge>
            </div>

            <div class="price-row">
              <div class="price-stack">
                <strong>¥ {{ product.price.toFixed(2) }}</strong>
                <span v-if="product.original_price && product.original_price > product.price">¥ {{ product.original_price.toFixed(2) }}</span>
              </div>
              <Badge v-if="product.stock > 0" variant="success">库存 {{ product.stock }}</Badge>
            </div>

            <div class="actions">
              <Button variant="outline" block @click="openProductDetail(product.id)">查看详情</Button>
              <Button block :disabled="product.stock <= 0" @click="addCart(product.id)">
                {{ product.stock <= 0 ? '暂不可购' : '加入购物车' }}
              </Button>
            </div>
          </div>
        </article>
      </div>

      <div v-if="products.length > 0" class="pager">
        <Button variant="outline" size="sm" :disabled="page <= 1" @click="jumpPage(page - 1)">上一页</Button>
        <div class="pager-meta">
          <strong>{{ page }} / {{ totalPages }}</strong>
          <span>当前结果分页</span>
        </div>
        <Button variant="outline" size="sm" :disabled="page >= totalPages" @click="jumpPage(page + 1)">下一页</Button>
      </div>
    </section>
  </section>
</template>

<style scoped>
.products-page {
  display: grid;
  gap: 18px;
}

.surface-block {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.surface-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: start;
}

.surface-title {
  display: grid;
  gap: 6px;
}

.surface-title h2 {
  margin: 0;
  font-size: 36px;
}

.surface-title p {
  max-width: 640px;
  color: var(--text-muted);
  line-height: 1.75;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.search-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
}

.filter-panel {
  display: grid;
  gap: 16px;
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(106, 81, 47, 0.14);
  background: rgba(255, 252, 247, 0.86);
}

.category-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-pill {
  min-height: 40px;
  border-radius: 999px;
  border: 1px solid rgba(107, 83, 48, 0.14);
  padding: 0 14px;
  background: rgba(255, 250, 243, 0.94);
  color: #5f503f;
}

.filter-pill.active {
  background: var(--brand-soft);
  color: var(--brand-strong);
  border-color: rgba(178, 122, 50, 0.28);
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.filter-field {
  display: grid;
  gap: 8px;
}

.filter-field span,
.stock-check {
  color: #5f513f;
  font-size: 13px;
  font-weight: 700;
}

.stock-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.filter-actions {
  display: flex;
  gap: 10px;
}

.catalog-state {
  min-height: 280px;
  display: grid;
  place-items: center;
  border-radius: 24px;
  border: 1px dashed rgba(107, 83, 48, 0.18);
  color: var(--text-muted);
}

.catalog-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.catalog-card {
  overflow: hidden;
  border-radius: 24px;
  border: 1px solid rgba(106, 81, 47, 0.14);
  background: rgba(255, 252, 247, 0.94);
  box-shadow: 0 18px 36px rgba(46, 32, 12, 0.05);
  display: grid;
  height: 100%;
}

.catalog-card:hover {
  transform: translateY(-2px);
}

.card-media {
  position: relative;
  height: 220px;
  cursor: pointer;
}

.card-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-fade {
  position: absolute;
  inset: auto 0 0;
  height: 70px;
  background: linear-gradient(180deg, transparent, rgba(26, 19, 10, 0.2));
}

.card-body {
  padding: 16px;
  display: grid;
  gap: 12px;
  align-content: start;
  height: 100%;
}

.card-headline,
.tags,
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.copy-stack {
  display: grid;
  gap: 8px;
  min-height: 116px;
  align-content: start;
}

.copy-stack h3 {
  margin: 0;
  font-size: 26px;
  line-height: 1.05;
  cursor: pointer;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  min-height: calc(26px * 1.05 * 2);
}

.copy-stack p,
.metrics {
  color: var(--text-muted);
  line-height: 1.7;
  font-size: 13px;
}

.identity-line {
  font-weight: 700;
  color: #5d503f;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.summary-line {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  min-height: calc(13px * 1.7 * 2);
}

.shop-link {
  justify-self: start;
  border: none;
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(47, 95, 89, 0.08);
  color: var(--accent);
  font-weight: 700;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metrics {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.metrics.compact {
  padding-top: 2px;
  border-top: 1px solid rgba(106, 81, 47, 0.08);
  color: #807261;
  font-size: 12px;
}

.price-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: end;
  margin-top: auto;
}

.price-stack {
  display: grid;
  gap: 3px;
}

.price-stack strong {
  font-size: 28px;
  color: #322414;
}

.price-stack span {
  font-size: 12px;
  color: var(--text-soft);
  text-decoration: line-through;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.pager {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.pager-meta {
  min-width: 124px;
  display: grid;
  justify-items: center;
  gap: 2px;
  color: var(--text-muted);
  font-size: 12px;
}

.pager-meta strong {
  color: var(--text);
  font-size: 14px;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.22s ease;
  transform-origin: top;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: scaleY(0.95);
}

@media (max-width: 860px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .search-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .surface-head,
  .actions {
    display: grid;
  }

  .filter-actions {
    flex-direction: column;
  }

  .metrics,
  .price-row {
    flex-wrap: wrap;
  }

  .shop-link {
    width: 100%;
    justify-content: center;
  }
}
</style>
