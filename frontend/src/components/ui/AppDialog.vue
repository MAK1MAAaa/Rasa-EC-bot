<script setup lang="ts">
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'

withDefaults(
  defineProps<{
    open: boolean
    title?: string
    description?: string
    widthClass?: string
  }>(),
  {
    title: '',
    description: '',
    widthClass: 'max-w-xl'
  }
)

const emit = defineEmits<{
  (e: 'close'): void
}>()
</script>

<template>
  <TransitionRoot :show="open" as="template">
    <Dialog class="dialog-root" @close="emit('close')">
      <TransitionChild
        as="template"
        enter="ease-out duration-200"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in duration-150"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="dialog-backdrop" />
      </TransitionChild>

      <div class="dialog-frame">
        <TransitionChild
          as="template"
          enter="ease-out duration-200"
          enter-from="opacity-0 translate-y-3 sm:translate-y-0 sm:scale-95"
          enter-to="opacity-100 translate-y-0 sm:scale-100"
          leave="ease-in duration-150"
          leave-from="opacity-100 translate-y-0 sm:scale-100"
          leave-to="opacity-0 translate-y-3 sm:translate-y-0 sm:scale-95"
        >
          <DialogPanel class="dialog-panel" :class="widthClass">
            <div v-if="title || description" class="dialog-head">
              <DialogTitle v-if="title" class="dialog-title">{{ title }}</DialogTitle>
              <p v-if="description" class="dialog-description">{{ description }}</p>
            </div>
            <slot />
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
