<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'

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
  <div class="auth-page">
    <form class="auth-card" @submit.prevent="handleRegister">
      <h1>创建账户</h1>
      <p class="subtitle">注册后即可添加商品到购物车并下单</p>

      <label>用户名</label>
      <input v-model="username" type="text" placeholder="请输入用户名" required>

      <label>邮箱</label>
      <input v-model="email" type="email" placeholder="you@example.com" required>

      <label>密码</label>
      <input v-model="password" type="password" placeholder="请输入密码" required>

      <p v-if="error" class="error">{{ error }}</p>

      <button :disabled="loading" type="submit">
        {{ loading ? '注册中...' : '注册' }}
      </button>

      <p class="switch-link">
        已有账号？<router-link to="/login">立即登录</router-link>
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
  max-width: 420px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #d7e5f4;
  border-radius: 18px;
  box-shadow: 0 22px 48px rgba(15, 45, 83, 0.12);
  padding: 32px;
  display: grid;
  gap: 12px;
}

.auth-card h1 {
  margin: 0;
  color: #0f2d53;
}

.subtitle {
  margin: 0 0 8px 0;
  color: #60758f;
}

label {
  font-size: 14px;
  color: #2f4f6f;
  font-weight: 600;
}

input {
  border: 1px solid #c9d9ea;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 14px;
}

input:focus {
  outline: none;
  border-color: #0ea5e9;
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.16);
}

button {
  margin-top: 6px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #0b5aa6, #0f766e);
  color: white;
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
  color: #dc2626;
  font-size: 14px;
}

.switch-link {
  margin: 4px 0 0;
  font-size: 14px;
  color: #4d637b;
  text-align: center;
}

.switch-link a {
  color: #0b5aa6;
  text-decoration: none;
  font-weight: 600;
}
</style>
