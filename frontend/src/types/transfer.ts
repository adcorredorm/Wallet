/**
 * Transfer type definitions
 * Represents money transfers between accounts
 */

export interface Transfer {
  id: string
  cuenta_origen_id: string
  cuenta_destino_id: string
  monto: number
  fecha: string  // ISO date string (YYYY-MM-DD)
  titulo?: string
  descripcion?: string
  tags: string[]
  created_at: string
  updated_at: string
  // Populated relations (optional, depends on API response)
  cuenta_origen?: {
    nombre: string
    divisa: string
  }
  cuenta_destino?: {
    nombre: string
    divisa: string
  }
}

export interface CreateTransferDto {
  cuenta_origen_id: string
  cuenta_destino_id: string
  monto: number
  fecha: string
  titulo?: string
  descripcion?: string
  tags?: string[]
}

export interface UpdateTransferDto {
  cuenta_origen_id?: string
  cuenta_destino_id?: string
  monto?: number
  fecha?: string
  titulo?: string
  descripcion?: string
  tags?: string[]
}

export interface TransferFilters {
  cuenta_id?: string  // Filter by either source or destination
  fecha_inicio?: string
  fecha_fin?: string
  limit?: number
  offset?: number
}
