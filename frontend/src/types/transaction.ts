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
  base_rate?: number  // Units of primaryCurrency per 1 unit of account.currency at transaction time
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
  // Multi-currency fields (null when no foreign currency involved)
  original_amount?: number | null
  original_currency?: string | null
  exchange_rate?: number | null
  base_rate?: number  // Captured at write time; null when offline with no cached rates
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
  // Multi-currency fields (null when no foreign currency involved)
  original_amount?: number | null
  original_currency?: string | null
  exchange_rate?: number | null
  base_rate?: number
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
