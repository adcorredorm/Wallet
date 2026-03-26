<script setup lang="ts">
/**
 * SyncErrorSheet — bottom sheet listing all entities with _sync_status === 'error'.
 *
 * Data flow:
 * 1. On open (watch syncStore.syncErrorSheetOpen), query all Dexie tables for
 *    _sync_status === 'error'.
 * 2. Cross-reference db.pendingMutations to get last_error for each entity.
 * 3. Compute dependentCount for each errored entity using DEPENDENCY_FIELDS.
 * 4. Render one SyncErrorItem per errored entity.
 *
 * Discard (single):
 * 1. If dependentCount > 0, show confirm dialog (uiStore.showConfirm).
 * 2. Delete the PendingMutation from pendingMutations.
 * 3. Delete the entity from its Dexie table.
 * 4. Cascade: find all pending mutations referencing this entity's ID and delete
 *    them + their Dexie entities.
 * 5. Refresh the error list from Dexie.
 *
 * Discard all:
 * 1. Show global confirm.
 * 2. Repeat single discard for every errored entity.
 * 3. Call syncManager.forceFullSync().
 * 4. Close sheet.
 */

import { ref, watch } from 'vue'
import { db } from '@/offline/db'
import { DEPENDENCY_FIELDS, syncManager } from '@/offline/sync-manager'
import { useSyncStore } from '@/stores/sync'
import { useUiStore } from '@/stores/ui'
import SyncErrorItem from './SyncErrorItem.vue'
import type { PendingMutation } from '@/offline/types'

interface ErroredEntity {
  id: string
  entityType: PendingMutation['entity_type']
  label: string
  errorReason: string
  dependentCount: number
  mutationId?: number
}

const syncStore = useSyncStore()
const uiStore = useUiStore()

const erroredEntities = ref<ErroredEntity[]>([])
const loading = ref(false)
const discardingId = ref<string | null>(null)
const discardingAll = ref(false)

// ── Data loading ─────────────────────────────────────────────────────────────

async function loadErrors(): Promise<void> {
  loading.value = true
  try {
    const tables = [
      { table: db.accounts,         entityType: 'account'          as const },
      { table: db.transactions,     entityType: 'transaction'      as const },
      { table: db.transfers,        entityType: 'transfer'         as const },
      { table: db.categories,       entityType: 'category'         as const },
      { table: db.dashboards,       entityType: 'dashboard'        as const },
      { table: db.dashboardWidgets, entityType: 'dashboard_widget' as const },
    ]

    const allErrored: ErroredEntity[] = []

    for (const { table, entityType } of tables) {
      const records = await (table as any).where('_sync_status').equals('error').toArray()

      for (const record of records) {
        // Find the corresponding PendingMutation for last_error
        const mutations = await db.pendingMutations
          .where('entity_id').equals(record.id)
          .toArray()
        const mutation = mutations.find(m => m.entity_type === entityType)

        // Compute cascade dependent count
        const dependentCount = await computeDependentCount(entityType, record.id)

        allErrored.push({
          id: record.id,
          entityType,
          label: buildLabel(entityType, record),
          errorReason: mutation?.last_error ?? 'Error desconocido',
          dependentCount,
          mutationId: mutation?.id,
        })
      }
    }

    erroredEntities.value = allErrored
  } finally {
    loading.value = false
  }
}

function buildLabel(entityType: string, record: Record<string, unknown>): string {
  switch (entityType) {
    case 'account':
      return `Cuenta: ${record['name'] ?? record['id']}`
    case 'transaction':
      return `Transacción: ${record['description'] ?? record['id']}`
    case 'transfer':
      return `Transferencia: ${record['id']}`
    case 'category':
      return `Categoría: ${record['name'] ?? record['id']}`
    case 'dashboard':
      return `Dashboard: ${record['name'] ?? record['id']}`
    case 'dashboard_widget':
      return `Widget: ${record['title'] ?? record['id']}`
    default:
      return String(record['id'])
  }
}

async function computeDependentCount(
  _entityType: PendingMutation['entity_type'],
  entityId: string
): Promise<number> {
  // Count pending mutations in the queue that reference this entity as a FK dependency
  const allMutations = await db.pendingMutations.toArray()
  let count = 0
  for (const m of allMutations) {
    if (m.entity_id === entityId) continue
    const fields = DEPENDENCY_FIELDS[m.entity_type] ?? []
    if (fields.some(f => m.payload[f] === entityId)) count++
  }
  return count
}

// ── Discard single ────────────────────────────────────────────────────────────

async function discardEntity(entity: ErroredEntity): Promise<void> {
  if (entity.dependentCount > 0) {
    const confirmed = await uiStore.showConfirm({
      title: 'Descartar con dependientes',
      message: `Este registro tiene ${entity.dependentCount} dependiente${entity.dependentCount !== 1 ? 's' : ''} que también se eliminarán. ¿Continuar?`,
      confirmLabel: 'Sí, descartar',
      cancelLabel: 'Cancelar',
    })
    if (!confirmed) return
  }

  discardingId.value = entity.id
  try {
    await performDiscard(entity)
    await loadErrors()
    syncStore.setErrorCount(erroredEntities.value.length)
  } finally {
    discardingId.value = null
  }
}

async function performDiscard(entity: ErroredEntity): Promise<void> {
  // 1. Delete PendingMutation by the known ID
  if (entity.mutationId != null) {
    await db.pendingMutations.delete(entity.mutationId)
  }

  // 2. Delete all pending mutations for this entity (there could be update/delete mutations too)
  const relatedMutations = await db.pendingMutations
    .where('entity_id').equals(entity.id).toArray()
  for (const m of relatedMutations) {
    if (m.id != null) await db.pendingMutations.delete(m.id)
  }

  // 3. Delete the entity from its Dexie table
  await deleteFromTable(entity.entityType, entity.id)

  // 4. Cascade: delete dependents that reference this entity's ID
  await cascadeDelete(entity.entityType, entity.id)
}

async function deleteFromTable(
  entityType: PendingMutation['entity_type'],
  id: string
): Promise<void> {
  switch (entityType) {
    case 'account':          await db.accounts.delete(id);         break
    case 'transaction':      await db.transactions.delete(id);     break
    case 'transfer':         await db.transfers.delete(id);        break
    case 'category':         await db.categories.delete(id);       break
    case 'dashboard':        await db.dashboards.delete(id);       break
    case 'dashboard_widget': await db.dashboardWidgets.delete(id); break
    case 'setting':          await db.settings.delete(id);         break
  }
}

async function cascadeDelete(
  _entityType: PendingMutation['entity_type'],
  entityId: string
): Promise<void> {
  // Find and delete all pending mutations whose FK fields reference entityId
  const allMutations = await db.pendingMutations.toArray()
  for (const m of allMutations) {
    if (m.entity_id === entityId) continue
    const fields = DEPENDENCY_FIELDS[m.entity_type] ?? []
    if (fields.some(f => m.payload[f] === entityId)) {
      // Delete the dependent entity from its table too
      await deleteFromTable(m.entity_type, m.entity_id)
      // Delete the mutation
      if (m.id != null) await db.pendingMutations.delete(m.id)
      // Recurse for deeper dependencies (dashboard → widget → nothing deeper)
      await cascadeDelete(m.entity_type, m.entity_id)
    }
  }
}

// ── Discard all ───────────────────────────────────────────────────────────────

async function discardAll(): Promise<void> {
  const confirmed = await uiStore.showConfirm({
    title: 'Descartar todos los errores',
    message: `Se eliminarán ${erroredEntities.value.length} registro${erroredEntities.value.length !== 1 ? 's' : ''} con error y sus dependientes. Se realizará una sincronización completa a continuación.`,
    confirmLabel: 'Sí, descartar todo',
    cancelLabel: 'Cancelar',
  })
  if (!confirmed) return

  discardingAll.value = true
  try {
    for (const entity of [...erroredEntities.value]) {
      await performDiscard(entity)
    }
    erroredEntities.value = []
    syncStore.setErrorCount(0)
    syncStore.clearErrors()
    close()
    // Trigger full resync so Dexie is consistent with the server
    await syncManager.forceFullSync()
  } finally {
    discardingAll.value = false
  }
}

// ── Sheet open/close ──────────────────────────────────────────────────────────

function close(): void {
  syncStore.setSyncErrorSheetOpen(false)
}

watch(() => syncStore.syncErrorSheetOpen, (open) => {
  if (open) loadErrors()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet-fade">
      <div
        v-if="syncStore.syncErrorSheetOpen"
        class="fixed inset-0 z-50 flex items-end justify-center"
        style="background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px);"
        role="dialog"
        aria-modal="true"
        aria-label="Errores de sincronización"
        @click.self="close"
      >
        <div
          class="w-full max-w-lg rounded-t-2xl flex flex-col"
          style="background-color: #1e293b; border-top: 1px solid rgba(51, 65, 85, 0.8); max-height: 80vh;"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-dark-border">
            <h2 class="text-base font-semibold text-dark-text-primary">
              Errores de sincronización
            </h2>
            <button
              type="button"
              class="flex items-center justify-center w-8 h-8 rounded-lg text-dark-text-secondary hover:text-dark-text-primary transition-colors"
              aria-label="Cerrar"
              @click="close"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body: error list -->
          <div class="flex-1 overflow-y-auto px-5">
            <!-- Loading state -->
            <div v-if="loading" class="py-8 text-center text-dark-text-secondary text-sm">
              Cargando errores...
            </div>

            <!-- Empty state -->
            <div v-else-if="erroredEntities.length === 0" class="py-8 text-center text-dark-text-secondary text-sm">
              No hay errores de sincronización.
            </div>

            <!-- Error list -->
            <div v-else>
              <SyncErrorItem
                v-for="entity in erroredEntities"
                :key="entity.id"
                :entity-type="entity.entityType"
                :entity-id="entity.id"
                :entity-label="entity.label"
                :error-reason="entity.errorReason"
                :dependent-count="entity.dependentCount"
                :discarding="discardingId === entity.id"
                @discard="discardEntity(entity)"
              />
            </div>
          </div>

          <!-- Footer: Discard all -->
          <div
            v-if="erroredEntities.length > 0"
            class="px-5 py-4 border-t border-dark-border"
          >
            <button
              type="button"
              class="w-full flex items-center justify-center px-4 py-3 rounded-xl text-sm font-medium transition-colors min-h-[44px]"
              style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #fca5a5;"
              :disabled="discardingAll"
              @click="discardAll"
            >
              {{ discardingAll ? 'Descartando...' : `Descartar todos (${erroredEntities.length})` }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-fade-enter-active {
  transition: opacity 250ms ease-out, transform 250ms ease-out;
}

.sheet-fade-leave-active {
  transition: opacity 200ms ease-in, transform 200ms ease-in;
}

.sheet-fade-enter-from,
.sheet-fade-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
