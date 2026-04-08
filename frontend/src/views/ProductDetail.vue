<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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
let realtimeClient: ReturnType<typeof createRealtimeClient> | null = null
let realtimeRefreshTimer: ReturnType<typeof setTimeout> | null = null

const canBuy = computed(() => Boolean(product.value && product.value.stock > 0 && authStore.isCustomer))
const fromSource = computed(() => (typeof route.query.from === 'string' ? route.query.from.trim() : ''))

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
  <section class="detail-page">
    <button class="back-btn" type="button" @click="handleBack()">← 返回</button>

    <div v-if="loading" class="state-card">加载中...</div>
    <div v-else-if="error" class="state-card error">{{ error }}</div>

    <article v-else-if="product" class="detail-card">
      <img :src="product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1000&q=80'" :alt="product.name" class="cover">

      <div class="info">
        <span class="category">{{ product.category || '未分类' }}</span>
        <h1>{{ product.name }}</h1>
        <button class="shop-btn" type="button" @click="jumpToShop">{{ product.shop_name }}</button>

        <div class="price-row">
          <span class="price">¥ {{ product.price.toFixed(2) }}</span>
          <span class="stock">库存 {{ product.stock }}</span>
        </div>

        <div class="buy-box">
          <label>数量</label>
          <input v-model.number="quantity" type="number" min="1" :max="product.stock" class="qty">
          <button type="button" :disabled="!canBuy" @click="addToCart">
            {{ canBuy ? '加入购物车' : authStore.isMerchant ? '商家账号不可购买' : '已售罄' }}
          </button>
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

.price-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.price {
  font-size: 30px;
  color: #3f2b10;
  font-weight: 700;
}

.stock {
  color: #756b5d;
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

@media (max-width: 860px) {
  .detail-card {
    grid-template-columns: 1fr;
  }

  .cover {
    min-height: 220px;
  }
}
</style>


