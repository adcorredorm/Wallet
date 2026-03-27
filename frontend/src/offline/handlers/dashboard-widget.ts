import { handlerRegistry } from '../handler-registry'
import { dashboardsApi } from '@/api/dashboards'
import type { PendingMutation } from '../types'
import type { DashboardWidget, CreateWidgetDto, UpdateWidgetDto } from '@/types/dashboard'

const dashboardWidgetHandler = {
  async create(mutation: PendingMutation, payload: Record<string, unknown>): Promise<DashboardWidget> {
    const dashboardId = payload['dashboard_id'] as string | undefined
    if (!dashboardId) throw new Error(`[dashboard-widget handler] missing dashboard_id in payload for entity ${mutation.entity_id}`)

    const { id: _id, dashboard_id: _did, ...createPayload } =
      payload as Record<string, unknown> & { id?: string; dashboard_id?: string }
    void _id
    void _did
    return dashboardsApi.createWidget(dashboardId, createPayload as unknown as CreateWidgetDto)
  },

  async update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<DashboardWidget> {
    const dashboardId = payload['dashboard_id'] as string | undefined
    if (!dashboardId) throw new Error(`[dashboard-widget handler] missing dashboard_id in payload for entity ${mutation.entity_id}`)

    const { id: _id, dashboard_id: _did, ...updatePayload } =
      payload as Record<string, unknown> & { id?: string; dashboard_id?: string }
    void _id
    void _did
    return dashboardsApi.updateWidget(dashboardId, mutation.entity_id, updatePayload as unknown as UpdateWidgetDto)
  },

  async delete(mutation: PendingMutation, payload: Record<string, unknown>): Promise<DashboardWidget> {
    const dashboardId = payload['dashboard_id'] as string | undefined
    if (!dashboardId) throw new Error(`[dashboard-widget handler] missing dashboard_id in payload for entity ${mutation.entity_id}`)

    await dashboardsApi.deleteWidget(dashboardId, mutation.entity_id)
    return { id: mutation.entity_id } as DashboardWidget
  },

  async delete_permanent(_mutation: PendingMutation, _payload: Record<string, unknown>): Promise<unknown> {
    throw new Error('delete_permanent not supported for dashboard_widget')
  },
}

handlerRegistry.register('dashboard_widget', dashboardWidgetHandler)
