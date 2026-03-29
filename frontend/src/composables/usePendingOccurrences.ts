/**
 * usePendingOccurrences — CRUD for Dexie-only PendingOccurrence records.
 *
 * PendingOccurrences are ephemeral UI state — not synced to the backend.
 * They represent verification-mode recurrences awaiting user confirmation.
 * If Dexie is cleared, the engine regenerates them on next run.
 */

import { ref, computed } from 'vue'
import { db } from '@/offline'
import { generateTempId } from '@/offline'
import type { LocalPendingOccurrence, PendingOccurrenceStatus } from '@/offline/types'

export function usePendingOccurrences() {
  const occurrences = ref<LocalPendingOccurrence[]>([])

  const pendingCount = computed(
    () => occurrences.value.filter(o => o.status === 'pending').length
  )

  async function loadOccurrences() {
    occurrences.value = await db.pendingOccurrences.toArray()
  }

  async function createOccurrence(data: Omit<LocalPendingOccurrence, 'id' | 'created_at'>): Promise<LocalPendingOccurrence> {
    const occ: LocalPendingOccurrence = {
      id: generateTempId(),
      created_at: new Date().toISOString(),
      ...data,
    }
    await db.pendingOccurrences.add(occ)
    occurrences.value.push(occ)
    return occ
  }

  async function setStatus(id: string, status: PendingOccurrenceStatus): Promise<void> {
    await db.pendingOccurrences.update(id, { status })
    const idx = occurrences.value.findIndex(o => o.id === id)
    if (idx !== -1) {
      occurrences.value[idx] = { ...occurrences.value[idx], status }
    }
  }

  async function confirm(id: string): Promise<void> {
    await setStatus(id, 'confirmed')
  }

  async function discard(id: string): Promise<void> {
    await setStatus(id, 'discarded')
  }

  async function expire(id: string): Promise<void> {
    await setStatus(id, 'expired')
  }

  /**
   * Expire all pending occurrences for a given rule.
   * Called before creating a new pending occurrence for the same rule so
   * there is never more than one active pending per rule.
   */
  async function expireAllPendingForRule(recurringRuleId: string): Promise<void> {
    const pendingForRule = await db.pendingOccurrences
      .where('recurring_rule_id').equals(recurringRuleId)
      .filter(o => o.status === 'pending')
      .toArray()

    for (const occ of pendingForRule) {
      await setStatus(occ.id, 'expired')
    }
  }

  return {
    occurrences,
    pendingCount,
    loadOccurrences,
    createOccurrence,
    confirm,
    discard,
    expire,
    expireAllPendingForRule,
  }
}
