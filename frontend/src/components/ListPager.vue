<script setup lang="ts">
const props = defineProps<{
  page: number
  totalPages: number
  totalItems?: number
}>()

const emit = defineEmits<{
  (e: 'change', page: number): void
}>()

const changePage = (nextPage: number) => {
  if (nextPage < 1 || nextPage > props.totalPages || nextPage === props.page) {
    return
  }
  emit('change', nextPage)
}
</script>

<template>
  <div v-if="totalPages > 1" class="pager">
    <button type="button" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
    <span>
      {{ page }} / {{ totalPages }}
      <template v-if="typeof totalItems === 'number'"> · 共 {{ totalItems }} 条</template>
    </span>
    <button type="button" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
  </div>
</template>

<style scoped>
.pager {
  margin-top: 18px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14px;
}

.pager button {
  border: none;
  background: #2f2413;
  color: #fff5e8;
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
}

.pager button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pager span {
  color: #6c6253;
  font-size: 13px;
}
</style>
