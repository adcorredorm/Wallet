<script setup lang="ts">
/**
 * Base Button Component
 *
 * Why a base button?
 * - Consistent styling across the app
 * - Touch-friendly sizing (min 44px height)
 * - Variants for different use cases
 * - Loading state built-in
 *
 * Mobile considerations:
 * - Large enough for thumb tapping
 * - Visual feedback on active state
 * - Disabled state clearly visible
 */

interface Props {
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  fullWidth?: boolean
  type?: 'button' | 'submit' | 'reset'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  loading: false,
  disabled: false,
  fullWidth: false,
  type: 'button'
})

const sizeClasses = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg'
}
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[
      `btn-${variant}`,
      sizeClasses[size],
      { 'w-full': fullWidth, 'opacity-50 cursor-not-allowed': loading }
    ]"
  >
    <!-- Loading spinner -->
    <span v-if="loading" class="spinner w-4 h-4 mr-2"></span>

    <!-- Button content -->
    <slot />
  </button>
</template>
