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
 * - Version 2 renames Spanish field names to English to match the new backend API.
 * - Version 3 adds exchangeRates and settings tables for multi-currency support.
 * - Version 4 introduces base_rate on transactions/transfers; clears all tables
 *   (test data only) so no records exist without base_rate.
 * - Version 5 adds dashboards and dashboardWidgets tables for the customizable
 *   analytics dashboard feature (Fase B). New tables start empty — no upgrade needed.
 * - Version 6 adds active index to categories for archive/hard-delete filtering.
 * - Version 7 adds sort_order index to accounts and icon field.
 *   Upgrade migration assigns sequential sort_order (by created_at) and
 *   a type-based default icon to existing records.
 * - Version 8 adds recurringRules and pendingOccurrences tables for the
 *   Recurring Transactions feature. New tables start empty — no upgrade needed.
 * - Version 9 adds fee_for_transaction_id and fee_for_transfer_id as indexed fields
 *   on the transactions table for fast parent→fee lookups. No upgrade needed.
 */

import Dexie, { type Table } from 'dexie'
import type {
  LocalAccount,
  LocalTransaction,
  LocalTransfer,
  LocalCategory,
  PendingMutation,
  LocalExchangeRate,
  LocalSetting,
  LocalDashboard,
  LocalDashboardWidget,
  LocalRecurringRule,
  LocalPendingOccurrence,
  LocalBudget
} from './types'

class WalletDB extends Dexie {
  // Typed table references — the '!' tells TypeScript these will be assigned
  // by Dexie's version().stores() call in the constructor, not by us directly.
  accounts!: Table<LocalAccount>
  transactions!: Table<LocalTransaction>
  transfers!: Table<LocalTransfer>
  categories!: Table<LocalCategory>
  pendingMutations!: Table<PendingMutation>
  exchangeRates!: Table<LocalExchangeRate>
  settings!: Table<LocalSetting>
  dashboards!: Table<LocalDashboard>
  dashboardWidgets!: Table<LocalDashboardWidget>
  recurringRules!: Table<LocalRecurringRule>
  pendingOccurrences!: Table<LocalPendingOccurrence>
  budgets!: Table<LocalBudget>

  constructor() {
    super('WalletDB')

    this.version(1).stores({
      // Version 1 schema (Spanish field names — kept for migration path)
      accounts: 'id, server_id, tipo, activa, _sync_status',
      transactions: 'id, server_id, cuenta_id, categoria_id, tipo, fecha, _sync_status',
      transfers: 'id, server_id, cuenta_origen_id, cuenta_destino_id, fecha, _sync_status',
      categories: 'id, server_id, tipo, categoria_padre_id, _sync_status',
      pendingMutations: '++id, entity_type, entity_id, operation, queued_at'
    })

    this.version(2).stores({
      // Accounts: filter by type, active flag, and sync status
      accounts: 'id, server_id, type, active, _sync_status',

      // Transactions: the most-queried table — indexed by account (account_id),
      // category, transaction type, date, and sync status
      transactions: 'id, server_id, account_id, category_id, type, date, _sync_status',

      // Transfers: both origin and destination accounts are valid filter keys
      transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',

      // Categories: filtered by type (income/expense/both) and parent for
      // hierarchy traversal
      categories: 'id, server_id, type, parent_category_id, _sync_status',

      // PendingMutations: auto-increment PK ensures FIFO insertion order;
      // queued_at is indexed for explicit ordering queries in Phase 3
      pendingMutations: '++id, entity_type, entity_id, operation, queued_at'
    })

    this.version(3).stores({
      // All existing tables are carried forward unchanged so Dexie does not
      // drop them during the upgrade.
      accounts: 'id, server_id, type, active, _sync_status',
      transactions: 'id, server_id, account_id, category_id, type, date, _sync_status',
      transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',
      categories: 'id, server_id, type, parent_category_id, _sync_status',
      pendingMutations: '++id, entity_type, entity_id, operation, queued_at',

      // New in v3 — multi-currency support.
      // exchangeRates: PK is the ISO 4217 code (or crypto ticker). No
      // auto-increment because we always upsert by currency code.
      exchangeRates: 'currency_code',

      // settings: PK is a string key (e.g. 'primary_currency'). Indexed by
      // _sync_status so the sync engine can query only dirty settings.
      settings: 'key, _sync_status'
    })

    this.version(4)
      .stores({
        // Schema strings are identical to v3 — base_rate is not indexed.
        // Dexie stores the full object regardless of what is listed here;
        // only fields that need to be queried by must appear in the string.
        accounts: 'id, server_id, type, active, _sync_status',
        transactions: 'id, server_id, account_id, category_id, type, date, _sync_status',
        transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',
        categories: 'id, server_id, type, parent_category_id, _sync_status',
        pendingMutations: '++id, entity_type, entity_id, operation, queued_at',
        exchangeRates: 'currency_code',
        settings: 'key, _sync_status'
      })
      .upgrade(async (tx) => {
        // Migration note: v4 introduces base_rate on transactions and transfers.
        // Current data is test data only — clear all tables for a clean slate
        // so no records exist without base_rate, which would produce incorrect
        // historical net worth calculations in the chart composable.
        await Promise.all([
          tx.table('accounts').clear(),
          tx.table('transactions').clear(),
          tx.table('transfers').clear(),
          tx.table('categories').clear(),
          tx.table('pendingMutations').clear(),
          tx.table('exchangeRates').clear(),
          tx.table('settings').clear()
        ])
      })

    this.version(5).stores({
      // All existing tables carried forward
      accounts: 'id, server_id, type, active, _sync_status',
      transactions: 'id, server_id, account_id, category_id, type, date, _sync_status',
      transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',
      categories: 'id, server_id, type, parent_category_id, _sync_status',
      pendingMutations: '++id, entity_type, entity_id, operation, queued_at',
      exchangeRates: 'currency_code',
      settings: 'key, _sync_status',
      // New in v5 — dashboard configuration cache
      dashboards: 'id, server_id, is_default, sort_order, _sync_status',
      dashboardWidgets: 'id, server_id, dashboard_id, _sync_status'
    })
    // No upgrade() needed — new tables start empty

    this.version(6)
      .stores({
        accounts: 'id, server_id, type, active, _sync_status',
        transactions: 'id, server_id, account_id, category_id, type, date, _sync_status',
        transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',
        // New in v6 — index categories.active for archive/hard-delete filtering
        categories: 'id, server_id, type, active, parent_category_id, _sync_status',
        pendingMutations: '++id, entity_type, entity_id, operation, queued_at',
        exchangeRates: 'currency_code',
        settings: 'key, _sync_status',
        dashboards: 'id, server_id, is_default, sort_order, _sync_status',
        dashboardWidgets: 'id, server_id, dashboard_id, _sync_status'
      })
      .upgrade(tx => {
        return tx.table('categories').toCollection().modify((cat: Record<string, unknown>) => {
          if (cat['active'] === undefined) {
            cat['active'] = true
          }
        })
      })

    this.version(7)
      .stores({
        // Add sort_order index to accounts so queries can order by it
        accounts: 'id, server_id, type, active, sort_order, _sync_status',
        transactions: 'id, server_id, account_id, category_id, type, date, _sync_status',
        transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',
        categories: 'id, server_id, type, active, parent_category_id, _sync_status',
        pendingMutations: '++id, entity_type, entity_id, operation, queued_at',
        exchangeRates: 'currency_code',
        settings: 'key, _sync_status',
        dashboards: 'id, server_id, is_default, sort_order, _sync_status',
        dashboardWidgets: 'id, server_id, dashboard_id, _sync_status'
      })
      .upgrade(async (tx) => {
        // Backfill: assign sequential sort_order ordered by created_at,
        // and a default icon by account type — matching backend migration logic.
        const accounts = await tx.table('accounts').toArray()
        accounts.sort((a: any, b: any) => (a.created_at || '').localeCompare(b.created_at || ''))
        for (let i = 0; i < accounts.length; i++) {
          const icon = accounts[i].type === 'cash' ? '💵' : '💳'
          await tx.table('accounts').update(accounts[i].id, {
            sort_order: i,
            icon
          })
        }
      })

    this.version(8).stores({
      // Carry forward all v7 tables unchanged
      accounts: 'id, server_id, type, active, sort_order, _sync_status',
      transactions: 'id, server_id, account_id, category_id, type, date, _sync_status',
      transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',
      categories: 'id, server_id, type, active, parent_category_id, _sync_status',
      pendingMutations: '++id, entity_type, entity_id, operation, queued_at',
      exchangeRates: 'currency_code',
      settings: 'key, _sync_status',
      dashboards: 'id, server_id, is_default, sort_order, _sync_status',
      dashboardWidgets: 'id, server_id, dashboard_id, _sync_status',
      // New in v8 — recurring transactions
      recurringRules: 'id, server_id, account_id, category_id, status, next_occurrence_date, _sync_status',
      pendingOccurrences: 'id, recurring_rule_id, status, due_date',
    })
    // No upgrade() needed — new tables start empty

    this.version(9).stores({
      // Carry forward all v8 tables unchanged
      accounts: 'id, server_id, type, active, sort_order, _sync_status',
      // New in v9: fee_for_transaction_id and fee_for_transfer_id indexed for parent→fee lookups
      transactions: 'id, server_id, account_id, category_id, type, date, _sync_status, fee_for_transaction_id, fee_for_transfer_id',
      transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',
      categories: 'id, server_id, type, active, parent_category_id, _sync_status',
      pendingMutations: '++id, entity_type, entity_id, operation, queued_at',
      exchangeRates: 'currency_code',
      settings: 'key, _sync_status',
      dashboards: 'id, server_id, is_default, sort_order, _sync_status',
      dashboardWidgets: 'id, server_id, dashboard_id, _sync_status',
      recurringRules: 'id, server_id, account_id, category_id, status, next_occurrence_date, _sync_status',
      pendingOccurrences: 'id, recurring_rule_id, status, due_date',
    })
    // No upgrade() needed — Dexie adds new indexes to existing data automatically

    this.version(10).stores({
      accounts: 'id, server_id, type, active, sort_order, _sync_status',
      transactions: 'id, server_id, account_id, category_id, type, date, _sync_status, fee_for_transaction_id, fee_for_transfer_id',
      transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',
      categories: 'id, server_id, type, active, parent_category_id, _sync_status',
      pendingMutations: '++id, entity_type, entity_id, operation, queued_at',
      exchangeRates: 'currency_code',
      settings: 'key, _sync_status',
      dashboards: 'id, server_id, is_default, sort_order, _sync_status',
      dashboardWidgets: 'id, server_id, dashboard_id, _sync_status',
      recurringRules: 'id, server_id, account_id, category_id, status, next_occurrence_date, _sync_status',
      pendingOccurrences: 'id, recurring_rule_id, status, due_date',
      // New in v10 — budgets feature
      budgets: 'id, server_id, account_id, category_id, budget_type, status, _sync_status',
    })
    // No upgrade() needed — new table starts empty
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
