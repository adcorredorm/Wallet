<script setup lang="ts">
/**
 * Base Toast Component
 *
 * Why toasts?
 * - Non-intrusive feedback for user actions
 * - Auto-dismiss after timeout
 * - Multiple toasts stacked
 *
 * Mobile considerations:
 * - Positioned at top on mobile (easier to see)
 * - Touch-friendly close button
 * - Swipe to dismiss (future enhancement)
 */

import { computed } from 'vue'
import { useUiStore } from '@/stores'

const uiStore = useUiStore()

const toasts = computed(() => uiStore.toasts)

const typeIcons = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ'
}

const typeClasses = {
  success: 'bg-accent-green/90 text-white',
  error: 'bg-accent-red/90 text-white',
  warning: 'bg-accent-amber/90 text-dark-bg-primary',
  info: 'bg-accent-blue/90 text-white'
}
</script>

<template>
  <!-- Toast container -->
  <div class="fixed top-4 right-4 left-4 md:left-auto md:w-96 z-50 space-y-2 pointer-events-none">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="[
          'flex items-start gap-3 p-4 rounded-lg shadow-lg backdrop-blur-sm',
          'pointer-events-auto',
          typeClasses[toast.type]
        ]"
      >
        <!-- Icon -->
        <span class="text-xl flex-shrink-0">
          {{ typeIcons[toast.type] }}
        </span>

        <!-- Message -->
        <p class="flex-1 text-sm font-medium">
          {{ toast.message }}
        </p>

        <!-- Close button -->
        <button
          class="flex-shrink-0 p-1 hover:bg-white/20 rounded transition-colors"
          @click="uiStore.removeToast(toast.id)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
/* Toast slide-in animation */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>
