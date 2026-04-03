import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '@/api/client'

interface AuthUser {
  id: string
  username: string
  email: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token'))
  const user = ref<AuthUser | null>(null)
  const initialized = ref(false)

  const isLoggedIn = computed(() => Boolean(token.value))

  const setToken = (value: string) => {
    token.value = value
    localStorage.setItem('token', value)
  }

  const clearAuth = () => {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  const fetchMe = async () => {
    if (!token.value) {
      user.value = null
      return null
    }
    const response = await api.get('/auth/me')
    user.value = response.data
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
    setToken,
    clearAuth,
    fetchMe,
    initialize
  }
})
