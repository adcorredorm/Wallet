import { handlerRegistry } from '../handler-registry'
import { dashboardsApi } from '@/api/dashboards'
import type { PendingMutation } from '../types'
import type { Dashboard, CreateDashboardDto, UpdateDashboardDto } from '@/types/dashboard'

const dashboardHandler = {
  async create(_mutation: PendingMutation, payload: Record<string, unknown>): Promise<Dashboard> {
    const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return dashboardsApi.create(createPayload as unknown as CreateDashboardDto)
  },

  async update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<Dashboard> {
    const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return dashboardsApi.update(mutation.entity_id, updatePayload as unknown as UpdateDashboardDto)
  },

  async delete(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<Dashboard> {
    await dashboardsApi.delete(mutation.entity_id)
    return { id: mutation.entity_id } as Dashboard
  },

  async delete_permanent(_mutation: PendingMutation, _payload: Record<string, unknown>): Promise<unknown> {
    throw new Error('delete_permanent not supported for dashboard')
  },
}

handlerRegistry.register('dashboard', dashboardHandler)
