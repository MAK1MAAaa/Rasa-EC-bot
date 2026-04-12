<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'

interface ProductViewHistoryItem {
  id: string
  shop_id: string
  shop_name: string
  name: string
  description?: string
  image_url?: string
  category?: string
  brand?: string
  price: number
  original_price?: number | null
  rating?: number | null
  review_count: number
  monthly_sales: number
  ship_in_hours: number
  tags: string[]
  stock: number
  view_count: number
  last_viewed_at: string
}

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const error = ref('')
const items = ref<ProductViewHistoryItem[]>([])

const hasItems = computed(() => items.value.length > 0)

const loadHistory = async () => {
  if (!authStore.isCustomer || !authStore.user?.id) {
    items.value = []
    return
  }

  loading.value = true
  error.value = ''
  try {
    const response = await api.get<{ items: ProductViewHistoryItem[] }>('/products/history', {
      params: { limit: 8 }
    })
    items.value = Array.isArray(response.data.items) ? response.data.items : []
  } catch (err: any) {
    items.value = []
    error.value = err.response?.data?.detail || '历史浏览加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const openProductDetail = (productId: string) => {
  router.push(`/products/${productId}`)
}

const formatLastViewedAt = (value: string) => {
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return value || '-'
  return dt.toLocaleString()
}

onMounted(async () => {
  await loadHistory()
})

watch(
  () => authStore.user?.id,
  async () => {
    await loadHistory()
  }
)
</script>

<template>
  <section class="history-page">
    <div class="hero">
      <div>
        <p class="eyebrow">History</p>
        <h1>历史浏览</h1>
        <p class="sub">这里会展示你最近看过的商品，客服推荐也会参考这部分浏览偏好。</p>
      </div>
      <button type="button" class="browse-btn" @click="router.push('/products')">继续逛商品</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <div v-if="loading" class="state-card">加载中...</div>

    <section v-else-if="hasItems" class="history-grid">
      <article
        v-for="item in items"
        :key="item.id"
        class="history-card"
        @click="openProductDetail(item.id)"
      >
        <img
          :src="item.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'"
          :alt="item.name"
          class="thumb"
        >
        <div class="content">
          <div class="head">
            <span class="category">{{ item.category || '未分类' }}</span>
            <span v-if="item.brand" class="brand">{{ item.brand }}</span>
          </div>
          <h2>{{ item.name }}</h2>
          <p class="shop">{{ item.shop_name }}</p>
          <div class="meta">
            <span>浏览 {{ item.view_count }} 次</span>
            <span>{{ formatLastViewedAt(item.last_viewed_at) }}</span>
          </div>
          <div class="foot">
            <strong>¥ {{ item.price.toFixed(2) }}</strong>
            <span>月销 {{ item.monthly_sales }}</span>
          </div>
        </div>
      </article>
    </section>

    <section v-else class="empty-card">
      <div class="empty-copy">
        <p class="eyebrow">Empty</p>
        <h2>还没有历史浏览记录</h2>
        <p>先进入几个商品详情页，这里就会出现最近看过的商品列表。</p>
      </div>
      <button type="button" class="browse-btn" @click="router.push('/products')">去商品页</button>
    </section>
  </section>
</template>

<style scoped>
.history-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 18px 40px;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  padding: 26px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(255, 241, 211, 0.95), rgba(255, 255, 255, 0) 38%),
    linear-gradient(135deg, #2d2213, #6f5122);
  color: #fff7ea;
  box-shadow: 0 22px 44px rgba(60, 42, 17, 0.18);
}

.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 11px;
  color: rgba(255, 245, 224, 0.82);
}

.hero h1,
.empty-copy h2 {
  margin: 0;
}

.sub {
  margin: 10px 0 0;
  max-width: 560px;
  color: rgba(255, 246, 231, 0.84);
  line-height: 1.6;
}

.browse-btn {
  border: none;
  border-radius: 999px;
  padding: 12px 18px;
  cursor: pointer;
  background: #f5e3be;
  color: #3c2b12;
  font-weight: 700;
}

.error {
  margin: 14px 0;
  color: var(--danger);
}

.state-card,
.empty-card {
  margin-top: 18px;
  border-radius: 20px;
  border: 1px dashed #d8c8aa;
  background: linear-gradient(180deg, #fffdf8, #fff8ed);
  padding: 36px 28px;
}

.state-card {
  text-align: center;
  color: #726755;
}

.empty-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.empty-copy p:last-child {
  margin: 10px 0 0;
  color: #756a58;
}

.history-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.history-card {
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid #e6d8bb;
  background: #fffdf8;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.history-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 18px 32px rgba(67, 48, 20, 0.12);
}

.thumb {
  width: 100%;
  height: 180px;
  object-fit: cover;
}

.content {
  display: grid;
  gap: 10px;
  padding: 16px;
}

.head,
.meta,
.foot {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.category {
  color: #866c3c;
  font-size: 12px;
  font-weight: 700;
}

.brand {
  border-radius: 999px;
  padding: 4px 8px;
  background: #f6ecd9;
  color: #5d4824;
  font-size: 12px;
}

.content h2 {
  margin: 0;
  color: #2e2416;
  font-size: 18px;
  line-height: 1.45;
}

.shop {
  margin: 0;
  color: #6b614f;
}

.meta {
  color: #7a705f;
  font-size: 12px;
}

.foot strong {
  color: #3b2910;
}

.foot span {
  color: #736856;
  font-size: 12px;
}

@media (max-width: 860px) {
  .hero,
  .empty-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .browse-btn {
    width: 100%;
  }
}
</style>
