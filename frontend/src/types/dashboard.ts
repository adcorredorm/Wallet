/**
 * Dashboard and widget type definitions for the customizable analytics feature.
 * display_currency lives on Dashboard, not on individual widgets or WidgetConfig.
 */

/** Widget visualization types */
export type WidgetType = 'line' | 'pie' | 'bar' | 'stacked_bar' | 'number'

/** Dynamic time range presets */
export type DynamicTimeRange =
  | 'last_7_days'
  | 'last_30_days'
  | 'last_90_days'
  | 'this_month'
  | 'last_month'
  | 'this_quarter'
  | 'this_year'
  | 'last_year'
  | 'all_time'

/** Time range configuration — dynamic preset or static date range */
export type TimeRange =
  | { type: 'dynamic'; value: DynamicTimeRange }
  | { type: 'static'; value: { from: string; to: string } }

/** Granularity for time-series data */
export type AnalyticsGranularity = 'day' | 'week' | 'month' | 'quarter' | 'semester' | 'year'

/** Grouping dimension */
export type GroupBy = 'category' | 'account' | 'type' | 'day_of_week' | 'none'

/** Aggregation function */
export type Aggregation = 'sum' | 'avg' | 'count' | 'min' | 'max'

/** Filter criteria for an analytics query */
export interface AnalyticsFilters {
  account_ids?: string[]
  category_ids?: string[]
  type?: 'income' | 'expense'
  amount_min?: number
  amount_max?: number
}

/**
 * Widget configuration stored in JSONB.
 * display_currency is NOT here — it lives on Dashboard and applies to all widgets.
 */
export interface WidgetConfig {
  time_range: TimeRange
  filters: AnalyticsFilters
  granularity: AnalyticsGranularity
  group_by: GroupBy
  aggregation: Aggregation
  category_groups?: Record<string, string[]>
}

/** Dashboard entity */
export interface Dashboard {
  id: string
  client_id?: string
  name: string
  description?: string | null
  /** ISO 4217 currency code — applies to all widgets in this dashboard */
  display_currency: string
  layout_columns: number
  is_default: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

/** Dashboard with nested widgets (returned by GET /dashboards/:id) */
export interface DashboardWithWidgets extends Dashboard {
  widgets: DashboardWidget[]
}

/** Dashboard widget entity */
export interface DashboardWidget {
  id: string
  client_id?: string
  dashboard_id: string
  widget_type: WidgetType
  title: string
  position_x: number
  position_y: number
  width: number
  height: number
  config: WidgetConfig
  created_at: string
  updated_at: string
}

/** DTO for creating a dashboard */
export interface CreateDashboardDto {
  client_id?: string
  name: string
  description?: string | null
  /** Required — UI should default to user's primaryCurrency */
  display_currency: string
  layout_columns?: number
  is_default?: boolean
  sort_order?: number
}

/** DTO for updating a dashboard */
export interface UpdateDashboardDto {
  name?: string
  description?: string | null
  display_currency?: string
  layout_columns?: number
  is_default?: boolean
  sort_order?: number
}

/** DTO for creating a widget */
export interface CreateWidgetDto {
  client_id?: string
  widget_type: WidgetType
  title: string
  position_x?: number
  position_y?: number
  width?: number
  height?: number
  config: WidgetConfig
}

/** DTO for updating a widget */
export interface UpdateWidgetDto {
  widget_type?: WidgetType  // changing chart type is allowed when editing
  title?: string
  position_x?: number
  position_y?: number
  width?: number
  height?: number
  config?: WidgetConfig
}

/** A single dataset in the analytics result */
export interface AnalyticsDataset {
  label: string
  data: number[]
}

/** Analytics computation result — returned by useWidgetData composable */
export interface AnalyticsResult {
  labels: string[]
  datasets: AnalyticsDataset[]
  totals: Record<string, number>
  metadata: {
    date_from: string
    date_to: string
    granularity: AnalyticsGranularity
    display_currency: string
  }
}
