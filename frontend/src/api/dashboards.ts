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
  /**
   * Get all dashboards
   */
  getAll(): Promise<Dashboard[]> {
    return apiClient.get('/dashboards')
  },

  /**
   * Get a single dashboard with all its widgets
   * @param id - Dashboard UUID
   */
  getById(id: string): Promise<DashboardWithWidgets> {
    return apiClient.get(`/dashboards/${id}`)
  },

  /**
   * Create a new dashboard
   * @param dto - Dashboard creation data
   */
  create(dto: CreateDashboardDto): Promise<Dashboard> {
    return apiClient.post('/dashboards', dto)
  },

  /**
   * Update an existing dashboard
   * @param id - Dashboard UUID
   * @param dto - Dashboard update data
   */
  update(id: string, dto: UpdateDashboardDto): Promise<Dashboard> {
    return apiClient.put(`/dashboards/${id}`, dto)
  },

  /**
   * Delete a dashboard
   * @param id - Dashboard UUID
   */
  delete(id: string): Promise<void> {
    return apiClient.delete(`/dashboards/${id}`)
  },

  /**
   * Create a new widget in a dashboard
   * @param dashboardId - UUID of the owning dashboard
   * @param dto - Widget creation data
   */
  createWidget(dashboardId: string, dto: CreateWidgetDto): Promise<DashboardWidget> {
    return apiClient.post(`/dashboards/${dashboardId}/widgets`, dto)
  },

  /**
   * Update a widget's config or layout
   * @param dashboardId - UUID of the owning dashboard
   * @param widgetId - UUID of the widget
   * @param dto - Widget update data
   */
  updateWidget(dashboardId: string, widgetId: string, dto: UpdateWidgetDto): Promise<DashboardWidget> {
    return apiClient.put(`/dashboards/${dashboardId}/widgets/${widgetId}`, dto)
  },

  /**
   * Delete a widget from a dashboard
   * @param dashboardId - UUID of the owning dashboard
   * @param widgetId - UUID of the widget
   */
  deleteWidget(dashboardId: string, widgetId: string): Promise<void> {
    return apiClient.delete(`/dashboards/${dashboardId}/widgets/${widgetId}`)
  }
}
