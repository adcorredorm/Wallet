/**
 * UI Store
 *
 * Manages global UI state:
 * - Toast notifications
 * - Loading states
 * - Modals
 * - Drawer navigation state (renamed from mobile menu for clarity)
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ConfirmDialogOptions {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
}

interface ConfirmDialogState {
  options: ConfirmDialogOptions
  resolve: (value: boolean) => void
}

export interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration?: number
}

export const useUiStore = defineStore('ui', () => {
  // State
  const toasts = ref<Toast[]>([])
  const isDrawerOpen = ref(false)
  const activeModal = ref<string | null>(null)
  const globalLoading = ref(false)
  const confirmDialog = ref<ConfirmDialogState | null>(null)

  // Toast management
  function showToast(message: string, type: Toast['type'] = 'info', duration = 3000) {
    const id = Date.now().toString()
    const toast: Toast = { id, message, type, duration }
    toasts.value.push(toast)

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }

  function removeToast(id: string) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  function clearToasts() {
    toasts.value = []
  }

  // Convenience methods for different toast types
  function showSuccess(message: string, duration?: number) {
    return showToast(message, 'success', duration)
  }

  function showError(message: string, duration?: number) {
    return showToast(message, 'error', duration)
  }

  function showWarning(message: string, duration?: number) {
    return showToast(message, 'warning', duration)
  }

  function showInfo(message: string, duration?: number) {
    return showToast(message, 'info', duration)
  }

  // Drawer menu (renamed from mobile menu for semantic clarity)
  function toggleDrawer() {
    isDrawerOpen.value = !isDrawerOpen.value
  }

  function closeDrawer() {
    isDrawerOpen.value = false
  }

  function openDrawer() {
    isDrawerOpen.value = true
  }

  // Modal management
  function openModal(modalId: string) {
    activeModal.value = modalId
  }

  function closeModal() {
    activeModal.value = null
  }

  // Global loading
  function setGlobalLoading(isLoading: boolean) {
    globalLoading.value = isLoading
  }

  // Async confirm dialog — resolves true (confirm) or false (cancel)
  function showConfirm(options: ConfirmDialogOptions): Promise<boolean> {
    return new Promise((resolve) => {
      confirmDialog.value = { options, resolve }
    })
  }

  function resolveConfirm(value: boolean): void {
    if (confirmDialog.value) {
      confirmDialog.value.resolve(value)
      confirmDialog.value = null
    }
  }

  return {
    // State
    toasts,
    isDrawerOpen,
    activeModal,
    globalLoading,
    confirmDialog,
    // Actions
    showToast,
    removeToast,
    clearToasts,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    toggleDrawer,
    closeDrawer,
    openDrawer,
    openModal,
    closeModal,
    setGlobalLoading,
    showConfirm,
    resolveConfirm,
  }
})
