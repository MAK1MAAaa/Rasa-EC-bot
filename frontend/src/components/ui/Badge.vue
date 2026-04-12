<script setup lang="ts">
import { computed } from 'vue'
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva('ui-badge', {
  variants: {
    variant: {
      default: 'ui-badge-default',
      muted: 'ui-badge-muted',
      success: 'ui-badge-success',
      info: 'ui-badge-info',
      warn: 'ui-badge-warn',
      danger: 'ui-badge-danger'
    }
  },
  defaultVariants: {
    variant: 'default'
  }
})

interface Props {
  variant?: 'default' | 'muted' | 'success' | 'info' | 'warn' | 'danger'
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default'
})

const classes = computed(() => cn(badgeVariants({ variant: props.variant }), props.class))
</script>

<template>
  <span :class="classes">
    <slot />
  </span>
</template>
