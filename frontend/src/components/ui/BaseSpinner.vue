<script setup lang="ts">
/**
 * Base Spinner Component
 *
 * Simple loading spinner for async operations
 */

interface Props {
  size?: 'sm' | 'md' | 'lg'
  centered?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  centered: false
})

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12'
}
</script>

<template>
  <div :class="{ 'flex items-center justify-center min-h-[200px]': centered }">
    <div :class="['spinner', sizeClasses[size]]"></div>
  </div>
</template>
