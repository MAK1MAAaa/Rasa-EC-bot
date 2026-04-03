<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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

const canBuy = computed(() => Boolean(product.value && product.value.stock > 0))

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

  const safeQuantity = Math.min(Math.max(1, Number(quantity.value) || 1), product.value.stock)
  quantity.value = safeQuantity

  try {
    await cartStore.addToCart(product.value.id, safeQuantity)
    router.push('/cart')
  } catch (err: any) {
    alert(err.response?.data?.detail || '加入购物车失败')
  }
}

onMounted(loadProduct)
</script>

<template>
  <section class="detail-page">
    <button class="back-btn" type="button" @click="router.back()">← 返回</button>

    <div v-if="loading" class="state-card">正在加载商品详情...</div>
    <div v-else-if="error" class="state-card error">{{ error }}</div>

    <article v-else-if="product" class="detail-card">
      <img :src="product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1000&q=80'" :alt="product.name" class="cover">

      <div class="info">
        <span class="category">{{ product.category || '未分类' }}</span>
        <h1>{{ product.name }}</h1>
        <p class="desc">{{ product.description || '暂无商品描述。' }}</p>

        <div class="price-row">
          <span class="price">¥ {{ product.price.toFixed(2) }}</span>
          <span class="stock">库存 {{ product.stock }}</span>
        </div>

        <div class="buy-box">
          <label>购买数量</label>
          <input v-model.number="quantity" type="number" min="1" :max="product.stock" class="qty">
          <button type="button" :disabled="!canBuy" @click="addToCart">
            {{ canBuy ? '加入购物车' : '已售罄' }}
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
  background: #e2edf8;
  color: #23476f;
  border-radius: 10px;
  padding: 8px 12px;
  margin-bottom: 14px;
}

.state-card {
  background: #fff;
  border: 1px dashed #bfd2e6;
  border-radius: 16px;
  padding: 30px;
  text-align: center;
}

.state-card.error {
  color: #b91c1c;
}

.detail-card {
  background: #fff;
  border: 1px solid #d8e5f1;
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
  color: #0f766e;
  font-weight: 700;
  font-size: 13px;
}

.info h1 {
  margin: 0;
  color: #16395f;
}

.desc {
  margin: 0;
  color: #586f89;
  line-height: 1.7;
}

.price-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.price {
  font-size: 30px;
  color: #0b5aa6;
  font-weight: 700;
}

.stock {
  color: #6e8097;
}

.buy-box {
  margin-top: 8px;
  display: grid;
  gap: 10px;
}

.buy-box label {
  color: #2f4f6f;
  font-weight: 600;
}

.qty {
  width: 130px;
  border: 1px solid #c5d8ee;
  border-radius: 10px;
  padding: 10px 12px;
}

.buy-box button {
  width: 180px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #0b5aa6, #0f766e);
  color: #fff;
  font-weight: 600;
  padding: 10px 12px;
}

.buy-box button:disabled {
  background: #9aa8b8;
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
