/**
 * Account type definitions
 * Represents financial accounts (debit, credit, cash)
 */

export enum AccountType {
  DEBIT = 'debit',
  CREDIT = 'credit',
  CASH = 'cash'
}

export interface Account {
  id: string
  name: string
  type: AccountType
  currency: string  // ISO 4217 currency code (EUR, USD, etc)
  description?: string
  tags: string[]
  active: boolean
  sort_order: number
  icon?: string
  balance?: number  // Calculated balance (included in list response)
  created_at: string
  updated_at: string
}

export interface AccountBalance {
  account_id: string
  balance: number
  currency: string
}

export interface CreateAccountDto {
  name: string
  type: AccountType
  currency: string
  description?: string
  tags?: string[]
  sort_order?: number
  icon?: string
}

export interface UpdateAccountDto {
  name?: string
  type?: AccountType
  currency?: string
  description?: string
  tags?: string[]
  active?: boolean
  sort_order?: number
  icon?: string
}
