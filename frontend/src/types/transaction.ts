/**
 * Transaction type definitions
 * Represents income and expense transactions
 */

export enum TransactionType {
  INGRESO = 'ingreso',
  GASTO = 'gasto'
}

export interface Transaction {
  id: string
  tipo: TransactionType
  monto: number
  fecha: string  // ISO date string (YYYY-MM-DD)
  cuenta_id: string
  categoria_id: string
  titulo?: string
  descripcion?: string
  tags: string[]
  created_at: string
  updated_at: string
  // Populated relations (optional, depends on API response)
  cuenta?: {
    nombre: string
    divisa: string
  }
  categoria?: {
    nombre: string
    icono?: string
    color?: string
  }
}

export interface CreateTransactionDto {
  tipo: TransactionType
  monto: number
  fecha: string
  cuenta_id: string
  categoria_id: string
  titulo?: string
  descripcion?: string
  tags?: string[]
}

export interface UpdateTransactionDto {
  tipo?: TransactionType
  monto?: number
  fecha?: string
  cuenta_id?: string
  categoria_id?: string
  titulo?: string
  descripcion?: string
  tags?: string[]
}

export interface TransactionFilters {
  cuenta_id?: string
  categoria_id?: string
  tipo?: TransactionType
  fecha_inicio?: string
  fecha_fin?: string
  tags?: string[]
  limit?: number
  offset?: number
}
