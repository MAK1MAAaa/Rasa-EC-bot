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
  const active = route.path.startsWith(target) || (target === '/orders' && route.path.startsWith('/order/'))
  return active ? 'nav-link active' : 'nav-link'
}

const username = computed(() => authStore.user?.username || '访客')
const homeLink = computed(() => (authStore.isMerchant ? '/merchant' : '/products'))

const logout = () => {
  authStore.clearAuth()
  cartStore.clear()
  router.push('/login')
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <router-link :to="homeLink" class="brand">
        <span class="brand-dot"></span>
        <div class="brand-text">
          <span class="name">NEX SHOP</span>
          <span class="sub">精选好物</span>
        </div>
      </router-link>

      <nav v-if="authStore.isMerchant" class="header-nav">
        <router-link :class="navClass('/merchant')" to="/merchant">商家台</router-link>
        <router-link :class="navClass('/chat')" to="/chat">客服</router-link>
      </nav>

      <nav v-else class="header-nav">
        <router-link :class="navClass('/products')" to="/products">商品</router-link>
        <router-link :class="navClass('/chat')" to="/chat">客服</router-link>
        <router-link :class="navClass('/cart')" to="/cart">
          购物车
          <span v-if="cartStore.totalItems > 0" class="badge">{{ cartStore.totalItems }}</span>
        </router-link>
        <router-link :class="navClass('/orders')" to="/orders">订单</router-link>
      </nav>

      <div class="header-right" v-if="authStore.isLoggedIn">
        <span class="welcome">{{ username }}</span>
        <button class="logout-btn" @click="logout">退出</button>
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
  z-index: 30;
  backdrop-filter: blur(14px);
  background: rgba(255, 251, 241, 0.86);
  border-bottom: 1px solid var(--line);
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
  color: var(--text);
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.brand-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: linear-gradient(130deg, var(--brand), var(--accent));
  box-shadow: 0 0 0 5px rgba(182, 134, 62, 0.16);
}

.brand-text {
  display: grid;
}

.name {
  font-weight: 700;
  letter-spacing: 0.08em;
}

.sub {
  font-size: 11px;
  color: var(--text-muted);
}

.header-nav {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
}

.nav-link {
  text-decoration: none;
  color: #5e5a52;
  padding: 8px 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.nav-link:hover {
  background: #f5ecda;
  color: #2b2a26;
}

.nav-link.active {
  background: #33250f;
  color: #fff7ea;
}

.badge {
  min-width: 20px;
  height: 20px;
  border-radius: 999px;
  background: var(--danger);
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
  color: var(--text-muted);
  font-size: 14px;
}

.logout-btn,
.login-btn {
  border: none;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  text-decoration: none;
  cursor: pointer;
}

.logout-btn {
  background: #2f2413;
  color: #fff6e8;
}

.login-btn {
  background: #f2e7d3;
  color: #3d3529;
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

