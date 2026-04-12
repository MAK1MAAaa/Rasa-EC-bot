<script setup lang="ts">
import Button from '@/components/ui/Button.vue'

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
    <Button variant="outline" size="sm" :disabled="page <= 1" @click="changePage(page - 1)">上一页</Button>
    <div class="pager-center">
      <strong>{{ page }} / {{ totalPages }}</strong>
      <span v-if="typeof totalItems === 'number'">共 {{ totalItems }} 条</span>
    </div>
    <Button variant="outline" size="sm" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</Button>
  </div>
</template>

<style scoped>
.pager {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 6px;
}

.pager-center {
  min-width: 136px;
  display: grid;
  justify-items: center;
  gap: 2px;
  color: var(--text-muted);
  font-size: 12px;
}

.pager-center strong {
  color: var(--text);
  font-size: 14px;
}
</style>
