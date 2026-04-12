<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import Button from '@/components/ui/Button.vue'
import PageHero from '@/components/shared/PageHero.vue'
import EmptyState from '@/components/shared/EmptyState.vue'

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
  <section class="page-shell checkout-page">
    <PageHero
      eyebrow="Checkout"
      title="把收货信息和订单摘要放在同一视口里，减少最后一步的切换成本。"
      description="确认地址、邮箱和订单金额后即可直接提交，不打断已有购物上下文。"
      accent="teal"
    />

    <div v-if="loading" class="state-card">加载中...</div>

    <EmptyState
      v-else-if="cartStore.items.length === 0"
      eyebrow="Cart Empty"
      title="购物车为空"
      description="先挑选一些商品，再回到这里完成下单。"
    >
      <Button variant="outline" @click="router.push('/products')">去选购</Button>
    </EmptyState>

    <div v-else class="page-grid-two">
      <div class="panel-surface form-card">
        <div class="surface-title">
          <h2>收货信息</h2>
          <p>填写详细地址和联系邮箱，订单提交后可以在订单详情页继续查看或修改待发货收货信息。</p>
        </div>

        <label class="field">
          <span>地址</span>
          <textarea v-model="address" class="field-textarea" rows="4" placeholder="请输入详细地址"></textarea>
        </label>

        <label class="field">
          <span>邮箱</span>
          <input v-model="contactEmail" class="field-input" type="email" placeholder="you@example.com">
        </label>

        <p v-if="error" class="status-banner error">{{ error }}</p>

        <Button size="lg" :disabled="submitting" @click="submitOrder">
          {{ submitting ? '提交中...' : '确认下单' }}
        </Button>
      </div>

      <aside class="panel-surface summary-card">
        <div class="surface-title">
          <h2>订单摘要</h2>
          <p>下单前再核对一次商品数量和金额。</p>
        </div>
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
  display: grid;
  gap: 18px;
}

.state-card {
  min-height: 280px;
  display: grid;
  place-items: center;
  border-radius: 28px;
  border: 1px dashed rgba(106, 81, 47, 0.18);
  color: #6b6153;
}

.form-card,
.summary-card {
  padding: 24px;
}

.form-card {
  display: grid;
  gap: 14px;
}

.field {
  display: grid;
  gap: 8px;
}

.field span {
  font-size: 13px;
  color: #61584b;
  font-weight: 700;
}

.summary-card {
  display: grid;
  gap: 16px;
  align-content: start;
}

.summary-card ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.summary-card li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #5b5244;
  font-size: 14px;
}

.total {
  border-top: 1px dashed #d6c8ae;
  padding-top: 10px;
  font-size: 20px;
  font-weight: 700;
  color: #3e2c12;
}
</style>
