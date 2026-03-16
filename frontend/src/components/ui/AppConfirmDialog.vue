<script setup lang="ts">
/**
 * AppConfirmDialog — global async confirmation modal.
 *
 * Why this component exists:
 * `usePostLoginFlow` (and any other composable) calls `uiStore.showConfirm()`
 * which stores a Promise resolver inside `uiStore.confirmDialog`. Without a
 * component that reads that state and calls `resolveConfirm(true/false)`, the
 * Promise never resolves and the post-login flow hangs indefinitely.
 *
 * Design decisions:
 * - Bottom-sheet on mobile (items-end), center on sm+ (sm:items-center).
 *   This matches the logout modal in SettingsView.vue and follows the native
 *   mobile bottom-sheet convention for one-thumb reachability.
 * - Teleport to <body> so the fixed overlay stacks correctly above all
 *   other z-indexed content regardless of where App.vue lives in the DOM.
 * - Transition reuses the same modal-fade keyframes defined locally so this
 *   component is self-contained (no shared CSS dependency).
 * - Two buttons only: confirmLabel and cancelLabel, with sensible defaults.
 *   The caller decides what the labels say — this component is generic.
 * - role="dialog" + aria-modal="true" + aria-labelledby for screen readers.
 * - Focus trap: on mount the confirm button receives focus so keyboard users
 *   can immediately press Enter to confirm, or Tab to reach Cancel.
 *
 * Why NOT use uiStore.activeModal?
 * activeModal is a string-based identifier for named modals (e.g., "editAccount").
 * The confirm dialog is a different pattern: it's async-imperative (returns a
 * Promise) rather than declarative (show this named modal). Mixing them would
 * require the confirm caller to also know the modal ID, coupling store shape
 * to call sites unnecessarily.
 */

import { computed, watch, nextTick, ref } from 'vue'
import { useUiStore } from '@/stores/ui'

const uiStore = useUiStore()

// Derived: is the dialog currently visible?
const isOpen = computed(() => uiStore.confirmDialog !== null)

// Derived: safe accessors with fallback defaults so the template never throws
// on null (even during the leave transition when confirmDialog becomes null
// before the animation finishes).
const title = computed(() => uiStore.confirmDialog?.options.title ?? '')
const message = computed(() => uiStore.confirmDialog?.options.message ?? '')
const confirmLabel = computed(() => uiStore.confirmDialog?.options.confirmLabel ?? 'Confirmar')
const cancelLabel = computed(() => uiStore.confirmDialog?.options.cancelLabel ?? 'Cancelar')

// Ref to the confirm button for focus management
const confirmButtonRef = ref<HTMLButtonElement | null>(null)

// Focus the confirm button whenever the dialog opens.
// Why nextTick? The button is rendered only after isOpen becomes true; we must
// wait for Vue to flush the DOM update before calling .focus().
watch(isOpen, async (opened) => {
  if (opened) {
    await nextTick()
    confirmButtonRef.value?.focus()
  }
})

function handleConfirm(): void {
  uiStore.resolveConfirm(true)
}

function handleCancel(): void {
  uiStore.resolveConfirm(false)
}

// Close on backdrop click — same pattern as SettingsView logout modal.
function handleBackdropClick(): void {
  uiStore.resolveConfirm(false)
}

// Keyboard accessibility: Escape key dismisses the dialog as a cancel action.
function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.preventDefault()
    uiStore.resolveConfirm(false)
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm-modal-fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-end justify-center sm:items-center px-4 pb-6 sm:pb-0"
        style="background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px);"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="isOpen ? 'confirm-dialog-title' : undefined"
        @click.self="handleBackdropClick"
        @keydown="handleKeydown"
      >
        <!--
          Dialog card.

          Why max-w-sm?
          Confirm dialogs are short messages with two buttons. A narrow card
          (max 384px) works on all screens: on mobile it fills the available
          width minus the 1rem horizontal padding; on desktop it stays compact
          and centred rather than stretching uncomfortably wide.
        -->
        <div
          class="w-full max-w-sm rounded-2xl p-6 space-y-5"
          style="background-color: #1e293b; border: 1px solid rgba(51, 65, 85, 0.8);"
        >
          <!-- Title + message -->
          <div class="space-y-2">
            <h2
              id="confirm-dialog-title"
              class="text-lg font-semibold text-dark-text-primary"
            >
              {{ title }}
            </h2>
            <p class="text-sm text-dark-text-secondary leading-relaxed">
              {{ message }}
            </p>
          </div>

          <!-- Action buttons -->
          <div class="space-y-3">
            <!--
              Confirm button.
              Gets initial focus on open so keyboard users can immediately act.
              Accent-blue background signals the primary/positive action.
            -->
            <button
              ref="confirmButtonRef"
              @click="handleConfirm"
              class="w-full flex items-center justify-center px-4 py-3 rounded-xl
                     text-sm font-medium transition-colors min-h-[44px]
                     hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-dark-bg-secondary"
              style="background-color: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #93c5fd;"
            >
              {{ confirmLabel }}
            </button>

            <!--
              Cancel button.
              Placed below confirm so the default/positive action is on top
              and more prominent. Neutral styling conveys "nothing will happen".
            -->
            <button
              @click="handleCancel"
              class="w-full flex items-center justify-center px-4 py-3 rounded-xl
                     text-sm text-dark-text-secondary transition-colors min-h-[44px]
                     hover:text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 focus:ring-offset-dark-bg-secondary"
              style="background-color: rgba(51, 65, 85, 0.3);"
            >
              {{ cancelLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/**
 * Modal overlay fade + subtle scale — identical to SettingsView logout modal.
 *
 * Why opacity + scale together?
 * Fading alone is flat. The scale (0.95 → 1.0) gives the card a "pop"
 * that matches native iOS/Android modal conventions, making the dialog
 * feel intentional rather than abrupt.
 *
 * 250ms enter / 200ms leave:
 * Enter is slightly slower so the user has time to register the dialog.
 * Leave is faster so it doesn't feel sluggish after they've made a choice.
 */
.confirm-modal-fade-enter-active {
  transition: opacity 250ms ease-out, transform 250ms ease-out;
}

.confirm-modal-fade-leave-active {
  transition: opacity 200ms ease-in, transform 200ms ease-in;
}

.confirm-modal-fade-enter-from,
.confirm-modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.confirm-modal-fade-enter-to,
.confirm-modal-fade-leave-from {
  opacity: 1;
  transform: scale(1);
}
</style>
