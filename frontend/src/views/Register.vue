<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Blocks, HeartHandshake, ShoppingBag } from 'lucide-vue-next'
import api from '@/api/client'
import Button from '@/components/ui/Button.vue'

const router = useRouter()

const username = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const handleRegister = async () => {
  loading.value = true
  error.value = ''

  try {
    await api.post('/auth/register', {
      username: username.value.trim(),
      email: email.value.trim().toLowerCase(),
      password: password.value
    })
    router.push('/login')
  } catch (err: any) {
    error.value = err.response?.data?.detail || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-shell reverse">
      <form class="auth-card" @submit.prevent="handleRegister">
        <div class="card-head">
          <p class="eyebrow muted">Create Account</p>
          <h2>创建账号</h2>
        </div>

        <label class="field">
          <span>用户名</span>
          <input v-model="username" class="field-input" type="text" placeholder="请输入用户名" required>
        </label>

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
          {{ loading ? '注册中...' : '注册' }}
        </Button>

        <div class="auth-links">
          <p>已有账号？<router-link to="/login">立即登录</router-link></p>
          <router-link class="browse-link" to="/products">先看看商品</router-link>
        </div>
      </form>

      <aside class="auth-showcase ink">
        <p class="eyebrow">Customer Journey</p>
        <h1>从浏览到下单，再到客服与售后，账号会把你的行为串起来。</h1>
        <p class="copy">注册后，历史浏览、购物车、订单和售后处理都能在统一体验里延续，不再反复跳转与丢失上下文。</p>

        <div class="feature-list">
          <article>
            <ShoppingBag :size="18" />
            <div>
              <strong>保存浏览与购物车</strong>
              <span>商品偏好会沉淀下来，客服推荐也能更贴近你的浏览上下文。</span>
            </div>
          </article>
          <article>
            <HeartHandshake :size="18" />
            <div>
              <strong>订单与售后闭环</strong>
              <span>取消订单、改地址、投诉物流和售后动作都保留在统一订单视图中。</span>
            </div>
          </article>
          <article>
            <Blocks :size="18" />
            <div>
              <strong>一致的工作流界面</strong>
              <span>同一套设计系统覆盖访客、买家、客服和商家角色。</span>
            </div>
          </article>
        </div>
      </aside>
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
  grid-template-columns: 460px minmax(0, 1.15fr);
  gap: 18px;
  align-items: stretch;
}

.auth-shell.reverse {
  grid-template-columns: 460px minmax(0, 1fr);
}

.auth-card,
.auth-showcase {
  border-radius: 30px;
  border: 1px solid rgba(108, 80, 42, 0.14);
  box-shadow: var(--shadow-panel);
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

.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
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

.auth-showcase {
  padding: 34px;
  color: #fff7ed;
  background:
    radial-gradient(circle at left top, rgba(164, 224, 214, 0.16), transparent 30%),
    linear-gradient(135deg, #131513 0%, #3a332c 48%, #7d6e5f 100%);
  display: grid;
  align-content: space-between;
  gap: 24px;
}

.auth-showcase h1 {
  margin: 8px 0 0;
  font-size: clamp(38px, 4.6vw, 64px);
  line-height: 0.95;
}

.copy {
  max-width: 520px;
  line-height: 1.8;
  color: rgba(255, 247, 237, 0.8);
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
  border: 1px solid rgba(255, 246, 232, 0.1);
}

.feature-list strong {
  display: block;
  margin-bottom: 4px;
}

.feature-list span {
  color: rgba(255, 247, 237, 0.74);
  font-size: 13px;
  line-height: 1.7;
}

@media (max-width: 980px) {
  .auth-shell,
  .auth-shell.reverse {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .auth-page {
    padding: 14px;
  }

  .auth-card,
  .auth-showcase {
    border-radius: 24px;
    padding: 22px;
  }

  .auth-showcase h1,
  .card-head h2 {
    font-size: 34px;
  }
}
</style>
