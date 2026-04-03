import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface CartItem {
  id: string
  product_id: string
  product_name: string
  product_image_url?: string
  unit_price: number
  quantity: number
  subtotal: number
}

interface CartPayload {
  items: CartItem[]
  total_items: number
  total_amount: number
}

export const useCartStore = defineStore('cart', () => {
  const items = ref<CartItem[]>([])
  const totalItems = ref(0)
  const totalAmount = ref(0)

  const applyPayload = (payload: CartPayload) => {
    items.value = payload.items
    totalItems.value = payload.total_items
    totalAmount.value = payload.total_amount
  }

  const clear = () => {
    items.value = []
    totalItems.value = 0
    totalAmount.value = 0
  }

  const refreshCart = async () => {
    const response = await api.get('/cart')
    applyPayload(response.data)
  }

  const addToCart = async (productId: string, quantity = 1) => {
    const response = await api.post('/cart/items', {
      product_id: productId,
      quantity
    })
    applyPayload(response.data)
  }

  const updateItem = async (itemId: string, quantity: number) => {
    const response = await api.patch(`/cart/items/${itemId}`, { quantity })
    applyPayload(response.data)
  }

  const removeItem = async (itemId: string) => {
    const response = await api.delete(`/cart/items/${itemId}`)
    applyPayload(response.data)
  }

  return {
    items,
    totalItems,
    totalAmount,
    clear,
    refreshCart,
    addToCart,
    updateItem,
    removeItem
  }
})
