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
  // Cross-currency fields — present for FX transfers, absent for same-currency
  destination_amount?: number   // Amount credited to the destination account
  exchange_rate?: number        // FX rate applied at transfer time
  destination_currency?: string // ISO 4217 code of the destination account's currency
  base_rate?: number     // Units of primaryCurrency per 1 unit of source_account.currency at transfer time
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
  // Cross-currency fields — omitted for same-currency transfers
  destination_amount?: number   // Amount received in the destination account (may differ due to FX)
  exchange_rate?: number        // FX rate applied at the time of the transfer
  destination_currency?: string // ISO 4217 code of the destination account's currency
  base_rate?: number
}

export interface UpdateTransferDto {
  source_account_id?: string
  destination_account_id?: string
  amount?: number
  date?: string
  title?: string
  description?: string
  tags?: string[]
  // Cross-currency fields — omitted for same-currency transfers
  destination_amount?: number
  exchange_rate?: number
  destination_currency?: string
  base_rate?: number
}

export interface TransferFilters {
  account_id?: string  // Filter by either source or destination
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}
