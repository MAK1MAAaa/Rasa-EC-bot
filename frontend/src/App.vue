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
  inset: 0;
  pointer-events: none;
  background-image: radial-gradient(rgba(62, 42, 19, 0.04) 0.8px, transparent 0.8px);
  background-size: 3px 3px;
  opacity: 0.42;
}

.page-body {
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

.page-body.with-header {
  min-height: calc(100vh - 74px);
}
</style>
