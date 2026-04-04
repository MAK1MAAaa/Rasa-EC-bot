<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

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
  <div class="auth-page">
    <form class="auth-card" @submit.prevent="handleLogin">
      <h1>账号登录</h1>

      <label>邮箱</label>
      <input v-model="email" type="email" placeholder="you@example.com" required>

      <label>密码</label>
      <input v-model="password" type="password" placeholder="请输入密码" required>

      <p v-if="error" class="error">{{ error }}</p>

      <button :disabled="loading" type="submit">
        {{ loading ? '登录中...' : '登录' }}
      </button>

      <p class="switch-link">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </p>
      <p class="switch-link ghost-link">
        <router-link to="/products">继续逛商品</router-link>
      </p>
    </form>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.auth-card {
  width: 100%;
  max-width: 440px;
  background: var(--surface-strong);
  border: 1px solid var(--line);
  border-radius: 22px;
  box-shadow: var(--shadow-soft);
  padding: 34px;
  display: grid;
  gap: 12px;
}

.auth-card h1 {
  margin: 0 0 8px;
  color: #2f2516;
}

label {
  font-size: 13px;
  color: #625a4f;
  font-weight: 600;
}

input {
  border: 1px solid #d6ccb8;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 14px;
  background: #fffcf5;
}

input:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 4px rgba(182, 134, 62, 0.15);
}

button {
  margin-top: 6px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #2f2413, #765322);
  color: #fff;
  font-weight: 600;
  padding: 12px;
  cursor: pointer;
}

button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.error {
  margin: 0;
  color: var(--danger);
  font-size: 14px;
}

.switch-link {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--text-muted);
  text-align: center;
}

.switch-link a {
  color: var(--brand-strong);
  text-decoration: none;
  font-weight: 600;
}

.ghost-link {
  font-size: 13px;
}
</style>
