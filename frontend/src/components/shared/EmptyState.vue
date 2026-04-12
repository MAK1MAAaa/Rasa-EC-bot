<script setup lang="ts">
defineProps<{
  eyebrow?: string
  title: string
  description?: string
  compact?: boolean
}>()
</script>

<template>
  <div class="empty-state-shell" :class="{ compact }">
    <p v-if="eyebrow" class="empty-state-eyebrow">{{ eyebrow }}</p>
    <h3 class="empty-state-title">{{ title }}</h3>
    <p v-if="description" class="empty-state-description">{{ description }}</p>
    <div v-if="$slots.default" class="empty-state-actions">
      <slot />
    </div>
  </div>
</template>
