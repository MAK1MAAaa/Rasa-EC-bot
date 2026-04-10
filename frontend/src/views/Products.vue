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
  name: string
  description?: string
  image_url?: string
  category?: string
  price: number
  stock: number
}

interface ProductFilterMetaResponse {
  categories: string[]
  price_min: number
  price_max: number
}

type SortBy = 'newest' | 'price_asc' | 'price_desc'

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
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const hasActiveFilters = computed(
  () =>
    !!appliedCategory.value ||
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

    const rangeMin = Number(response.data.price_min ?? 0)
    const rangeMax = Number(response.data.price_max ?? 0)
    if (Number.isFinite(rangeMin) && Number.isFinite(rangeMax) && rangeMax >= rangeMin) {
      priceRange.value = { min: rangeMin, max: rangeMax }
    }
  } catch {
    availableCategories.value = [...fallbackCategories]
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
  appliedMinPrice.value = minPrice
  appliedMaxPrice.value = maxPrice
  page.value = 1
  loadProducts()
}

const resetFilters = () => {
  selectedCategory.value = ''
  appliedCategory.value = ''
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
      page.value = 1
      loadProducts()
    }
  }
)

onMounted(async () => {
  await loadFilterMeta()
  selectedCategory.value = appliedCategory.value

  const queryShopId = typeof route.query.shop_id === 'string' ? route.query.shop_id : ''
  if (queryShopId) {
    appliedShopId.value = queryShopId
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
  <section class="page-wrap">
    <div class="hero">
      <h1>本周热卖</h1>
      <div class="hero-actions">
        <button v-if="!authStore.isMerchant" class="chat-link" type="button" @click="router.push('/chat')">问客服</button>
        <button class="ghost-link" type="button" @click="showFilters = !showFilters">{{ showFilters ? '收起筛选' : '筛选' }}</button>
      </div>
    </div>

    <div class="toolbar">
      <div class="search-box">
        <input v-model="keywordInput" type="text" placeholder="搜商品 / 品牌" @keyup.enter="search">
        <button type="button" @click="search">搜索</button>
      </div>
    </div>

    <transition name="expand">
      <div v-if="showFilters" class="filter-panel">
        <div class="filter-group">
          <div class="categories">
            <button
              v-for="item in categoryOptions"
              :key="item"
              type="button"
              :class="selectedCategory === (item === '全部' ? '' : item) ? 'pill active' : 'pill'"
              @click="selectCategory(item)"
            >
              {{ item }}
            </button>
          </div>
        </div>

        <div class="filter-grid">
          <label>
            <span>最低价</span>
            <input
              v-model="minPriceInput"
              type="number"
              min="0"
              step="0.01"
              :placeholder="`¥${priceRange.min.toFixed(0)}`"
            >
          </label>
          <label>
            <span>最高价</span>
            <input
              v-model="maxPriceInput"
              type="number"
              min="0"
              step="0.01"
              :placeholder="`¥${priceRange.max.toFixed(0)}`"
            >
          </label>
          <label>
            <span>排序</span>
            <select v-model="sortBy">
              <option value="newest">最新</option>
              <option value="price_asc">价格低到高</option>
              <option value="price_desc">价格高到低</option>
            </select>
          </label>
        </div>

        <label class="stock-check">
          <input v-model="onlyInStock" type="checkbox">
          <span>仅看有货</span>
        </label>

        <div class="filter-actions">
          <button type="button" class="apply" @click="applyFilters">应用</button>
          <button type="button" class="reset" @click="resetFilters">重置</button>
        </div>
      </div>
    </transition>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-else class="result-text">
      {{ total }} 件商品
      <span v-if="hasActiveFilters"> · 已筛选</span>
      <span v-if="appliedShopName"> · {{ appliedShopName }}</span>
    </p>

    <div v-if="loading" class="state-card">加载中...</div>
    <div v-else-if="products.length === 0" class="state-card">暂无商品</div>

    <div v-else class="grid-list">
      <article v-for="product in products" :key="product.id" class="product-card">
        <img :src="product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'" :alt="product.name" class="thumb">
        <div class="content">
          <span class="category">{{ product.category || '未分类' }}</span>
          <h3>{{ product.name }}</h3>
          <button class="shop-link" type="button" @click="filterByShop(product.shop_id, product.shop_name)">
            {{ product.shop_name }}
          </button>
          <div class="bottom-row">
            <span class="price">¥ {{ product.price.toFixed(2) }}</span>
            <span class="stock">库存 {{ product.stock }}</span>
          </div>
          <div class="actions">
            <button type="button" class="ghost" @click="router.push(`/products/${product.id}`)">详情</button>
            <button type="button" :disabled="product.stock <= 0" @click="addCart(product.id)">
              {{ product.stock <= 0 ? '售罄' : '加购' }}
            </button>
          </div>
        </div>
      </article>
    </div>

    <div class="pager">
      <button type="button" :disabled="page <= 1" @click="jumpPage(page - 1)">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button type="button" :disabled="page >= totalPages" @click="jumpPage(page + 1)">下一页</button>
    </div>
  </section>
</template>

<style scoped>
.page-wrap {
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 18px 40px;
}

.hero {
  background:
    linear-gradient(135deg, rgba(50, 39, 24, 0.95), rgba(114, 82, 38, 0.93)),
    radial-gradient(circle at 80% 0%, rgba(255, 255, 255, 0.14), transparent 42%);
  color: #fff6ea;
  border-radius: 22px;
  padding: 24px;
  box-shadow: 0 20px 40px rgba(66, 46, 18, 0.2);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.hero h1 {
  margin: 0;
  font-size: 30px;
}

.hero-actions {
  display: inline-flex;
  gap: 8px;
}

.chat-link,
.ghost-link {
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
  font-weight: 600;
}

.chat-link {
  background: #f6e2be;
  color: #3f2b10;
}

.ghost-link {
  background: rgba(255, 255, 255, 0.16);
  color: #fffaf2;
  border: 1px solid rgba(255, 255, 255, 0.35);
}

.toolbar {
  margin-top: 18px;
}

.search-box {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

.search-box input {
  border: 1px solid #d8ccb5;
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 14px;
  background: #fffdf7;
}

.search-box button {
  border: none;
  border-radius: 999px;
  background: #2e2313;
  color: #fff6e8;
  padding: 0 18px;
}

.filter-panel {
  margin-top: 12px;
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px;
  display: grid;
  gap: 14px;
}

.categories {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  border: 1px solid #d8cab2;
  background: #fff8eb;
  color: #5d523f;
  border-radius: 999px;
  padding: 8px 12px;
}

.pill.active {
  border-color: #b6863e;
  color: #3d2c14;
  background: #f4dfbd;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.filter-grid label {
  display: grid;
  gap: 6px;
  color: #5a5143;
  font-size: 13px;
}

.filter-grid input,
.filter-grid select {
  border: 1px solid #d8ccb5;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 14px;
  background: #fffdf7;
}

.stock-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #5a5143;
  font-size: 14px;
}

.filter-actions {
  display: flex;
  gap: 10px;
}

.filter-actions button {
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
}

.filter-actions .apply {
  background: #2f2413;
  color: #fff4e6;
}

.filter-actions .reset {
  background: #efdfc2;
  color: #4a3a1e;
}

.result-text,
.error {
  margin: 14px 0;
}

.result-text {
  color: #655c4f;
}

.error {
  color: var(--danger);
}

.state-card {
  background: var(--surface-strong);
  border: 1px dashed #d9cdb7;
  border-radius: 16px;
  padding: 30px;
  text-align: center;
  color: #756a58;
}

.grid-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.product-card {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.product-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-soft);
}

.thumb {
  width: 100%;
  height: 180px;
  object-fit: cover;
}

.content {
  display: grid;
  gap: 8px;
  padding: 14px;
}

.category {
  color: #826d46;
  font-size: 12px;
  font-weight: 600;
}

.content h3 {
  margin: 0;
  color: #2b2317;
  font-size: 18px;
}

.shop-link {
  border: none;
  background: #efe2c9;
  color: #544427;
  border-radius: 8px;
  width: fit-content;
  padding: 4px 8px;
  font-size: 12px;
}

.bottom-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.price {
  color: #3f2b10;
  font-weight: 700;
}

.stock {
  color: #7c7466;
  font-size: 13px;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.actions button {
  border: none;
  border-radius: 999px;
  padding: 9px 0;
  cursor: pointer;
  background: #2f2413;
  color: #fff5e8;
}

.actions button:disabled {
  background: #b8b0a4;
}

.actions .ghost {
  background: #efe2c9;
  color: #4f3f26;
}

.pager {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14px;
}

.pager button {
  border: none;
  background: #2f2413;
  color: #fff5e8;
  border-radius: 999px;
  padding: 8px 14px;
}

.pager button:disabled {
  opacity: 0.5;
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

  .search-box {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .hero h1 {
    font-size: 24px;
  }

  .actions {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    flex-direction: column;
  }
}
</style>
