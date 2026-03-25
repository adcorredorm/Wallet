<script setup lang="ts">
/**
 * Base Card Component
 *
 * Why cards?
 * - Visual grouping of related content
 * - Touch-friendly clickable areas
 * - Consistent spacing and styling
 *
 * Mobile considerations:
 * - Adequate padding for readability
 * - Optional clickable variant with hover effect
 * - Dark mode optimized background
 */

interface Props {
  clickable?: boolean
  bordered?: boolean
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

withDefaults(defineProps<Props>(), {
  clickable: false,
  bordered: false,
  padding: 'md'
})

const emit = defineEmits<{
  click: []
}>()

const paddingClasses = {
  none: '',
  sm: 'p-2',
  md: 'p-4',
  lg: 'p-6'
}
</script>

<template>
  <div
    :class="[
      'card',
      paddingClasses[padding],
      {
        'card-bordered': bordered,
        'cursor-pointer hover:bg-dark-bg-tertiary transition-colors': clickable,
        'active:scale-[0.98] transition-transform': clickable
      }
    ]"
    @click="clickable && emit('click')"
  >
    <slot />
  </div>
</template>
