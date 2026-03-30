/**
 * useRecurringEngine — frontend generation engine for recurring transactions.
 *
 * Runs on app init (after stores load) and on visibilitychange to 'visible'.
 * Processes all active RecurringRules whose next_occurrence_date <= today.
 *
 * Auto mode:   creates real transactions for all overdue cycles.
 * Verification mode: expires previous pending occurrence, creates one new
 *   pending for the most recent overdue cycle.
 *
 * Guard against double execution via `running` flag.
 */

import { db } from '@/offline'
import type { LocalRecurringRule } from '@/offline/types'
import { useRecurringRulesStore } from '@/stores/recurringRules'
import { useTransactionsStore } from '@/stores/transactions'
import { useAccountsStore } from '@/stores/accounts'
import { useCategoriesStore } from '@/stores/categories'
import { usePendingOccurrences } from './usePendingOccurrences'

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

/** Return today's date as YYYY-MM-DD (local time). */
function todayISO(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * Advance a date string (YYYY-MM-DD) by one recurrence interval.
 * Handles day-of-month overflow: day_of_month=31 in April → April 30.
 */
export function advanceDate(currentDate: string, rule: Pick<LocalRecurringRule, 'frequency' | 'interval' | 'day_of_month'>): string {
  const date = new Date(currentDate + 'T00:00:00')

  switch (rule.frequency) {
    case 'daily':
      date.setDate(date.getDate() + rule.interval)
      break

    case 'weekly':
      date.setDate(date.getDate() + 7 * rule.interval)
      break

    case 'monthly': {
      const targetDay = rule.day_of_month ?? date.getDate()
      date.setMonth(date.getMonth() + rule.interval, 1)
      // Clamp to last day of the target month (handles e.g. Jan 31 → Feb 28)
      const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
      date.setDate(Math.min(targetDay, lastDay))
      break
    }

    case 'yearly': {
      const targetDay = rule.day_of_month ?? date.getDate()
      date.setFullYear(date.getFullYear() + rule.interval, date.getMonth(), 1)
      const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
      date.setDate(Math.min(targetDay, lastDay))
      break
    }
  }

  return date.toISOString().slice(0, 10)
}

// ---------------------------------------------------------------------------
// Engine
// ---------------------------------------------------------------------------

export function useRecurringEngine() {
  const rulesStore = useRecurringRulesStore()
  const transactionsStore = useTransactionsStore()
  const accountsStore = useAccountsStore()
  const categoriesStore = useCategoriesStore()
  const pendingHelper = usePendingOccurrences()

  /** Prevents concurrent engine runs (e.g. rapid tab focus events). */
  let running = false

  /**
   * Idempotency guard: returns true if a transaction for this rule + date
   * already exists in Dexie, preventing duplicate generation.
   */
  async function transactionExistsForRuleAndDate(ruleId: string, date: string): Promise<boolean> {
    const count = await db.transactions
      .filter(tx => tx.recurring_rule_id === ruleId && tx.date === date)
      .count()
    return count > 0
  }

  /**
   * Check if the rule's account or category is inactive.
   * If so, pause the rule and return true.
   */
  async function autoPauseIfNeeded(rule: LocalRecurringRule): Promise<boolean> {
    const account = accountsStore.accounts.find(a => a.id === rule.account_id)
    const category = categoriesStore.categories.find(c => c.id === rule.category_id)

    const accountInactive = account !== undefined && !account.active
    const categoryInactive = category !== undefined && !(category as any).active

    if (accountInactive || categoryInactive) {
      await rulesStore.updateRule(rule.id, { status: 'paused' })
      return true
    }
    return false
  }

  /**
   * Process a single due rule.
   *
   * Auto mode: generates all overdue cycles as real transactions.
   * Verification mode: expires stale pending, creates one pending for the
   *   most recent overdue cycle.
   */
  async function processRule(rule: LocalRecurringRule): Promise<void> {
    const today = todayISO()
    let nextDate = rule.next_occurrence_date
    let occurrencesCreated = rule.occurrences_created

    if (!rule.requires_confirmation) {
      // ── Auto mode: generate ALL overdue cycles ─────────────────────────────
      while (nextDate <= today) {
        // Check completion limits before generating
        if (
          rule.max_occurrences !== null &&
          rule.max_occurrences !== undefined &&
          occurrencesCreated >= rule.max_occurrences
        ) {
          await rulesStore.updateRule(rule.id, { status: 'completed' })
          return
        }
        if (rule.end_date && nextDate > rule.end_date) {
          await rulesStore.updateRule(rule.id, { status: 'completed' })
          return
        }

        // Idempotency: skip if transaction already exists for this cycle
        const alreadyExists = await transactionExistsForRuleAndDate(rule.id, nextDate)
        if (!alreadyExists) {
          await transactionsStore.createTransaction({
            type: rule.type,
            amount: rule.amount,
            date: nextDate,
            account_id: rule.account_id,
            category_id: rule.category_id,
            title: rule.title,
            description: rule.description ?? undefined,
            tags: [...rule.tags.filter(t => t !== 'Recurrente'), 'Recurrente'],
            recurring_rule_id: rule.id,
          } as any)
          occurrencesCreated++
        }

        nextDate = advanceDate(nextDate, rule)
      }

      await rulesStore.updateRule(rule.id, {
        next_occurrence_date: nextDate,
        occurrences_created: occurrencesCreated,
      } as any)

    } else {
      // ── Verification mode: one pending for most recent overdue cycle ────────
      // Walk forward to find the most recent cycle that is still <= today.
      let mostRecentDate = nextDate

      // Check end_date completion before starting
      if (rule.end_date && nextDate > rule.end_date) {
        await rulesStore.updateRule(rule.id, { status: 'completed' })
        return
      }

      let candidate = advanceDate(mostRecentDate, rule)
      while (candidate <= today) {
        mostRecentDate = candidate
        candidate = advanceDate(mostRecentDate, rule)
      }

      // Expire any existing pending occurrences for this rule
      await pendingHelper.loadOccurrences()
      await pendingHelper.expireAllPendingForRule(rule.id)

      // Only create if no confirmed transaction already exists for this date
      const alreadyConfirmed = await transactionExistsForRuleAndDate(rule.id, mostRecentDate)
      if (!alreadyConfirmed) {
        await pendingHelper.createOccurrence({
          recurring_rule_id: rule.id,
          due_date: mostRecentDate,
          suggested_amount: rule.amount,
          status: 'pending',
        })
      }

      // Only advance next_occurrence_date — do NOT increment occurrences_created.
      // occurrences_created is incremented when the user confirms the pending occurrence.
      const nextAfterMostRecent = advanceDate(mostRecentDate, rule)
      await rulesStore.updateRule(rule.id, {
        next_occurrence_date: nextAfterMostRecent,
      } as any)

      // Check end_date completion (occurrences-based completion happens on confirm)
      if (rule.end_date && nextAfterMostRecent > rule.end_date) {
        await rulesStore.updateRule(rule.id, { status: 'completed' })
      }
    }
  }

  /**
   * Main entry point. Loads active rules, processes any that are due.
   * Idempotent via `running` guard.
   */
  async function run(): Promise<void> {
    if (running) return
    running = true
    try {
      await rulesStore.loadRules()

      const activeRules = rulesStore.rules.filter(r => r.status === 'active')
      const today = todayISO()

      for (const rule of activeRules) {
        // Auto-pause before processing if account/category is inactive
        const paused = await autoPauseIfNeeded(rule)
        if (paused) continue

        if (rule.next_occurrence_date <= today) {
          await processRule(rule)
        }
      }
    } finally {
      running = false
    }
  }

  return { run }
}
