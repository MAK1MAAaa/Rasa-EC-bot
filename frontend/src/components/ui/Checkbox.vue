<script setup lang="ts">
import { computed } from 'vue'
import { Check } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

interface Props {
  modelValue?: boolean
  disabled?: boolean
  class?: string
  id?: string
  name?: string
  value?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  disabled: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const classes = computed(() =>
  cn('ui-checkbox-root', props.class, {
    'is-disabled': props.disabled,
    'is-checked': props.modelValue
  })
)

const handleChange = (event: Event) => {
  emit('update:modelValue', (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <label :class="classes">
    <input
      :id="id"
      :name="name"
      :value="value"
      class="ui-checkbox-input"
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      @change="handleChange"
    >
    <span class="ui-checkbox-box" aria-hidden="true">
      <Check :size="14" :stroke-width="3" />
    </span>
    <span v-if="$slots.default" class="ui-checkbox-label">
      <slot />
    </span>
  </label>
</template>

<style scoped>
.ui-checkbox-root {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  cursor: pointer;
  user-select: none;
  color: var(--text-muted);
}

.ui-checkbox-root.is-disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.ui-checkbox-input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.ui-checkbox-box {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  border-radius: 8px;
  border: 1px solid rgba(113, 86, 50, 0.22);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 240, 230, 0.94));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.8),
    0 10px 20px rgba(39, 27, 12, 0.06);
  color: transparent;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.ui-checkbox-root:hover .ui-checkbox-box {
  border-color: rgba(178, 122, 50, 0.34);
  transform: translateY(-1px);
}

.ui-checkbox-root.is-checked .ui-checkbox-box {
  border-color: rgba(178, 122, 50, 0.52);
  background:
    linear-gradient(180deg, rgba(188, 131, 58, 0.96), rgba(132, 86, 32, 0.96));
  box-shadow:
    inset 0 1px 0 rgba(255, 245, 225, 0.35),
    0 12px 26px rgba(178, 122, 50, 0.2);
  color: #fff8ee;
}

.ui-checkbox-label {
  min-width: 0;
  font-size: 14px;
  line-height: 1.5;
}
</style>
