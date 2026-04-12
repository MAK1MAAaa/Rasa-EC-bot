<script setup lang="ts">
defineProps<{
  eyebrow?: string
  title: string
  description?: string
  accent?: 'gold' | 'teal' | 'rose' | 'ink'
}>()
</script>

<template>
  <header class="page-hero" :data-accent="accent || 'gold'">
    <div class="page-hero-copy">
      <p v-if="eyebrow" class="page-hero-eyebrow">{{ eyebrow }}</p>
      <h1 class="page-hero-title">{{ title }}</h1>
      <p v-if="description" class="page-hero-description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-hero-actions">
      <slot name="actions" />
    </div>
  </header>
</template>
