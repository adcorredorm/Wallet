/**
 * useOfflineMutation — generic offline-first write composable with lifecycle hooks.
 *
 * Encapsulates the 3-step pattern repeated across every store:
 *   1. Write to Dexie (IndexedDB)
 *   2. Update Pinia reactive state
 *   3. Enqueue mutation for background sync
 *
 * Lifecycle hooks let each store inject entity-specific side effects
 * (balance adjustments, base_rate computation, soft-delete behavior)
 * without modifying the composable internals.
 *
 * CRITICAL: This is a pure refactor tool. Every store action that uses this
 * composable must produce the EXACT SAME Dexie writes, reactive state updates,
 * and mutation queue entries as before.
 */

import type { Ref } from 'vue'
import type { Table } from 'dexie'
import { mutationQueue } from '@/offline/mutation-queue'
import type { PendingMutation } from '@/offline/types'

export interface OfflineMutationConfig<TLocal, TCreateDto, TUpdateDto> {
  /** Entity type for mutation queue (must match PendingMutation['entity_type']) */
  entityType: PendingMutation['entity_type']
  /** Dexie table reference */
  table: Table<TLocal>
  /** Reactive array in the store */
  items: Ref<TLocal[]>
  /** Generate a temp-* UUID for new records */
  generateId: () => string
  /** Convert a create DTO + generated id + timestamp into a full local record */
  toLocal: (dto: TCreateDto, id: string, now: string) => TLocal
  /** Merge an update DTO into an existing local record */
  mergeUpdate: (existing: TLocal, dto: TUpdateDto, now: string) => TLocal
  /** Build the mutation queue payload from a full local record (for CREATE) */
  toCreatePayload: (local: TLocal) => Record<string, unknown>
  /** Build the mutation queue payload from an update DTO (for UPDATE) */
  toUpdatePayload: (dto: TUpdateDto, id: string) => Record<string, unknown>

  // ── Lifecycle hooks (all optional) ──────────────────────────────────────

  /** Called after toLocal(), before Dexie write */
  beforeCreate?: (dto: TCreateDto, local: TLocal) => void | Promise<void>
  /** Called after Dexie write + reactive state push */
  afterCreate?: (local: TLocal, dto: TCreateDto) => void | Promise<void>

  /** Called before Dexie update; can TRANSFORM the dto (e.g., inject base_rate) */
  beforeUpdate?: (id: string, dto: TUpdateDto, existing: TLocal) => TUpdateDto | Promise<TUpdateDto>
  /** Called after Dexie update + reactive state update; receives old + merged entity */
  afterUpdate?: (id: string, dto: TUpdateDto, old: TLocal, merged: TLocal) => void | Promise<void>

  /** Called before any remove logic */
  beforeRemove?: (id: string, existing: TLocal) => void | Promise<void>
  /** Called after remove completes (in BOTH cancellation and normal paths) */
  afterRemove?: (id: string, removed: TLocal) => void | Promise<void>

  /** Override default db.table.delete() for soft-delete pattern */
  onRemove?: (id: string, existing: TLocal) => Promise<void>
  /** Override default items.value.filter() for custom reactive state removal */
  onRemoveFromState?: (id: string) => void
  /** Dispatch a window Event after remove (e.g., 'wallet:local-delete') */
  afterRemoveEvent?: string
}

export function useOfflineMutation<TLocal extends { id: string }, TCreateDto, TUpdateDto>(
  config: OfflineMutationConfig<TLocal, TCreateDto, TUpdateDto>
) {
  /**
   * CREATE — generates local record, writes to Dexie, pushes to reactive array,
   * invokes hooks, enqueues 'create' mutation.
   */
  async function create(dto: TCreateDto): Promise<TLocal> {
    const id = config.generateId()
    const now = new Date().toISOString()
    const local = config.toLocal(dto, id, now)

    // Hook: beforeCreate
    if (config.beforeCreate) {
      await config.beforeCreate(dto, local)
    }

    // Step 1 — Dexie write
    await config.table.add(local as any)

    // Step 2 — Reactive state update
    config.items.value.push(local)

    // Hook: afterCreate
    if (config.afterCreate) {
      await config.afterCreate(local, dto)
    }

    // Step 3 — Enqueue CREATE mutation
    await mutationQueue.enqueue({
      entity_type: config.entityType,
      entity_id: id,
      operation: 'create',
      payload: config.toCreatePayload(local),
    })

    return local
  }

  /**
   * UPDATE — finds existing, invokes beforeUpdate (can transform dto),
   * writes to Dexie, updates reactive array, invokes afterUpdate,
   * enqueues 'update' (or merges with pending create).
   */
  async function update(id: string, dto: TUpdateDto): Promise<void> {
    const existing = await config.table.get(id) as TLocal | undefined
    if (!existing) throw new Error(`${config.entityType} not found in local DB: ${id}`)

    const now = new Date().toISOString()

    // Hook: beforeUpdate (can transform dto)
    let effectiveDto = dto
    if (config.beforeUpdate) {
      effectiveDto = await config.beforeUpdate(id, dto, existing)
    }

    // Step 1 — Dexie update (merge + sync metadata)
    const merged = config.mergeUpdate(existing, effectiveDto, now)
    await config.table.update(id, {
      ...merged,
      _sync_status: 'pending',
      _local_updated_at: now,
    } as any)

    // Step 2 — Reactive state update
    const idx = config.items.value.findIndex((item) => item.id === id)
    if (idx !== -1) {
      const old = { ...config.items.value[idx] }
      config.items.value[idx] = { ...merged, _sync_status: 'pending', _local_updated_at: now } as TLocal

      // Hook: afterUpdate (receives old + merged for delta computation)
      if (config.afterUpdate) {
        await config.afterUpdate(id, effectiveDto, old as TLocal, config.items.value[idx])
      }
    }

    // Step 3 — Merge optimisation: collapse into pending CREATE if one exists
    const pendingCreate = await mutationQueue.findPendingCreate(config.entityType, id)
    if (pendingCreate?.id != null) {
      await mutationQueue.updatePayload(pendingCreate.id, {
        ...pendingCreate.payload,
        ...config.toUpdatePayload(effectiveDto, id),
      })
    } else {
      await mutationQueue.enqueue({
        entity_type: config.entityType,
        entity_id: id,
        operation: 'update',
        payload: config.toUpdatePayload(effectiveDto, id),
      })
    }
  }

  /**
   * REMOVE — checks for pending create (cancellation optimisation),
   * deletes from Dexie (or calls onRemove override), removes from reactive
   * state (or calls onRemoveFromState override), enqueues 'delete' mutation,
   * dispatches afterRemoveEvent.
   *
   * afterRemove hook is called in BOTH paths (cancellation and normal delete)
   * so balance reversals always happen.
   */
  async function remove(id: string): Promise<void> {
    // Capture the entity before removal for hooks
    const existing = config.items.value.find((item) => item.id === id) as TLocal | undefined

    // Hook: beforeRemove
    if (config.beforeRemove && existing) {
      await config.beforeRemove(id, existing)
    }

    // Cancellation optimisation: if CREATE is still pending, cancel it
    const pendingCreate = await mutationQueue.findPendingCreate(config.entityType, id)
    if (pendingCreate?.id != null) {
      await mutationQueue.remove(pendingCreate.id)

      // Dexie removal: use override or default hard-delete
      if (config.onRemove && existing) {
        await config.onRemove(id, existing)
      } else {
        await config.table.delete(id as any)
      }

      // Reactive state removal: use override or default filter
      if (config.onRemoveFromState) {
        config.onRemoveFromState(id)
      } else {
        config.items.value = config.items.value.filter((item) => item.id !== id)
      }

      // Hook: afterRemove (called in cancellation path too)
      if (config.afterRemove && existing) {
        await config.afterRemove(id, existing)
      }

      // No DELETE mutation needed — entity never existed on server
      return
    }

    // Normal path: entity exists on the server

    // Dexie removal: use override or default hard-delete
    if (config.onRemove && existing) {
      await config.onRemove(id, existing)
    } else {
      await config.table.delete(id as any)
    }

    // Reactive state removal: use override or default filter
    if (config.onRemoveFromState) {
      config.onRemoveFromState(id)
    } else {
      config.items.value = config.items.value.filter((item) => item.id !== id)
    }

    // Hook: afterRemove
    if (config.afterRemove && existing) {
      await config.afterRemove(id, existing)
    }

    // Enqueue DELETE mutation
    await mutationQueue.enqueue({
      entity_type: config.entityType,
      entity_id: id,
      operation: 'delete',
      payload: { id },
    })

    // Dispatch afterRemoveEvent if configured
    if (config.afterRemoveEvent) {
      window.dispatchEvent(new Event(config.afterRemoveEvent))
    }
  }

  return { create, update, remove }
}
