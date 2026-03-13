/**
 * Dashboards Store
 *
 * Manages the state for user-defined analytics dashboards and their widgets.
 * Follows the same offline-first patterns as the accounts store, but with a
 * key difference: write operations (create/update/delete) use direct API calls
 * rather than the mutation queue. Dashboards are configuration data, not
 * financial records — they don't need offline-first write semantics because
 * the user is configuring an analytics view, which inherently requires
 * connectivity to be useful.
 *
 * Read operations still follow stale-while-revalidate: IndexedDB is read
 * first for instant cold-start, then the API is fetched in the background.
 *
 * ensureStarterDashboard() is called on first visit to /analytics and creates
 * a default dashboard with 3 expense widgets if the user has none.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardsApi } from '@/api/dashboards'
import { db } from '@/offline'
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
   * Create a new dashboard via the API, then persist to Dexie and update state.
   * Defaults display_currency to the user's primaryCurrency if not provided.
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
      const created = await dashboardsApi.create(payload)
      const now = new Date().toISOString()
      const localDash: LocalDashboard = {
        ...created,
        _sync_status: 'synced',
        _local_updated_at: now
      }
      await db.dashboards.put(localDash)
      dashboards.value.push(localDash)
      return created
    } catch (err: any) {
      error.value = err.message || 'Error al crear dashboard'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update an existing dashboard via the API, then update Dexie and state.
   */
  async function updateDashboard(id: string, dto: UpdateDashboardDto) {
    loading.value = true
    error.value = null
    try {
      const updated = await dashboardsApi.update(id, dto)
      const now = new Date().toISOString()
      const localDash: LocalDashboard = {
        ...updated,
        _sync_status: 'synced',
        _local_updated_at: now
      }
      await db.dashboards.put(localDash)

      // Update in dashboards list
      const idx = dashboards.value.findIndex(d => d.id === id)
      if (idx >= 0) {
        dashboards.value[idx] = localDash
      }

      // Update currentDashboard if it's the one being edited
      if (currentDashboard.value?.id === id) {
        currentDashboard.value = {
          ...localDash,
          widgets: currentDashboard.value.widgets
        }
      }

      return updated
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar dashboard'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a dashboard via the API, then remove from Dexie and state.
   * Also deletes all widgets belonging to the dashboard from Dexie.
   */
  async function deleteDashboard(id: string) {
    loading.value = true
    error.value = null
    try {
      await dashboardsApi.delete(id)

      // Remove dashboard from Dexie
      await db.dashboards.delete(id)

      // Remove all widgets for this dashboard from Dexie
      const widgetIds = await db.dashboardWidgets
        .where('dashboard_id')
        .equals(id)
        .primaryKeys()
      if (widgetIds.length > 0) {
        await db.dashboardWidgets.bulkDelete(widgetIds)
      }

      // Update reactive state
      dashboards.value = dashboards.value.filter(d => d.id !== id)
      if (currentDashboard.value?.id === id) {
        currentDashboard.value = null
      }
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar dashboard'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Widget CRUD (direct API calls)
  // ---------------------------------------------------------------------------

  /**
   * Create a widget in a dashboard via the API, persist to Dexie, add to state.
   */
  async function createWidget(dashboardId: string, dto: CreateWidgetDto) {
    loading.value = true
    error.value = null
    try {
      const created = await dashboardsApi.createWidget(dashboardId, dto)
      const now = new Date().toISOString()
      const localWidget: LocalDashboardWidget = {
        ...created,
        _sync_status: 'synced',
        _local_updated_at: now
      }
      await db.dashboardWidgets.put(localWidget)

      // Add to currentDashboard if it matches
      if (currentDashboard.value?.id === dashboardId) {
        currentDashboard.value = {
          ...currentDashboard.value,
          widgets: [...currentDashboard.value.widgets, localWidget]
        }
      }

      return created
    } catch (err: any) {
      error.value = err.message || 'Error al crear widget'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update a widget via the API, persist to Dexie, update in state.
   */
  async function updateWidget(dashboardId: string, widgetId: string, dto: UpdateWidgetDto) {
    loading.value = true
    error.value = null
    try {
      const updated = await dashboardsApi.updateWidget(dashboardId, widgetId, dto)
      const now = new Date().toISOString()
      const localWidget: LocalDashboardWidget = {
        ...updated,
        _sync_status: 'synced',
        _local_updated_at: now
      }
      await db.dashboardWidgets.put(localWidget)

      // Update in currentDashboard if it matches
      if (currentDashboard.value?.id === dashboardId) {
        const widgetIdx = currentDashboard.value.widgets.findIndex(w => w.id === widgetId)
        if (widgetIdx >= 0) {
          const newWidgets = [...currentDashboard.value.widgets]
          newWidgets[widgetIdx] = localWidget
          currentDashboard.value = {
            ...currentDashboard.value,
            widgets: newWidgets
          }
        }
      }

      return updated
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar widget'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a widget via the API, remove from Dexie, remove from state.
   */
  async function deleteWidget(dashboardId: string, widgetId: string) {
    loading.value = true
    error.value = null
    try {
      await dashboardsApi.deleteWidget(dashboardId, widgetId)
      await db.dashboardWidgets.delete(widgetId)

      // Remove from currentDashboard if it matches
      if (currentDashboard.value?.id === dashboardId) {
        const filteredWidgets = currentDashboard.value.widgets.filter(w => w.id !== widgetId)
        currentDashboard.value = {
          ...currentDashboard.value,
          widgets: filteredWidgets as LocalDashboardWidget[]
        }
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
    const data = await db.dashboards.toArray()
    dashboards.value = data as LocalDashboard[]
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
