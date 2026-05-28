import { createRouter, createWebHistory } from 'vue-router'
const Login = () => import('@/views/Login.vue')
const Register = () => import('@/views/Register.vue')
const Products = () => import('@/views/Products.vue')
const ProductDetail = () => import('@/views/ProductDetail.vue')
const Cart = () => import('@/views/Cart.vue')
const Checkout = () => import('@/views/Checkout.vue')
const OrderList = () => import('@/views/OrderList.vue')
const OrderDetail = () => import('@/views/OrderDetail.vue')
const History = () => import('@/views/History.vue')
const ChatSupport = () => import('@/views/ChatSupport.vue')
const MerchantCenter = () => import('@/views/MerchantCenter.vue')

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
      path: '/merchant',
      name: 'MerchantCenter',
      component: MerchantCenter,
      meta: { requiresAuth: true, merchantOnly: true }
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
      meta: { requiresAuth: true, customerOnly: true }
    },
    {
      path: '/checkout',
      name: 'Checkout',
      component: Checkout,
      meta: { requiresAuth: true, customerOnly: true }
    },
    {
      path: '/orders',
      name: 'OrderList',
      component: OrderList,
      meta: { requiresAuth: true, customerOnly: true }
    },
    {
      path: '/history',
      name: 'History',
      component: History,
      meta: { requiresAuth: true, customerOnly: true }
    },
    {
      path: '/order/:id',
      name: 'OrderDetail',
      component: OrderDetail,
      props: true,
      meta: { requiresAuth: true, customerOnly: true }
    },
    {
      path: '/orders/:id',
      redirect: (to) => `/order/${to.params.id}`
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
  const role = localStorage.getItem('user_role')

  if (to.meta.requiresAuth && !token) {
    return {
      path: '/login',
      query: { redirect: to.fullPath }
    }
  }

  if (to.meta.merchantOnly && role !== 'merchant') {
    return role === 'customer' ? '/products' : '/login'
  }

  if (to.meta.customerOnly && role === 'merchant') {
    return '/merchant'
  }

  if (to.path.startsWith('/chat') && role === 'merchant') {
    return '/merchant'
  }

  if (to.meta.guestOnly && token) {
    return role === 'merchant' ? '/merchant' : '/products'
  }

  return true
})

export default router
