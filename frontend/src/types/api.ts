/**
 * API response and error types
 * Standard response structure from Flask backend
 */

export interface ApiResponse<T = any> {
  data?: T
  message?: string
  success: boolean
  errors?: Record<string, string[]>
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface ApiError {
  message: string
  status: number
  errors?: Record<string, string[]>
}

// Dashboard specific types
export interface DashboardData {
  net_worth: number
  accounts: Array<{
    id: string
    name: string
    balance: number
    currency: string
  }>
  recent_transactions: any[]
  monthly_summary?: {
    income: number
    expenses: number
    balance: number
  }
}
