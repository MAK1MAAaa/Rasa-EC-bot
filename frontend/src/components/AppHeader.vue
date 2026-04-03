<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const authStore = useAuthStore()
const cartStore = useCartStore()
const router = useRouter()
const route = useRoute()

const navClass = (target: string) => {
  const active = route.path.startsWith(target)
  return active ? 'nav-link active' : 'nav-link'
}

const username = computed(() => authStore.user?.username || '访客')

const logout = () => {
  authStore.clearAuth()
  cartStore.clear()
  router.push('/login')
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <router-link to="/products" class="brand">
        <span class="brand-dot"></span>
        <span>NEX SHOP</span>
      </router-link>

      <nav class="header-nav">
        <router-link :class="navClass('/products')" to="/products">商品</router-link>
        <router-link :class="navClass('/cart')" to="/cart">
          购物车
          <span v-if="cartStore.totalItems > 0" class="badge">{{ cartStore.totalItems }}</span>
        </router-link>
        <router-link :class="navClass('/orders')" to="/orders">我的订单</router-link>
      </nav>

      <div class="header-right" v-if="authStore.isLoggedIn">
        <span class="welcome">Hi, {{ username }}</span>
        <button class="logout-btn" @click="logout">退出登录</button>
      </div>

      <div class="header-right" v-else>
        <router-link to="/login" class="login-btn">登录</router-link>
        <router-link to="/register" class="logout-btn">注册</router-link>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(10px);
  background: rgba(251, 253, 255, 0.92);
  border-bottom: 1px solid #dbe6f3;
}

.header-inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.brand {
  text-decoration: none;
  color: #0f2d53;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.brand-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0ea5e9, #0f766e);
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.15);
}

.header-nav {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
}

.nav-link {
  text-decoration: none;
  color: #345372;
  padding: 8px 12px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.nav-link:hover {
  background: #ecf5ff;
  color: #0f2d53;
}

.nav-link.active {
  background: #dff0ff;
  color: #0b4f8c;
}

.badge {
  min-width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #ef4444;
  color: white;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
}

.header-right {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.welcome {
  color: #4b5f77;
  font-size: 14px;
}

.logout-btn,
.login-btn {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  text-decoration: none;
  cursor: pointer;
}

.logout-btn {
  background: #0f2d53;
  color: #fff;
}

.login-btn {
  background: #e7f2fd;
  color: #0b4f8c;
}

@media (max-width: 860px) {
  .header-inner {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
