<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const route = useRoute()
const authStore = useAuthStore()
const cartStore = useCartStore()

const showHeader = computed(() => !route.meta.hideHeader)

onMounted(async () => {
  await authStore.initialize()
  if (authStore.isLoggedIn && authStore.isCustomer) {
    try {
      await cartStore.refreshCart()
    } catch {
      cartStore.clear()
    }
  } else {
    cartStore.clear()
  }
})
</script>

<template>
  <div class="app-shell">
    <AppHeader v-if="showHeader" />
    <main :class="showHeader ? 'page-body with-header' : 'page-body'">
      <router-view />
    </main>
  </div>
</template>

<style>
.app-shell {
  min-height: 100vh;
  position: relative;
}

.app-shell::before {
  content: '';
  position: fixed;
  inset: -18% -10% auto auto;
  width: 420px;
  height: 420px;
  pointer-events: none;
  background: radial-gradient(circle, rgba(178, 122, 50, 0.12), transparent 72%);
  filter: blur(12px);
}

.app-shell::after {
  content: '';
  position: fixed;
  inset: auto auto -14% -8%;
  width: 360px;
  height: 360px;
  pointer-events: none;
  background: radial-gradient(circle, rgba(47, 95, 89, 0.12), transparent 70%);
  filter: blur(12px);
}

.page-body {
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

.page-body.with-header {
  min-height: calc(100vh - 92px);
  padding-top: 4px;
}
</style>
