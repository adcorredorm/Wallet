<script setup lang="ts">
/**
 * Confirm Dialog Component
 *
 * Why confirm dialogs?
 * - Prevent accidental deletions
 * - Clear action communication
 * - Mobile-friendly button layout
 */

import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

interface Props {
  show: boolean
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning' | 'info'
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Confirmar acción',
  confirmText: 'Confirmar',
  cancelText: 'Cancelar',
  variant: 'danger',
  loading: false
})

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const variantIcons = {
  danger: '⚠️',
  warning: '⚡',
  info: 'ℹ️'
}
</script>

<template>
  <BaseModal
    :show="show"
    :title="title"
    size="sm"
    @close="emit('cancel')"
  >
    <!-- Message -->
    <div class="flex gap-3">
      <span class="text-3xl flex-shrink-0">
        {{ variantIcons[variant] }}
      </span>
      <p class="text-dark-text-secondary">
        {{ message }}
      </p>
    </div>

    <!-- Actions -->
    <template #footer>
      <div class="flex gap-3 flex-col md:flex-row-reverse">
        <BaseButton
          :variant="variant"
          :loading="loading"
          full-width
          @click="emit('confirm')"
        >
          {{ confirmText }}
        </BaseButton>
        <BaseButton
          variant="ghost"
          :disabled="loading"
          full-width
          @click="emit('cancel')"
        >
          {{ cancelText }}
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
