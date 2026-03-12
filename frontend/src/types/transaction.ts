/**
 * Transaction type definitions
 * Represents income and expense transactions
 */

export enum TransactionType {
  INCOME = 'income',
  EXPENSE = 'expense'
}

export interface Transaction {
  id: string
  type: TransactionType
  amount: number
  date: string  // ISO date string (YYYY-MM-DD)
  account_id: string
  category_id: string
  title?: string
  description?: string
  tags: string[]
  created_at: string
  updated_at: string
  // Populated relations (optional, depends on API response)
  account?: {
    name: string
    currency: string
  }
  category?: {
    name: string
    icon?: string
    color?: string
  }
}

export interface CreateTransactionDto {
  type: TransactionType
  amount: number
  date: string
  account_id: string
  category_id: string
  title?: string
  description?: string
  tags?: string[]
}

export interface UpdateTransactionDto {
  type?: TransactionType
  amount?: number
  date?: string
  account_id?: string
  category_id?: string
  title?: string
  description?: string
  tags?: string[]
}

export interface TransactionFilters {
  account_id?: string
  category_id?: string
  type?: TransactionType
  date_from?: string
  date_to?: string
  tags?: string[]
  limit?: number
  offset?: number
}
