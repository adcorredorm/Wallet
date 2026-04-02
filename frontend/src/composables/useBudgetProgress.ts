// frontend/src/composables/useBudgetProgress.ts
/**
 * useBudgetProgress — computes the spend vs. limit for a budget.
 *
 * Progress is calculated 100% from Dexie transactions (offline-first).
 * All amounts are converted to the budget's currency via exchange rates.
 */

import { computed, ref, type Ref } from 'vue'
import { db } from '@/offline'
import type { LocalBudget } from '@/offline/types'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useCategoriesStore } from '@/stores/categories'

export interface BudgetProgress {
  spent: number
  limit: number
  percentage: number     // 0–100+
  periodStart: string    // YYYY-MM-DD
  periodEnd: string      // YYYY-MM-DD
  isOver: boolean
}

/**
 * Compute [periodStart, periodEnd] for a recurring budget as of `today`.
 *
 * If reference_date is null, uses calendar defaults:
 *   - daily: today only
 *   - weekly: Monday of current week
 *   - monthly: 1st of current month
 *   - yearly: Jan 1st of current year
 *
 * If reference_date is set, finds the period boundary that contains today
 * by stepping forward from reference_date by (interval × frequency).
 */
function getCurrentPeriod(budget: LocalBudget, today: Date): { start: Date; end: Date } {
  if (budget.budget_type === 'one_time') {
    return {
      start: new Date(budget.start_date!),
      end: new Date(budget.end_date!),
    }
  }

  const freq = budget.frequency ?? 'monthly'
  const interval = budget.interval ?? 1

  if (!budget.reference_date) {
    // Calendar defaults
    switch (freq) {
      case 'daily': {
        const start = new Date(today)
        start.setHours(0, 0, 0, 0)
        const end = new Date(start)
        end.setDate(end.getDate() + 1)
        end.setMilliseconds(-1)
        return { start, end }
      }
      case 'weekly': {
        const start = new Date(today)
        const day = start.getDay()
        const diff = day === 0 ? -6 : 1 - day  // Monday
        start.setDate(start.getDate() + diff)
        start.setHours(0, 0, 0, 0)
        const end = new Date(start)
        end.setDate(end.getDate() + 7 * interval)
        end.setMilliseconds(-1)
        return { start, end }
      }
      case 'monthly': {
        const start = new Date(today.getFullYear(), today.getMonth(), 1)
        const end = new Date(today.getFullYear(), today.getMonth() + interval, 1)
        end.setMilliseconds(-1)
        return { start, end }
      }
      case 'yearly': {
        const start = new Date(today.getFullYear(), 0, 1)
        const end = new Date(today.getFullYear() + interval, 0, 1)
        end.setMilliseconds(-1)
        return { start, end }
      }
    }
  }

  // Custom reference_date: find the period that contains today
  const anchor = new Date(budget.reference_date)
  anchor.setHours(0, 0, 0, 0)

  const advanceByPeriod = (d: Date): Date => {
    const next = new Date(d)
    switch (freq) {
      case 'daily': next.setDate(next.getDate() + interval); break
      case 'weekly': next.setDate(next.getDate() + 7 * interval); break
      case 'monthly': next.setMonth(next.getMonth() + interval); break
      case 'yearly': next.setFullYear(next.getFullYear() + interval); break
    }
    return next
  }

  let periodStart = new Date(anchor)
  // If today is before the anchor, move back in increments (edge case: editing reference date in the future)
  while (periodStart > today) {
    const prev = new Date(periodStart)
    switch (freq) {
      case 'daily': prev.setDate(prev.getDate() - interval); break
      case 'weekly': prev.setDate(prev.getDate() - 7 * interval); break
      case 'monthly': prev.setMonth(prev.getMonth() - interval); break
      case 'yearly': prev.setFullYear(prev.getFullYear() - interval); break
    }
    periodStart = prev
  }
  // Advance until the period contains today
  let periodEnd = advanceByPeriod(periodStart)
  while (periodEnd <= today) {
    periodStart = periodEnd
    periodEnd = advanceByPeriod(periodStart)
  }
  periodEnd.setMilliseconds(-1)

  return { start: periodStart, end: periodEnd }
}

function toYMD(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export function useBudgetProgress(budget: Ref<LocalBudget> | LocalBudget) {
  const budgetRef = computed(() => ('value' in budget ? (budget as Ref<LocalBudget>).value : budget))
  const exchangeRatesStore = useExchangeRatesStore()
  const categoriesStore = useCategoriesStore()

  const spent = ref(0)
  const periodStart = ref('')
  const periodEnd = ref('')

  async function refresh() {
    const b = budgetRef.value
    if (!b) return
    const today = new Date()
    const { start, end } = getCurrentPeriod(b, today)
    periodStart.value = toYMD(start)
    periodEnd.value = toYMD(end)

    const startStr = toYMD(start)
    const endStr = toYMD(end)

    // Determine scope category IDs (include subcategories)
    let categoryIds: string[] = []
    if (b.category_id) {
      categoryIds = [
        b.category_id,
        ...categoriesStore.getSubcategories(b.category_id).map((c) => c.id),
      ]
    }

    // Query Dexie: expense transactions in the period
    const txs = await db.transactions
      .where('date')
      .between(startStr, endStr, true, true)
      .filter((tx) => {
        if (tx.type !== 'expense') return false
        if (b.account_id) return tx.account_id === b.account_id
        return categoryIds.includes(tx.category_id ?? '')
      })
      .toArray()

    // Sum, converting each tx to budget currency
    let total = 0
    for (const tx of txs) {
      const txCurrency = tx.original_currency ?? b.currency
      const amount = Number(tx.original_amount ?? tx.amount)
      if (isNaN(amount)) continue
      const converted = exchangeRatesStore.convert(amount, txCurrency, b.currency)
      if (!isNaN(converted)) total += converted
    }
    spent.value = total
  }

  const progress = computed((): BudgetProgress => ({
    spent: spent.value,
    limit: budgetRef.value?.amount_limit ?? 0,
    percentage: (budgetRef.value?.amount_limit ?? 0) > 0
      ? Math.min((spent.value / budgetRef.value.amount_limit) * 100, 999)
      : 0,
    periodStart: periodStart.value,
    periodEnd: periodEnd.value,
    isOver: spent.value > (budgetRef.value?.amount_limit ?? 0),
  }))

  return { progress, refresh }
}
