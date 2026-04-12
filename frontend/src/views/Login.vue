<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ShieldCheck, ShoppingBag, Sparkles } from 'lucide-vue-next'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import Button from '@/components/ui/Button.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const cartStore = useCartStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const handleLogin = async () => {
  loading.value = true
  error.value = ''

  try {
    const response = await api.post('/auth/login', {
      email: email.value.trim().toLowerCase(),
      password: password.value
    })

    authStore.setToken(response.data.access_token)
    await authStore.fetchMe()

    if (authStore.isCustomer) {
      await cartStore.refreshCart()
    } else {
      cartStore.clear()
    }

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    if (redirect) {
      router.push(redirect)
      return
    }
    router.push(authStore.isMerchant ? '/merchant' : '/products')
  } catch (err: any) {
    error.value = err.response?.data?.detail || '登录失败，请检查账号密码'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-shell">
      <aside class="auth-showcase">
        <p class="eyebrow">NEX Atelier</p>
        <h1>让商城、客服与商家工作台在同一套界面里顺畅协同。</h1>
        <p class="copy">统一管理商品浏览、订单处理、客服对话与商家履约动作，保持从访客到运营侧的一致体验。</p>

        <div class="feature-list">
          <article>
            <ShoppingBag :size="18" />
            <div>
              <strong>电商主链路</strong>
              <span>商品、购物车、结算、订单与历史浏览串成完整零售体验。</span>
            </div>
          </article>
          <article>
            <ShieldCheck :size="18" />
            <div>
              <strong>客服协同</strong>
              <span>待确认动作、图片售后与结构化卡片都保持可控交互。</span>
            </div>
          </article>
          <article>
            <Sparkles :size="18" />
            <div>
              <strong>商家工作台</strong>
              <span>订单履约、商品维护和售后处理落在统一的仪表盘版式里。</span>
            </div>
          </article>
        </div>
      </aside>

      <form class="auth-card" @submit.prevent="handleLogin">
        <div class="card-head">
          <p class="eyebrow muted">Account Access</p>
          <h2>账号登录</h2>
          <p>输入邮箱与密码，继续当前商城浏览或进入商家工作台。</p>
        </div>

        <label class="field">
          <span>邮箱</span>
          <input v-model="email" class="field-input" type="email" placeholder="you@example.com" required>
        </label>

        <label class="field">
          <span>密码</span>
          <input v-model="password" class="field-input" type="password" placeholder="请输入密码" required>
        </label>

        <p v-if="error" class="status-banner error">{{ error }}</p>

        <Button type="submit" size="lg" block :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </Button>

        <div class="auth-links">
          <p>还没有账号？<router-link to="/register">立即注册</router-link></p>
          <router-link class="browse-link" to="/products">继续逛商品</router-link>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: 24px;
  display: grid;
  place-items: center;
}

.auth-shell {
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) 460px;
  gap: 18px;
  align-items: stretch;
}

.auth-showcase,
.auth-card {
  border-radius: 30px;
  border: 1px solid rgba(108, 80, 42, 0.14);
  box-shadow: var(--shadow-panel);
}

.auth-showcase {
  padding: 34px;
  color: #fff7ed;
  background:
    radial-gradient(circle at right top, rgba(255, 240, 205, 0.2), transparent 26%),
    linear-gradient(135deg, #1f1710 0%, #6f4720 52%, #b27a32 100%);
  display: grid;
  align-content: space-between;
  gap: 24px;
}

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.auth-showcase h1 {
  margin: 8px 0 0;
  font-size: clamp(38px, 4.6vw, 64px);
  line-height: 0.95;
}

.copy {
  max-width: 520px;
  line-height: 1.8;
  color: rgba(255, 247, 237, 0.82);
}

.feature-list {
  display: grid;
  gap: 12px;
}

.feature-list article {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 246, 232, 0.12);
}

.feature-list strong {
  display: block;
  margin-bottom: 4px;
}

.feature-list span {
  color: rgba(255, 247, 237, 0.76);
  font-size: 13px;
  line-height: 1.7;
}

.auth-card {
  padding: 28px;
  background: linear-gradient(180deg, rgba(255, 253, 249, 0.96), rgba(248, 241, 231, 0.94));
  display: grid;
  align-content: center;
  gap: 14px;
}

.card-head {
  display: grid;
  gap: 6px;
}

.card-head h2 {
  margin: 0;
  font-size: 40px;
}

.card-head p {
  color: var(--text-muted);
  line-height: 1.7;
}

.muted {
  color: var(--text-soft);
}

.field {
  display: grid;
  gap: 8px;
}

.field span {
  color: #5b4e3f;
  font-size: 13px;
  font-weight: 700;
}

.auth-links {
  display: grid;
  gap: 10px;
  justify-items: center;
  color: var(--text-muted);
  font-size: 14px;
}

.auth-links a {
  color: var(--brand-strong);
  text-decoration: none;
  font-weight: 700;
}

.browse-link {
  font-size: 13px;
}

@media (max-width: 980px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .auth-page {
    padding: 14px;
  }

  .auth-showcase,
  .auth-card {
    border-radius: 24px;
    padding: 22px;
  }

  .auth-showcase h1,
  .card-head h2 {
    font-size: 34px;
  }
}
</style>
