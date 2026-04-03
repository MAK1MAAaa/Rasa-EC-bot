<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

interface Product {
  id: string
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

const fallbackCategories = ['手机', '音频', '电脑', '外设', '显示器', '穿戴']
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

const priceRange = ref({ min: 0, max: 0 })

const categoryOptions = computed(() => ['全部', ...availableCategories.value])
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const hasActiveFilters = computed(
  () =>
    !!appliedCategory.value ||
    appliedMinPrice.value !== null ||
    appliedMaxPrice.value !== null ||
    onlyInStock.value ||
    sortBy.value !== 'newest'
)
const filterSummary = computed(() => {
  const chips: string[] = []
  if (appliedCategory.value) {
    chips.push(`分类:${appliedCategory.value}`)
  }
  if (appliedMinPrice.value !== null || appliedMaxPrice.value !== null) {
    chips.push(`价格:¥${appliedMinPrice.value ?? 0}-¥${appliedMaxPrice.value ?? '不限'}`)
  }
  if (onlyInStock.value) {
    chips.push('仅看有库存')
  }
  if (sortBy.value === 'price_asc') {
    chips.push('价格升序')
  }
  if (sortBy.value === 'price_desc') {
    chips.push('价格降序')
  }
  return chips.join(' / ')
})

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
  page.value = 1
  error.value = ''
  loadProducts()
}

const addCart = async (productId: string) => {
  if (!authStore.isLoggedIn) {
    router.push('/login')
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

onMounted(async () => {
  await loadFilterMeta()
  selectedCategory.value = appliedCategory.value
  await loadProducts()
})
</script>

<template>
  <section class="page-wrap">
    <div class="hero">
      <h1>发现你的下一件心动好物</h1>
      <p>精选数码、办公与生活科技产品，支持一键加购与快速下单。</p>
      <button class="chat-link" type="button">去智能客服咨询</button>
    </div>

    <div class="toolbar">
      <div class="search-box">
        <input v-model="keywordInput" type="text" placeholder="搜索商品名称或描述" @keyup.enter="search">
        <button type="button" @click="search">搜索</button>
      </div>
      <button type="button" :class="showFilters ? 'filter-toggle active' : 'filter-toggle'" @click="showFilters = !showFilters">
        {{ showFilters ? '收起筛选' : '筛选商品' }}
      </button>
    </div>

    <transition name="expand">
      <div v-if="showFilters" class="filter-panel">
        <div class="filter-group">
          <p class="group-title">商品分类</p>
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
              :placeholder="`最低 ¥${priceRange.min.toFixed(2)}`"
            >
          </label>
          <label>
            <span>最高价</span>
            <input
              v-model="maxPriceInput"
              type="number"
              min="0"
              step="0.01"
              :placeholder="`最高 ¥${priceRange.max.toFixed(2)}`"
            >
          </label>
          <label>
            <span>排序</span>
            <select v-model="sortBy">
              <option value="newest">最新上架</option>
              <option value="price_asc">价格从低到高</option>
              <option value="price_desc">价格从高到低</option>
            </select>
          </label>
        </div>

        <label class="stock-check">
          <input v-model="onlyInStock" type="checkbox">
          <span>仅看有库存商品</span>
        </label>

        <div class="filter-actions">
          <button type="button" class="apply" @click="applyFilters">应用筛选</button>
          <button type="button" class="reset" @click="resetFilters">重置筛选</button>
        </div>
      </div>
    </transition>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-else class="result-text">
      共 {{ total }} 件商品
      <span v-if="hasActiveFilters"> · {{ filterSummary }}</span>
    </p>

    <div v-if="loading" class="state-card">正在加载商品...</div>
    <div v-else-if="products.length === 0" class="state-card">暂无符合条件的商品</div>

    <div v-else class="grid-list">
      <article v-for="product in products" :key="product.id" class="product-card">
        <img :src="product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'" :alt="product.name" class="thumb">
        <div class="content">
          <span class="category">{{ product.category || '未分类' }}</span>
          <h3>{{ product.name }}</h3>
          <p>{{ product.description || '这款商品暂时没有详细描述。' }}</p>
          <div class="bottom-row">
            <span class="price">¥ {{ product.price.toFixed(2) }}</span>
            <span class="stock">库存 {{ product.stock }}</span>
          </div>
          <div class="actions">
            <button type="button" class="ghost" @click="router.push(`/products/${product.id}`)">查看详情</button>
            <button type="button" :disabled="product.stock <= 0" @click="addCart(product.id)">
              {{ product.stock <= 0 ? '已售罄' : '加入购物车' }}
            </button>
          </div>
        </div>
      </article>
    </div>

    <div class="pager">
      <button type="button" :disabled="page <= 1" @click="jumpPage(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
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
  background: linear-gradient(120deg, #0b5aa6, #0f766e);
  color: #fff;
  border-radius: 20px;
  padding: 28px;
  box-shadow: 0 18px 34px rgba(11, 90, 166, 0.24);
}

.hero h1 {
  margin: 0;
  font-size: 30px;
}

.hero p {
  margin: 10px 0 0;
  color: rgba(255, 255, 255, 0.9);
  max-width: 560px;
}

.chat-link {
  margin-top: 16px;
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.toolbar {
  margin-top: 20px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

.search-box {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

.search-box input {
  border: 1px solid #c5d8ee;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 14px;
}

.search-box button {
  border: none;
  border-radius: 12px;
  background: #0b5aa6;
  color: #fff;
  padding: 0 16px;
}

.filter-toggle {
  border: 1px solid #b9d3ec;
  background: #f0f7ff;
  color: #20507f;
  border-radius: 12px;
  padding: 0 16px;
  font-weight: 600;
}

.filter-toggle.active {
  border-color: #0ea5e9;
  background: #dff2ff;
  color: #0b5aa6;
}

.filter-panel {
  margin-top: 12px;
  background: #fff;
  border: 1px solid #d6e4f2;
  border-radius: 16px;
  padding: 14px;
  display: grid;
  gap: 14px;
}

.filter-group {
  display: grid;
  gap: 8px;
}

.group-title {
  margin: 0;
  color: #214e7a;
  font-weight: 700;
}

.categories {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  border: 1px solid #bfd5ea;
  background: #f8fbff;
  color: #365879;
  border-radius: 999px;
  padding: 8px 12px;
}

.pill.active {
  border-color: #0ea5e9;
  color: #0b5aa6;
  background: #dff2ff;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.filter-grid label {
  display: grid;
  gap: 6px;
  color: #365879;
  font-size: 13px;
}

.filter-grid input,
.filter-grid select {
  border: 1px solid #c5d8ee;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 14px;
  background: #fff;
}

.stock-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #365879;
  font-size: 14px;
}

.filter-actions {
  display: flex;
  gap: 10px;
}

.filter-actions button {
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  cursor: pointer;
}

.filter-actions .apply {
  background: #0b5aa6;
  color: #fff;
}

.filter-actions .reset {
  background: #eaf2fb;
  color: #20507f;
}

.result-text,
.error {
  margin: 14px 0;
}

.error {
  color: #dc2626;
}

.state-card {
  background: #fff;
  border: 1px dashed #c8d7e8;
  border-radius: 16px;
  padding: 30px;
  text-align: center;
  color: #5f7690;
}

.grid-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.product-card {
  background: #fff;
  border: 1px solid #d8e5f1;
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
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
  color: #0f766e;
  font-size: 12px;
  font-weight: 600;
}

.content h3 {
  margin: 0;
  color: #17395f;
}

.content p {
  margin: 0;
  color: #5a718b;
  font-size: 14px;
  min-height: 42px;
}

.bottom-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.price {
  color: #0b5aa6;
  font-weight: 700;
}

.stock {
  color: #6d8099;
  font-size: 13px;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.actions button {
  border: none;
  border-radius: 10px;
  padding: 10px 0;
  cursor: pointer;
  background: #0b5aa6;
  color: #fff;
}

.actions button:disabled {
  background: #94a3b8;
}

.actions .ghost {
  background: #eaf2fb;
  color: #20507f;
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
  background: #0f2d53;
  color: #fff;
  border-radius: 10px;
  padding: 8px 12px;
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
  .toolbar {
    grid-template-columns: 1fr;
  }

  .filter-toggle {
    min-height: 44px;
  }

  .filter-grid {
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
