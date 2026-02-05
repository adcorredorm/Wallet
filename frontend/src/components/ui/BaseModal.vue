<script setup lang="ts">
/**
 * Base Modal Component
 *
 * Why modals?
 * - Focus user attention on specific action
 * - Prevent accidental navigation away
 * - Confirmation dialogs
 *
 * Mobile considerations:
 * - Full-screen on mobile for better UX
 * - Slide-up animation (native-like)
 * - Backdrop prevents body scrolling
 */

import { watch, onMounted, onUnmounted } from 'vue'

interface Props {
  show: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'full'
  closeOnBackdrop?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  closeOnBackdrop: true
})

const emit = defineEmits<{
  close: []
}>()

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-2xl',
  full: 'max-w-full m-0 h-full rounded-none'
}

// Prevent body scroll when modal is open
watch(() => props.show, (isOpen) => {
  if (isOpen) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

// Handle ESC key
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.show) {
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})

function handleBackdropClick() {
  if (props.closeOnBackdrop) {
    emit('close')
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="show"
        class="fixed inset-0 z-50 overflow-y-auto"
        @click.self="handleBackdropClick"
      >
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/70 backdrop-blur-sm"></div>

        <!-- Modal container -->
        <div class="relative min-h-screen flex items-end md:items-center justify-center p-0 md:p-4">
          <!-- Modal content -->
          <div
            :class="[
              'relative w-full bg-dark-bg-secondary',
              'rounded-t-2xl md:rounded-2xl shadow-xl',
              'max-h-[90vh] flex flex-col',
              sizeClasses[size]
            ]"
            @click.stop
          >
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-dark-border">
              <h3 class="text-lg font-semibold">
                {{ title }}
              </h3>
              <button
                class="p-2 hover:bg-dark-bg-tertiary rounded-lg transition-colors"
                @click="emit('close')"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Body (scrollable) -->
            <div class="flex-1 overflow-y-auto p-4">
              <slot />
            </div>

            <!-- Footer (optional) -->
            <div v-if="$slots.footer" class="p-4 border-t border-dark-border">
              <slot name="footer" />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* Modal slide-up animation for mobile */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active .relative,
.modal-leave-active .relative {
  transition: transform 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .relative {
  transform: translateY(100%);
}

.modal-leave-to .relative {
  transform: translateY(100%);
}

@media (min-width: 768px) {
  .modal-enter-from .relative,
  .modal-leave-to .relative {
    transform: translateY(0) scale(0.95);
  }
}
</style>
