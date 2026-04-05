<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const authStore = useAuthStore()
const cartStore = useCartStore()

const loading = ref(false)
const submitting = ref(false)
const address = ref('')
const contactEmail = ref('')
const error = ref('')

const loadPage = async () => {
  loading.value = true
  try {
    await cartStore.refreshCart()
    if (authStore.user?.email) {
      contactEmail.value = authStore.user.email
    }
  } finally {
    loading.value = false
  }
}

const submitOrder = async () => {
  if (!address.value.trim()) {
    error.value = '请填写收货地址'
    return
  }
  if (!contactEmail.value.trim()) {
    error.value = '请填写联系邮箱'
    return
  }

  error.value = ''
  submitting.value = true
  try {
    const response = await api.post('/orders', {
      address: address.value.trim(),
      contact_email: contactEmail.value.trim().toLowerCase()
    })
    await cartStore.refreshCart()
    router.push({ path: `/order/${response.data.id}` })
  } catch (err: any) {
    error.value = err.response?.data?.detail || '下单失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

onMounted(loadPage)
</script>

<template>
  <section class="checkout-page">
    <h1>提交订单</h1>

    <div v-if="loading" class="state-card">加载中...</div>

    <div v-else-if="cartStore.items.length === 0" class="state-card">
      购物车为空
      <button type="button" @click="router.push('/products')">去选购</button>
    </div>

    <div v-else class="checkout-layout">
      <div class="form-card">
        <h2>收货信息</h2>

        <label>地址</label>
        <textarea v-model="address" rows="4" placeholder="请输入详细地址"></textarea>

        <label>邮箱</label>
        <input v-model="contactEmail" type="email" placeholder="you@example.com">

        <p v-if="error" class="error">{{ error }}</p>

        <button type="button" :disabled="submitting" @click="submitOrder">
          {{ submitting ? '提交中...' : '确认下单' }}
        </button>
      </div>

      <aside class="summary-card">
        <h2>商品</h2>
        <ul>
          <li v-for="item in cartStore.items" :key="item.id">
            <span>{{ item.product_name }} x {{ item.quantity }}</span>
            <strong>¥ {{ item.subtotal.toFixed(2) }}</strong>
          </li>
        </ul>
        <div class="total">合计 ¥ {{ cartStore.totalAmount.toFixed(2) }}</div>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.checkout-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 18px 38px;
}

.checkout-page h1 {
  margin: 0 0 14px;
  color: #2f2618;
}

.state-card {
  background: var(--surface-strong);
  border: 1px dashed #d8ccb6;
  border-radius: 16px;
  padding: 30px;
  text-align: center;
  color: #6b6153;
}

.state-card button {
  margin-top: 12px;
  border: none;
  border-radius: 999px;
  background: #2f2413;
  color: #fff6e8;
  padding: 10px 14px;
}

.checkout-layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
}

.form-card,
.summary-card {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px;
}

.form-card {
  display: grid;
  gap: 10px;
}

.form-card h2,
.summary-card h2 {
  margin: 0 0 8px;
  color: #312819;
}

label {
  font-size: 13px;
  color: #61584b;
  font-weight: 600;
}

textarea,
input {
  border: 1px solid #d8ccb5;
  border-radius: 12px;
  padding: 11px 12px;
  font-size: 14px;
  background: #fffcf5;
}

button {
  width: fit-content;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #2f2413, #765322);
  color: #fff7ea;
  font-weight: 600;
  padding: 10px 16px;
}

button:disabled {
  opacity: 0.7;
}

.error {
  margin: 0;
  color: var(--danger);
  font-size: 14px;
}

.summary-card ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.summary-card li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #5b5244;
}

.total {
  margin-top: 12px;
  border-top: 1px dashed #d6c8ae;
  padding-top: 10px;
  font-size: 20px;
  font-weight: 700;
  color: #3e2c12;
}

@media (max-width: 920px) {
  .checkout-layout {
    grid-template-columns: 1fr;
  }
}
</style>
