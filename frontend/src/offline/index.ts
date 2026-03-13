/**
 * Offline module barrel export
 *
 * Why a barrel file?
 * Consumers (stores, composables, etc.) import from '@/offline' rather than
 * from deep internal paths like '@/offline/db'. This decouples the public
 * interface from the internal folder structure. If we ever split db.ts or
 * rename temp-id.ts, only this file needs to change.
 *
 * Usage examples:
 *   import { db } from '@/offline'
 *   import { generateTempId, isTempId } from '@/offline'
 *   import type { LocalAccount, PendingMutation } from '@/offline'
 */

export { db } from './db'
export { generateTempId, isTempId } from './temp-id'
export { fetchAllWithRevalidation, fetchByIdWithRevalidation } from './repository'
export { mutationQueue, MutationQueue } from './mutation-queue'
export { syncManager, SyncManager } from './sync-manager'
export type {
  LocalAccount,
  LocalTransaction,
  LocalTransfer,
  LocalCategory,
  PendingMutation,
  SyncStatus,
  LocalExchangeRate,
  LocalSetting,
  LocalDashboard,
  LocalDashboardWidget
} from './types'
