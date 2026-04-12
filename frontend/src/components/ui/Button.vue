<script setup lang="ts">
import { computed } from 'vue'
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva('ui-button', {
  variants: {
    variant: {
      default: 'ui-button-default',
      secondary: 'ui-button-secondary',
      ghost: 'ui-button-ghost',
      outline: 'ui-button-outline',
      danger: 'ui-button-danger'
    },
    size: {
      sm: 'ui-button-sm',
      md: 'ui-button-md',
      lg: 'ui-button-lg',
      icon: 'ui-button-icon'
    },
    block: {
      true: 'ui-button-block',
      false: ''
    }
  },
  defaultVariants: {
    variant: 'default',
    size: 'md',
    block: false
  }
})

interface Props {
  variant?: 'default' | 'secondary' | 'ghost' | 'outline' | 'danger'
  size?: 'sm' | 'md' | 'lg' | 'icon'
  block?: boolean
  as?: 'button' | 'a' | 'span'
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
  href?: string
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  as: 'button',
  type: 'button',
  variant: 'default',
  size: 'md',
  block: false
})

const tag = computed(() => (props.href ? 'a' : props.as))
const classes = computed(() =>
  cn(
    buttonVariants({
      variant: props.variant,
      size: props.size,
      block: props.block
    }),
    props.class
  )
)
</script>

<template>
  <component
    :is="tag"
    :class="classes"
    :type="tag === 'button' ? type : undefined"
    :disabled="tag === 'button' ? disabled : undefined"
    :href="href"
  >
    <slot />
  </component>
</template>
