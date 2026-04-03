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
  if (authStore.isLoggedIn) {
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
  background:
    radial-gradient(circle at 10% 10%, rgba(14, 165, 233, 0.14), transparent 26%),
    radial-gradient(circle at 90% 0%, rgba(15, 118, 110, 0.12), transparent 30%),
    #f4f8fd;
}

.page-body {
  min-height: 100vh;
}

.page-body.with-header {
  min-height: calc(100vh - 66px);
}
</style>
