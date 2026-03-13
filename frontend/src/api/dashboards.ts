/**
 * Dashboards API Client
 * CRUD for user-defined analytics dashboards and their widgets.
 * The backend stores only configuration — analytics are computed locally from IndexedDB.
 */

import apiClient from './index'
import type {
  Dashboard,
  DashboardWithWidgets,
  CreateDashboardDto,
  UpdateDashboardDto,
  DashboardWidget,
  CreateWidgetDto,
  UpdateWidgetDto
} from '@/types/dashboard'

export const dashboardsApi = {
  getAll(): Promise<Dashboard[]> {
    return apiClient.get('/dashboards')
  },

  getById(id: string): Promise<DashboardWithWidgets> {
    return apiClient.get(`/dashboards/${id}`)
  },

  create(dto: CreateDashboardDto): Promise<Dashboard> {
    return apiClient.post('/dashboards', dto)
  },

  update(id: string, dto: UpdateDashboardDto): Promise<Dashboard> {
    return apiClient.put(`/dashboards/${id}`, dto)
  },

  delete(id: string): Promise<void> {
    return apiClient.delete(`/dashboards/${id}`)
  },

  createWidget(dashboardId: string, dto: CreateWidgetDto): Promise<DashboardWidget> {
    return apiClient.post(`/dashboards/${dashboardId}/widgets`, dto)
  },

  updateWidget(dashboardId: string, widgetId: string, dto: UpdateWidgetDto): Promise<DashboardWidget> {
    return apiClient.put(`/dashboards/${dashboardId}/widgets/${widgetId}`, dto)
  },

  deleteWidget(dashboardId: string, widgetId: string): Promise<void> {
    return apiClient.delete(`/dashboards/${dashboardId}/widgets/${widgetId}`)
  }
}
