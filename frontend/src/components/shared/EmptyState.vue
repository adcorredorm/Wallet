<script setup lang="ts">
/**
 * Empty State Component
 *
 * Why empty states?
 * - Prevent confusion when no data
 * - Guide user to create first item
 * - Better UX than blank screen
 */

interface Props {
  title?: string
  message?: string
  actionText?: string
  icon?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'No hay datos',
  message: 'Comienza creando tu primer elemento',
  actionText: 'Crear',
  icon: '📭'
})

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12 px-4 text-center">
    <!-- Icon -->
    <div class="text-6xl mb-4">
      {{ icon }}
    </div>

    <!-- Title -->
    <h3 class="text-lg font-semibold mb-2">
      {{ title }}
    </h3>

    <!-- Message -->
    <p class="text-dark-text-secondary mb-6 max-w-sm">
      {{ message }}
    </p>

    <!-- Action button -->
    <slot name="action">
      <button
        v-if="actionText"
        class="btn-primary"
        @click="emit('action')"
      >
        {{ actionText }}
      </button>
    </slot>
  </div>
</template>
