/**
 * Transfer type definitions
 * Represents money transfers between accounts
 */

export interface Transfer {
  id: string
  source_account_id: string
  destination_account_id: string
  amount: number
  date: string  // ISO date string (YYYY-MM-DD)
  title?: string
  description?: string
  tags: string[]
  created_at: string
  updated_at: string
  // Populated relations (optional, depends on API response)
  source_account?: {
    name: string
    currency: string
  }
  destination_account?: {
    name: string
    currency: string
  }
}

export interface CreateTransferDto {
  source_account_id: string
  destination_account_id: string
  amount: number
  date: string
  title?: string
  description?: string
  tags?: string[]
}

export interface UpdateTransferDto {
  source_account_id?: string
  destination_account_id?: string
  amount?: number
  date?: string
  title?: string
  description?: string
  tags?: string[]
}

export interface TransferFilters {
  account_id?: string  // Filter by either source or destination
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}
