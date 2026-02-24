/**
 * WalletDB — IndexedDB schema via Dexie.js
 *
 * Why Dexie over raw IndexedDB?
 * IndexedDB has a callback-heavy API that is difficult to compose with
 * async/await and TypeScript. Dexie wraps it in Promises, provides a
 * clean Table<T> generic API, and handles schema versioning/migrations.
 *
 * Why a class that extends Dexie?
 * The class pattern gives us typed Table<T> properties that TypeScript
 * understands, plus a single place to manage version migrations as the
 * schema evolves.
 *
 * Schema string syntax: 'primaryKey, index1, index2, ...'
 * - The first entry after the table name is the primary key.
 * - '++' prefix means auto-increment (integers, used for pendingMutations).
 * - Only fields you need to query by need to be listed — Dexie stores the
 *   full object regardless.
 *
 * Version strategy:
 * - Version 1 is the initial schema for Phase 2.
 * - Future phases (e.g., Phase 3 adding conflict tracking) will add version 2
 *   with an upgrade function, leaving existing data intact.
 */

import Dexie, { type Table } from 'dexie'
import type {
  LocalAccount,
  LocalTransaction,
  LocalTransfer,
  LocalCategory,
  PendingMutation
} from './types'

class WalletDB extends Dexie {
  // Typed table references — the '!' tells TypeScript these will be assigned
  // by Dexie's version().stores() call in the constructor, not by us directly.
  accounts!: Table<LocalAccount>
  transactions!: Table<LocalTransaction>
  transfers!: Table<LocalTransfer>
  categories!: Table<LocalCategory>
  pendingMutations!: Table<PendingMutation>

  constructor() {
    super('WalletDB')

    this.version(1).stores({
      // Accounts: filter by type, active flag, and sync status
      accounts: 'id, server_id, tipo, activa, _sync_status',

      // Transactions: the most-queried table — indexed by account (cuenta_id),
      // category, transaction type, date, and sync status
      transactions: 'id, server_id, cuenta_id, categoria_id, tipo, fecha, _sync_status',

      // Transfers: both origin and destination accounts are valid filter keys
      transfers: 'id, server_id, cuenta_origen_id, cuenta_destino_id, fecha, _sync_status',

      // Categories: filtered by tipo (ingreso/gasto/ambos) and parent for
      // hierarchy traversal
      categories: 'id, server_id, tipo, categoria_padre_id, _sync_status',

      // PendingMutations: auto-increment PK ensures FIFO insertion order;
      // queued_at is indexed for explicit ordering queries in Phase 3
      pendingMutations: '++id, entity_type, entity_id, operation, queued_at'
    })
  }
}

/**
 * Singleton database instance.
 *
 * Why a singleton?
 * IndexedDB connections are expensive to open. A single shared instance
 * avoids re-opening the database on every store action and ensures all
 * parts of the app share the same transaction scope when needed.
 *
 * Import this `db` object anywhere you need IndexedDB access:
 *   import { db } from '@/offline'
 */
export const db = new WalletDB()
