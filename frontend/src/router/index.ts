import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import Products from '@/views/Products.vue'
import ProductDetail from '@/views/ProductDetail.vue'
import Cart from '@/views/Cart.vue'
import Checkout from '@/views/Checkout.vue'
import Orders from '@/views/Orders.vue'
import ChatSupport from '@/views/ChatSupport.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: Login,
      meta: { hideHeader: true, guestOnly: true }
    },
    {
      path: '/register',
      name: 'Register',
      component: Register,
      meta: { hideHeader: true, guestOnly: true }
    },
    {
      path: '/products',
      name: 'Products',
      component: Products
    },
    {
      path: '/products/:id',
      name: 'ProductDetail',
      component: ProductDetail,
      props: true
    },
    {
      path: '/cart',
      name: 'Cart',
      component: Cart,
      meta: { requiresAuth: true }
    },
    {
      path: '/checkout',
      name: 'Checkout',
      component: Checkout,
      meta: { requiresAuth: true }
    },
    {
      path: '/orders',
      name: 'Orders',
      component: Orders,
      meta: { requiresAuth: true }
    },
    {
      path: '/chat',
      name: 'ChatSupport',
      component: ChatSupport
    },
    {
      path: '/',
      redirect: '/products'
    }
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    return {
      path: '/login',
      query: { redirect: to.fullPath }
    }
  }
  if (to.meta.guestOnly && token) {
    return '/products'
  }
  return true
})

export default router
