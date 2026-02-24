/**
 * Pinia Stores Index
 * Central export for all application stores
 */

export { useAccountsStore } from './accounts'
export { useCategoriesStore } from './categories'
export { useTransactionsStore } from './transactions'
export { useTransfersStore } from './transfers'
export { useUiStore } from './ui'
// Phase 5: sync state store (connectivity + queue status for UI visibility)
export { useSyncStore } from './sync'
export type { SyncError } from './sync'
