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
// Phase 3.2: exchange rates cache + conversion helpers
export { useExchangeRatesStore } from './exchangeRates'
// Recurring transactions
export { useRecurringRulesStore } from './recurringRules'
// Budgets
export { useBudgetsStore } from './budgets'
