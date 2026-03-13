/**
 * Dashboards Store
 *
 * Manages the state for user-defined analytics dashboards and their widgets.
 * Follows the same offline-first patterns as accounts/transactions/transfers:
 *
 *   Read  — stale-while-revalidate: IndexedDB is read first for instant cold-start,
 *            then the API is fetched in the background and Dexie is updated.
 *   Write — three-step mutation queue pattern:
 *             1. Write optimistic record to Dexie (_sync_status: 'pending')
 *             2. Update Pinia reactive state immediately (zero-latency UI)
 *             3. Enqueue a PendingMutation for background sync via SyncManager
 *
 * ensureStarterDashboard() is called on first visit to /analytics and creates
 * a default dashboard with 3 expense widgets if the user has none.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardsApi } from '@/api/dashboards'
import { db, mutationQueue } from '@/offline'
import { generateTempId } from '@/offline/temp-id'
import { useSettingsStore } from '@/stores/settings'
import type {
  DashboardWithWidgets,
  CreateDashboardDto,
  UpdateDashboardDto,
  CreateWidgetDto,
  UpdateWidgetDto
} from '@/types/dashboard'
import type { LocalDashboard, LocalDashboardWidget } from '@/offline/types'

export const useDashboardsStore = defineStore('dashboards', () => {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  const dashboards = ref<LocalDashboard[]>([])
  const currentDashboard = ref<DashboardWithWidgets & { widgets: LocalDashboardWidget[] } | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  // Single-flight guard for ensureStarterDashboard to prevent concurrent calls
  // from creating duplicate starter dashboards
  let _ensureStarterInFlight = false


  // ---------------------------------------------------------------------------
  // Actions — Reads (stale-while-revalidate)
  // ---------------------------------------------------------------------------

  /**
   * Fetch all dashboards using stale-while-revalidate.
   *
   * 1. Load from IndexedDB immediately for instant UI.
   * 2. If online, fetch from API in background, bulkPut to Dexie, update state.
   */
  async function fetchDashboards() {
    loading.value = true
    error.value = null
    try {
      // Step 1 — Instant local read
      const localData = await db.dashboards.toArray()
      dashboards.value = localData

      // Step 2 — Background revalidation (fire-and-forget)
      ;(async () => {
        try {
          const serverItems = await dashboardsApi.getAll()
          const now = new Date().toISOString()
          const localMapped: LocalDashboard[] = serverItems.map(item => ({
            ...item,
            _sync_status: 'synced' as const,
            _local_updated_at: now
          }))
          await db.dashboards.bulkPut(localMapped)

          // Remove orphaned records no longer on the server
          const serverIds = new Set(localMapped.map(d => d.id))
          const allLocalIds = await db.dashboards.toCollection().primaryKeys()
          const orphanedIds = allLocalIds.filter(id => !serverIds.has(id as string))
          if (orphanedIds.length > 0) await db.dashboards.bulkDelete(orphanedIds)

          // Re-read from Dexie for authoritative local state
          const freshFromDB = await db.dashboards.toArray()
          dashboards.value = freshFromDB
        } catch (err) {
          console.warn('[dashboards store] Background revalidation failed:', err)
        }
      })()
    } catch (err: any) {
      error.value = err.message || 'Error al cargar dashboards'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch a single dashboard with its widgets.
   *
   * 1. Load dashboard + widgets from Dexie immediately.
   * 2. If online, fetch from API, persist to Dexie, update currentDashboard.
   */
  async function fetchDashboard(id: string) {
    loading.value = true
    error.value = null
    try {
      // Step 1 — Local read
      const localDashboard = await db.dashboards.get(id)
      const localWidgets = await db.dashboardWidgets
        .where('dashboard_id')
        .equals(id)
        .toArray()

      if (localDashboard) {
        currentDashboard.value = {
          ...localDashboard,
          widgets: localWidgets
        }
      }

      // Step 2 — Background revalidation
      ;(async () => {
        try {
          const serverData = await dashboardsApi.getById(id)
          const now = new Date().toISOString()

          // Persist dashboard
          // Remove the widgets key entirely for Dexie storage
          const { widgets: serverWidgets, ...dashboardOnly } = serverData
          const dashForDexie: LocalDashboard = {
            ...dashboardOnly,
            _sync_status: 'synced',
            _local_updated_at: now
          }
          await db.dashboards.put(dashForDexie)

          // Persist widgets — replace all widgets for this dashboard
          const existingWidgetIds = await db.dashboardWidgets
            .where('dashboard_id')
            .equals(id)
            .primaryKeys()
          if (existingWidgetIds.length > 0) {
            await db.dashboardWidgets.bulkDelete(existingWidgetIds)
          }

          const localWidgetsMapped: LocalDashboardWidget[] = serverWidgets.map(w => ({
            ...w,
            _sync_status: 'synced' as const,
            _local_updated_at: now
          }))
          if (localWidgetsMapped.length > 0) {
            await db.dashboardWidgets.bulkPut(localWidgetsMapped)
          }

          // Update reactive state
          currentDashboard.value = {
            ...dashForDexie,
            widgets: localWidgetsMapped
          }

          // Also update the dashboard in the list
          const idx = dashboards.value.findIndex(d => d.id === id)
          if (idx >= 0) {
            dashboards.value[idx] = dashForDexie
          }
        } catch (err) {
          console.warn(`[dashboards store] Background revalidation failed for id=${id}:`, err)
        }
      })()
    } catch (err: any) {
      error.value = err.message || 'Error al cargar dashboard'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Dashboard CRUD (direct API calls)
  // ---------------------------------------------------------------------------

  /**
   * Create a dashboard — offline-first.
   * Generates a local UUID, persists to Dexie immediately, then syncs to API
   * in background. On success, reconciles the server-assigned ID.
   */
  async function createDashboard(dto: CreateDashboardDto) {
    const settingsStore = useSettingsStore()
    const payload: CreateDashboardDto = {
      ...dto,
      display_currency: dto.display_currency || settingsStore.primaryCurrency
    }

    loading.value = true
    error.value = null
    try {
      const tempId = generateTempId()
      const now = new Date().toISOString()
      const optimistic: LocalDashboard = {
        id: tempId,
        name: payload.name,
        description: payload.description ?? null,
        display_currency: payload.display_currency,
        layout_columns: payload.layout_columns ?? 2,
        is_default: payload.is_default ?? false,
        sort_order: payload.sort_order ?? 0,
        created_at: now,
        updated_at: now,
        _sync_status: 'pending',
        _local_updated_at: now,
      }

      await db.dashboards.put(optimistic)
      dashboards.value.push(optimistic)

      await mutationQueue.enqueue({
        entity_type: 'dashboard',
        entity_id: tempId,
        operation: 'create',
        payload: { ...payload, client_id: tempId } as Record<string, unknown>,
      })

      return optimistic
    } catch (err: any) {
      error.value = err.message || 'Error al crear dashboard'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update a dashboard — offline-first.
   * Merges changes into Dexie immediately, then syncs to API in background.
   */
  async function updateDashboard(id: string, dto: UpdateDashboardDto) {
    loading.value = true
    error.value = null
    try {
      const existing = await db.dashboards.get(id)
      if (!existing) throw new Error('Dashboard not found in local DB')

      const now = new Date().toISOString()
      const patch = {
        ...(dto.name !== undefined && { name: dto.name }),
        ...(dto.description !== undefined && { description: dto.description }),
        ...(dto.display_currency !== undefined && { display_currency: dto.display_currency }),
        ...(dto.layout_columns !== undefined && { layout_columns: dto.layout_columns }),
        ...(dto.is_default !== undefined && { is_default: dto.is_default }),
        ...(dto.sort_order !== undefined && { sort_order: dto.sort_order }),
        updated_at: now,
        _sync_status: 'pending' as const,
        _local_updated_at: now,
      }

      await db.dashboards.update(id, patch)
      const optimistic: LocalDashboard = { ...existing, ...patch }

      const idx = dashboards.value.findIndex(d => d.id === id)
      if (idx >= 0) dashboards.value[idx] = optimistic
      if (currentDashboard.value?.id === id) {
        currentDashboard.value = { ...optimistic, widgets: currentDashboard.value.widgets }
      }

      // Merge into pending CREATE if one exists (avoids POST + PATCH round-trip)
      const pendingCreate = await mutationQueue.findPendingCreate('dashboard', id)
      if (pendingCreate?.id != null) {
        await mutationQueue.updatePayload(pendingCreate.id, { ...pendingCreate.payload, ...dto })
      } else {
        await mutationQueue.enqueue({
          entity_type: 'dashboard',
          entity_id: id,
          operation: 'update',
          payload: dto as Record<string, unknown>,
        })
      }

      return optimistic
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar dashboard'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a dashboard — offline-first.
   * Removes from Dexie and state immediately, then deletes from API in background.
   */
  async function deleteDashboard(id: string) {
    loading.value = true
    error.value = null
    try {
      await db.dashboards.delete(id)
      const widgetIds = await db.dashboardWidgets.where('dashboard_id').equals(id).primaryKeys()
      if (widgetIds.length > 0) await db.dashboardWidgets.bulkDelete(widgetIds)

      dashboards.value = dashboards.value.filter(d => d.id !== id)
      if (currentDashboard.value?.id === id) currentDashboard.value = null

      // If there is a pending CREATE (dashboard never reached server), cancel it
      const pendingCreate = await mutationQueue.findPendingCreate('dashboard', id)
      if (pendingCreate?.id != null) {
        await mutationQueue.remove(pendingCreate.id)
        // No DELETE mutation needed — entity never existed on server
      } else {
        await mutationQueue.enqueue({
          entity_type: 'dashboard',
          entity_id: id,
          operation: 'delete',
          payload: {},
        })
      }
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar dashboard'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Widget CRUD (offline-first)
  // ---------------------------------------------------------------------------

  /**
   * Create a widget — offline-first.
   * Generates a local UUID, persists to Dexie immediately, then syncs to API
   * in background. On success, reconciles the server-assigned ID.
   */
  async function createWidget(dashboardId: string, dto: CreateWidgetDto) {
    loading.value = true
    error.value = null
    try {
      const tempId = generateTempId()
      const now = new Date().toISOString()
      const optimistic: LocalDashboardWidget = {
        id: tempId,
        dashboard_id: dashboardId,
        widget_type: dto.widget_type,
        title: dto.title,
        position_x: dto.position_x ?? 0,
        position_y: dto.position_y ?? 0,
        width: dto.width ?? 1,
        height: dto.height ?? 1,
        config: dto.config,
        created_at: now,
        updated_at: now,
        _sync_status: 'pending',
        _local_updated_at: now,
      }

      await db.dashboardWidgets.put(optimistic)
      if (currentDashboard.value?.id === dashboardId) {
        currentDashboard.value = {
          ...currentDashboard.value,
          widgets: [...currentDashboard.value.widgets, optimistic],
        }
      }

      await mutationQueue.enqueue({
        entity_type: 'dashboard_widget',
        entity_id: tempId,
        operation: 'create',
        // dashboard_id is included so SyncManager can route to the correct endpoint
        payload: { ...dto, dashboard_id: dashboardId, client_id: tempId } as Record<string, unknown>,
      })

      return optimistic
    } catch (err: any) {
      error.value = err.message || 'Error al crear widget'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update a widget — offline-first.
   *
   * 1. Merge dto into existing Dexie record and persist immediately (_sync_status: 'pending').
   * 2. Update reactive state so the UI reflects the change instantly.
   * 3. Fire API call in background; on success mark as 'synced'. On failure, leave
   *    as 'pending' — the next fetchDashboard revalidation will reconcile.
   */
  async function updateWidget(dashboardId: string, widgetId: string, dto: UpdateWidgetDto) {
    loading.value = true
    error.value = null
    try {
      const existing = await db.dashboardWidgets.get(widgetId)
      if (!existing) throw new Error('Widget not found in local DB')

      const now = new Date().toISOString()
      const patch = {
        ...(dto.widget_type !== undefined && { widget_type: dto.widget_type }),
        ...(dto.title !== undefined && { title: dto.title }),
        ...(dto.config !== undefined && { config: dto.config }),
        ...(dto.position_x !== undefined && { position_x: dto.position_x }),
        ...(dto.position_y !== undefined && { position_y: dto.position_y }),
        ...(dto.width !== undefined && { width: dto.width }),
        ...(dto.height !== undefined && { height: dto.height }),
        updated_at: now,
        _sync_status: 'pending' as const,
        _local_updated_at: now,
      }

      await db.dashboardWidgets.update(widgetId, patch)
      const optimistic: LocalDashboardWidget = { ...existing, ...patch }

      if (currentDashboard.value?.id === dashboardId) {
        const widgetIdx = currentDashboard.value.widgets.findIndex(w => w.id === widgetId)
        if (widgetIdx >= 0) {
          const newWidgets = [...currentDashboard.value.widgets]
          newWidgets[widgetIdx] = optimistic
          currentDashboard.value = { ...currentDashboard.value, widgets: newWidgets }
        }
      }

      const pendingCreate = await mutationQueue.findPendingCreate('dashboard_widget', widgetId)
      if (pendingCreate?.id != null) {
        await mutationQueue.updatePayload(pendingCreate.id, { ...pendingCreate.payload, ...dto })
      } else {
        await mutationQueue.enqueue({
          entity_type: 'dashboard_widget',
          entity_id: widgetId,
          operation: 'update',
          // dashboard_id is needed by SyncManager to build the correct URL
          payload: { ...dto, dashboard_id: dashboardId } as Record<string, unknown>,
        })
      }

      return optimistic
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar widget'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a widget — offline-first.
   * Removes from Dexie and state immediately, then deletes from API in background.
   */
  async function deleteWidget(dashboardId: string, widgetId: string) {
    loading.value = true
    error.value = null
    try {
      await db.dashboardWidgets.delete(widgetId)
      if (currentDashboard.value?.id === dashboardId) {
        currentDashboard.value = {
          ...currentDashboard.value,
          widgets: currentDashboard.value.widgets.filter(
            w => w.id !== widgetId
          ) as LocalDashboardWidget[],
        }
      }

      const pendingCreate = await mutationQueue.findPendingCreate('dashboard_widget', widgetId)
      if (pendingCreate?.id != null) {
        await mutationQueue.remove(pendingCreate.id)
      } else {
        await mutationQueue.enqueue({
          entity_type: 'dashboard_widget',
          entity_id: widgetId,
          operation: 'delete',
          // dashboard_id is required by SyncManager to build the DELETE URL
          payload: { dashboard_id: dashboardId },
        })
      }
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar widget'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Starter Dashboard
  // ---------------------------------------------------------------------------

  /**
   * Ensure the user has at least one dashboard. Called on first visit to
   * /analytics. If no dashboards exist, creates "Mi Dashboard" with 3
   * default expense widgets that provide immediate value:
   *   - Bar chart: expenses by category this month
   *   - Number card: total expenses this month
   *   - Line chart: expense trend over last 90 days
   */
  async function ensureStarterDashboard() {
    if (_ensureStarterInFlight) return
    _ensureStarterInFlight = true
    try {
      await fetchDashboards()

      if (dashboards.value.length > 0) return

      const settingsStore = useSettingsStore()

      const newDashboard = await createDashboard({
        name: 'Mi Dashboard',
        display_currency: settingsStore.primaryCurrency,
        layout_columns: 2
      })

      // Create the 3 default widgets sequentially to preserve position order
      await createWidget(newDashboard.id, {
        widget_type: 'bar',
        title: 'Gastos por Categoría (Este Mes)',
        position_x: 0,
        position_y: 0,
        width: 2,
        height: 1,
        config: {
          time_range: { type: 'dynamic', value: 'this_month' },
          filters: { type: 'expense' },
          granularity: 'month',
          group_by: 'category',
          aggregation: 'sum'
        }
      })

      await createWidget(newDashboard.id, {
        widget_type: 'number',
        title: 'Total Gastos (Este Mes)',
        position_x: 0,
        position_y: 1,
        width: 1,
        height: 1,
        config: {
          time_range: { type: 'dynamic', value: 'this_month' },
          filters: { type: 'expense' },
          granularity: 'month',
          group_by: 'none',
          aggregation: 'sum'
        }
      })

      await createWidget(newDashboard.id, {
        widget_type: 'line',
        title: 'Tendencia de Gastos (Últimos 90 días)',
        position_x: 1,
        position_y: 1,
        width: 1,
        height: 1,
        config: {
          time_range: { type: 'dynamic', value: 'last_90_days' },
          filters: { type: 'expense' },
          granularity: 'week',
          group_by: 'none',
          aggregation: 'sum'
        }
      })

      // Load the newly created dashboard with its widgets as currentDashboard
      await fetchDashboard(newDashboard.id)
    } finally {
      _ensureStarterInFlight = false
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Refresh from DB (post-sync)
  // ---------------------------------------------------------------------------

  /**
   * Re-read dashboards from IndexedDB without an API call.
   * Called after sync completes to reflect any server-side changes that were
   * pulled into Dexie by the SyncManager.
   */
  async function refreshFromDB() {
    try {
      const data = await db.dashboards.toArray()
      dashboards.value = data as LocalDashboard[]

      // Also refresh currentDashboard so widget IDs match the server state.
      // Without this, after fullReadSync the store may hold stale IDs from the
      // previous session, causing updateWidget/deleteWidget calls to 404.
      if (currentDashboard.value) {
        const freshWidgets = await db.dashboardWidgets
          .where('dashboard_id')
          .equals(currentDashboard.value.id)
          .toArray()
        const freshDash = data.find(d => d.id === currentDashboard.value!.id)
        if (freshDash) {
          currentDashboard.value = {
            ...freshDash,
            widgets: freshWidgets as LocalDashboardWidget[]
          }
        }
      }
    } catch (err) {
      console.warn('[dashboards store] refreshFromDB failed:', err)
    }
  }

  // ---------------------------------------------------------------------------
  // Expose
  // ---------------------------------------------------------------------------

  return {
    // State
    dashboards,
    currentDashboard,
    loading,
    error,
    // Actions
    fetchDashboards,
    fetchDashboard,
    createDashboard,
    updateDashboard,
    deleteDashboard,
    createWidget,
    updateWidget,
    deleteWidget,
    ensureStarterDashboard,
    refreshFromDB
  }
})
