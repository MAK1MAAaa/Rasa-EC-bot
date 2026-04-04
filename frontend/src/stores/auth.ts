import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '@/api/client'

interface AuthUser {
  id: string
  username: string
  email: string
  role: 'customer' | 'merchant'
  shop?: {
    id: string
    name: string
  } | null
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token'))
  const user = ref<AuthUser | null>(null)
  const initialized = ref(false)

  const isLoggedIn = computed(() => Boolean(token.value))
  const isMerchant = computed(() => user.value?.role === 'merchant')
  const isCustomer = computed(() => user.value?.role === 'customer')

  const setToken = (value: string) => {
    token.value = value
    localStorage.setItem('token', value)
  }

  const setUser = (payload: AuthUser | null) => {
    user.value = payload
    if (payload?.role) {
      localStorage.setItem('user_role', payload.role)
    } else {
      localStorage.removeItem('user_role')
    }
  }

  const clearAuth = () => {
    token.value = null
    setUser(null)
    localStorage.removeItem('token')
  }

  const fetchMe = async () => {
    if (!token.value) {
      setUser(null)
      return null
    }
    const response = await api.get('/auth/me')
    setUser(response.data)
    return user.value
  }

  const initialize = async () => {
    if (initialized.value) {
      return
    }
    initialized.value = true
    if (!token.value) {
      return
    }
    try {
      await fetchMe()
    } catch {
      clearAuth()
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    isMerchant,
    isCustomer,
    setToken,
    setUser,
    clearAuth,
    fetchMe,
    initialize
  }
})
