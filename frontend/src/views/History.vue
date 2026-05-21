<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import PageHero from '@/components/shared/PageHero.vue'
import EmptyState from '@/components/shared/EmptyState.vue'

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
  <section class="page-shell history-page">
    <PageHero
      eyebrow="History"
      title="历史浏览"
      accent="ink"
    >
      <template #actions>
        <Button variant="ghost" size="md" @click="router.push('/products')">继续逛商品</Button>
      </template>
    </PageHero>

    <p v-if="error" class="status-banner error">{{ error }}</p>
    <div v-if="loading" class="state-card">加载中...</div>

    <section v-else-if="hasItems" class="history-grid">
      <article
        v-for="item in items"
        :key="item.id"
        class="history-card"
        @click="openProductDetail(item.id)"
      >
        <img
          :src="item.image_url || '/demo-assets/products/default.svg'"
          :alt="item.name"
          class="thumb"
        >
        <div class="content">
          <div class="head">
            <Badge variant="muted">{{ item.category || '未分类' }}</Badge>
            <Badge v-if="item.brand" variant="default">{{ item.brand }}</Badge>
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

    <EmptyState
      v-else
      eyebrow="Empty"
      title="还没有历史浏览记录"
      description="先进入几个商品详情页，这里就会出现最近看过的商品列表。"
    >
      <Button variant="outline" @click="router.push('/products')">去商品页</Button>
    </EmptyState>
  </section>
</template>

<style scoped>
.history-page {
  display: grid;
  gap: 18px;
}

.state-card {
  min-height: 260px;
  display: grid;
  place-items: center;
  border-radius: 28px;
  border: 1px dashed rgba(106, 81, 47, 0.18);
  color: #726755;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.history-card {
  overflow: hidden;
  border-radius: 24px;
  border: 1px solid rgba(106, 81, 47, 0.14);
  background: rgba(255, 253, 248, 0.96);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  height: 100%;
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
  align-content: start;
  height: 100%;
}

.head,
.meta,
.foot {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.content h2 {
  margin: 0;
  color: #2e2416;
  font-size: 28px;
  line-height: 1.45;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  min-height: calc(28px * 1.45 * 2);
}

.shop {
  margin: 0;
  color: #6b614f;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-height: calc(14px * 1.5);
}

.meta {
  color: #7a705f;
  font-size: 12px;
  min-height: calc(12px * 1.5);
}

.foot strong {
  color: #3b2910;
}

.foot span {
  color: #736856;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.foot {
  margin-top: auto;
}
</style>
