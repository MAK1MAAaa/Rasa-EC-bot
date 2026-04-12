<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dialog, DialogPanel, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { Clock3, LogOut, Menu, MessageSquare, Package, ShoppingBag, Store, UserRound, X } from 'lucide-vue-next'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'

const authStore = useAuthStore()
const cartStore = useCartStore()
const router = useRouter()
const route = useRoute()
const mobileMenuOpen = ref(false)

const customerNav = [
  { label: '精选商品', to: '/products', icon: ShoppingBag },
  { label: '智能客服', to: '/chat', icon: MessageSquare },
  { label: '我的订单', to: '/orders', icon: Package },
  { label: '历史浏览', to: '/history', icon: Clock3 }
]

const merchantNav = [{ label: '商家工作台', to: '/merchant', icon: Store }]

const navItems = computed(() => (authStore.isMerchant ? merchantNav : customerNav))
const username = computed(() => authStore.user?.username || '访客')
const homeLink = computed(() => (authStore.isMerchant ? '/merchant' : '/products'))

const isActive = (target: string) => route.path.startsWith(target) || (target === '/orders' && route.path.startsWith('/order/'))

const logout = () => {
  authStore.clearAuth()
  cartStore.clear()
  mobileMenuOpen.value = false
  router.push('/login')
}

const closeMenu = () => {
  mobileMenuOpen.value = false
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <router-link :to="homeLink" class="brand" @click="closeMenu">
        <span class="brand-mark">
          <span class="brand-core"></span>
        </span>
        <div class="brand-copy">
          <span class="brand-name">NEX Atelier</span>
          <span class="brand-sub">新零售客服与商家协同台</span>
        </div>
      </router-link>

      <nav class="header-nav desktop-only">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ active: isActive(item.to) }"
        >
          <component :is="item.icon" :size="16" />
          <span>{{ item.label }}</span>
        </router-link>
        <router-link v-if="!authStore.isMerchant" to="/cart" class="nav-link nav-cart" :class="{ active: isActive('/cart') }">
          <ShoppingBag :size="16" />
          <span>购物车</span>
          <Badge v-if="cartStore.totalItems > 0" variant="danger">{{ cartStore.totalItems }}</Badge>
        </router-link>
      </nav>

      <div class="header-right desktop-only">
        <div class="account-chip">
          <UserRound :size="16" />
          <span>{{ username }}</span>
        </div>
        <router-link v-if="!authStore.isLoggedIn" to="/login">
          <Button as="span" variant="outline" size="sm">登录</Button>
        </router-link>
        <router-link v-if="!authStore.isLoggedIn" to="/register">
          <Button as="span" variant="default" size="sm">注册</Button>
        </router-link>
        <Button v-if="authStore.isLoggedIn" variant="outline" size="sm" @click="logout">
          <LogOut :size="15" />
          退出
        </Button>
      </div>

      <button class="menu-trigger mobile-only" type="button" @click="mobileMenuOpen = true">
        <Menu :size="20" />
      </button>
    </div>

    <TransitionRoot :show="mobileMenuOpen" as="template">
      <Dialog class="mobile-sheet" @close="closeMenu">
        <TransitionChild
          as="template"
          enter="ease-out duration-200"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="ease-in duration-150"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div class="mobile-backdrop" />
        </TransitionChild>

        <div class="mobile-frame">
          <TransitionChild
            as="template"
            enter="ease-out duration-200"
            enter-from="opacity-0 translate-x-8"
            enter-to="opacity-100 translate-x-0"
            leave="ease-in duration-150"
            leave-from="opacity-100 translate-x-0"
            leave-to="opacity-0 translate-x-8"
          >
            <DialogPanel class="mobile-panel">
              <div class="mobile-head">
                <div>
                  <p class="mobile-eyebrow">Navigation</p>
                  <h2>{{ username }}</h2>
                </div>
                <button class="mobile-close" type="button" @click="closeMenu">
                  <X :size="18" />
                </button>
              </div>

              <nav class="mobile-nav">
                <router-link
                  v-for="item in navItems"
                  :key="item.to"
                  :to="item.to"
                  class="mobile-link"
                  :class="{ active: isActive(item.to) }"
                  @click="closeMenu"
                >
                  <component :is="item.icon" :size="16" />
                  <span>{{ item.label }}</span>
                </router-link>

                <router-link
                  v-if="!authStore.isMerchant"
                  to="/cart"
                  class="mobile-link"
                  :class="{ active: isActive('/cart') }"
                  @click="closeMenu"
                >
                  <ShoppingBag :size="16" />
                  <span>购物车</span>
                  <Badge v-if="cartStore.totalItems > 0" variant="danger">{{ cartStore.totalItems }}</Badge>
                </router-link>
              </nav>

              <div class="mobile-actions">
                <router-link v-if="!authStore.isLoggedIn" to="/login" @click="closeMenu">
                  <Button as="span" variant="outline" block>登录</Button>
                </router-link>
                <router-link v-if="!authStore.isLoggedIn" to="/register" @click="closeMenu">
                  <Button as="span" block>注册</Button>
                </router-link>
                <Button v-if="authStore.isLoggedIn" variant="outline" block @click="logout">退出当前账号</Button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </Dialog>
    </TransitionRoot>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 40;
  padding: 16px 12px 0;
}

.header-inner {
  max-width: calc(var(--container-width) + 24px);
  margin: 0 auto;
  min-height: 78px;
  padding: 14px 18px;
  border: 1px solid rgba(108, 80, 42, 0.14);
  border-radius: 26px;
  background: rgba(255, 250, 242, 0.72);
  backdrop-filter: blur(16px);
  box-shadow: 0 18px 40px rgba(39, 28, 10, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  text-decoration: none;
}

.brand-mark {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(34, 24, 12, 0.94), rgba(178, 122, 50, 0.9));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16);
}

.brand-core {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  background: linear-gradient(135deg, #ffedc8, #f3bf71);
  box-shadow: 0 0 0 6px rgba(255, 239, 209, 0.16);
}

.brand-copy {
  min-width: 0;
  display: grid;
}

.brand-name {
  font-size: 20px;
  font-weight: 800;
  color: #271c11;
}

.brand-sub {
  color: var(--text-soft);
  font-size: 11px;
  letter-spacing: 0.08em;
}

.header-nav {
  flex: 1;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}

.nav-link,
.mobile-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 14px;
  text-decoration: none;
  color: #4d4030;
  border-radius: 999px;
  border: 1px solid transparent;
}

.nav-link:hover,
.mobile-link:hover,
.nav-link.active,
.mobile-link.active {
  background: rgba(255, 251, 245, 0.94);
  border-color: rgba(113, 85, 48, 0.14);
  box-shadow: 0 8px 18px rgba(45, 29, 8, 0.06);
}

.nav-cart {
  background: rgba(47, 95, 89, 0.06);
}

.header-right {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.account-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 14px;
  border-radius: 999px;
  color: #55493b;
  background: rgba(255, 255, 255, 0.58);
  border: 1px solid rgba(110, 84, 48, 0.12);
}

.menu-trigger,
.mobile-close {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: rgba(255, 253, 249, 0.9);
  color: #2c2113;
}

.mobile-only {
  display: none;
}

.mobile-sheet {
  position: relative;
  z-index: 60;
}

.mobile-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(22, 16, 10, 0.48);
  backdrop-filter: blur(6px);
}

.mobile-frame {
  position: fixed;
  inset: 0;
  display: flex;
  justify-content: flex-end;
  padding: 14px;
}

.mobile-panel {
  width: min(100%, 340px);
  height: calc(100vh - 28px);
  border-radius: 28px;
  border: 1px solid rgba(109, 81, 44, 0.14);
  background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(245, 238, 228, 0.96));
  box-shadow: 0 28px 80px rgba(26, 19, 12, 0.18);
  padding: 18px;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 16px;
}

.mobile-head {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 12px;
}

.mobile-eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-soft);
}

.mobile-head h2 {
  margin: 4px 0 0;
  color: var(--text);
}

.mobile-nav {
  display: grid;
  gap: 10px;
  align-content: start;
}

.mobile-link {
  justify-content: space-between;
  min-height: 48px;
  padding: 0 16px;
  background: rgba(255, 255, 255, 0.58);
}

.mobile-actions {
  display: grid;
  gap: 10px;
}

@media (max-width: 980px) {
  .desktop-only {
    display: none;
  }

  .mobile-only {
    display: inline-grid;
  }

  .header-inner {
    min-height: 70px;
    padding: 12px 14px;
  }

  .brand-sub {
    display: none;
  }
}
</style>
