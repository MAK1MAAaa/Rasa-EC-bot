<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const cartStore = useCartStore()
const loading = ref(false)

const loadCart = async () => {
  loading.value = true
  try {
    await cartStore.refreshCart()
  } finally {
    loading.value = false
  }
}

const increase = async (itemId: string, quantity: number) => {
  try {
    await cartStore.updateItem(itemId, quantity + 1)
  } catch (err: any) {
    alert(err.response?.data?.detail || '更新数量失败')
  }
}

const decrease = async (itemId: string, quantity: number) => {
  try {
    await cartStore.updateItem(itemId, Math.max(0, quantity - 1))
  } catch (err: any) {
    alert(err.response?.data?.detail || '更新数量失败')
  }
}

const remove = async (itemId: string) => {
  try {
    await cartStore.removeItem(itemId)
  } catch (err: any) {
    alert(err.response?.data?.detail || '移除商品失败')
  }
}

onMounted(loadCart)
</script>

<template>
  <section class="cart-page">
    <div class="header-row">
      <h1>购物车</h1>
      <button type="button" class="ghost" @click="router.push('/products')">继续逛逛</button>
    </div>

    <div v-if="loading" class="state-card">正在加载购物车...</div>

    <div v-else-if="cartStore.items.length === 0" class="state-card">
      购物车还是空的，快去挑选心仪商品。
    </div>

    <div v-else class="cart-layout">
      <div class="item-list">
        <article v-for="item in cartStore.items" :key="item.id" class="item-card">
          <img :src="item.product_image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=400&q=80'" :alt="item.product_name">
          <div class="item-main">
            <h3>{{ item.product_name }}</h3>
            <p>单价 ¥ {{ item.unit_price.toFixed(2) }}</p>
          </div>
          <div class="qty-box">
            <button @click="decrease(item.id, item.quantity)">-</button>
            <span>{{ item.quantity }}</span>
            <button @click="increase(item.id, item.quantity)">+</button>
          </div>
          <div class="right-col">
            <strong>¥ {{ item.subtotal.toFixed(2) }}</strong>
            <button class="text-btn" @click="remove(item.id)">移除</button>
          </div>
        </article>
      </div>

      <aside class="summary-card">
        <h2>订单汇总</h2>
        <div class="sum-row"><span>商品件数</span><span>{{ cartStore.totalItems }}</span></div>
        <div class="sum-row total"><span>合计</span><span>¥ {{ cartStore.totalAmount.toFixed(2) }}</span></div>
        <button type="button" @click="router.push('/checkout')">去结算</button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.cart-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 18px 38px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.header-row h1 {
  margin: 0;
  color: #16395f;
}

.ghost {
  border: 1px solid #bdd3e8;
  background: #eff6fd;
  color: #1c4a76;
  border-radius: 10px;
  padding: 8px 12px;
}

.state-card {
  background: #fff;
  border: 1px dashed #bfd2e6;
  border-radius: 16px;
  padding: 28px;
  text-align: center;
  color: #5c738c;
}

.cart-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
}

.item-list {
  display: grid;
  gap: 12px;
}

.item-card {
  background: #fff;
  border: 1px solid #d8e5f1;
  border-radius: 14px;
  padding: 12px;
  display: grid;
  gap: 12px;
  grid-template-columns: 96px 1fr auto auto;
  align-items: center;
}

.item-card img {
  width: 96px;
  height: 80px;
  object-fit: cover;
  border-radius: 10px;
}

.item-main h3 {
  margin: 0;
  color: #17395f;
}

.item-main p {
  margin: 6px 0 0;
  color: #60748d;
}

.qty-box {
  display: inline-flex;
  align-items: center;
  border: 1px solid #c5d8ee;
  border-radius: 10px;
  overflow: hidden;
}

.qty-box button {
  border: none;
  width: 30px;
  height: 30px;
  background: #f0f7ff;
  color: #194874;
}

.qty-box span {
  min-width: 34px;
  text-align: center;
}

.right-col {
  display: grid;
  justify-items: end;
  gap: 6px;
}

.right-col strong {
  color: #0b5aa6;
}

.text-btn {
  border: none;
  background: transparent;
  color: #dc2626;
  cursor: pointer;
}

.summary-card {
  background: #fff;
  border: 1px solid #d8e5f1;
  border-radius: 14px;
  padding: 16px;
  height: fit-content;
}

.summary-card h2 {
  margin: 0 0 14px;
  color: #16395f;
  font-size: 18px;
}

.sum-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #4c6178;
}

.sum-row.total {
  font-size: 18px;
  font-weight: 700;
  color: #0b5aa6;
  border-top: 1px dashed #c6d8eb;
  padding-top: 10px;
}

.summary-card button {
  width: 100%;
  margin-top: 12px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #0b5aa6, #0f766e);
  color: white;
  padding: 11px;
  font-weight: 600;
}

@media (max-width: 900px) {
  .cart-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .item-card {
    grid-template-columns: 96px 1fr;
  }

  .qty-box,
  .right-col {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
