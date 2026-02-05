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
  patrimonio_neto: number
  cuentas: Array<{
    id: string
    nombre: string
    balance: number
    divisa: string
  }>
  transacciones_recientes: any[]
  resumen_mensual?: {
    ingresos: number
    gastos: number
    balance: number
  }
}
