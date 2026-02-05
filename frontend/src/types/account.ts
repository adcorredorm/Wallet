/**
 * Account type definitions
 * Represents financial accounts (debit, credit, cash)
 */

export enum AccountType {
  DEBITO = 'debito',
  CREDITO = 'credito',
  EFECTIVO = 'efectivo'
}

export interface Account {
  id: string
  nombre: string
  tipo: AccountType
  divisa: string  // ISO 4217 currency code (EUR, USD, etc)
  descripcion?: string
  tags: string[]
  activa: boolean
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
  nombre: string
  tipo: AccountType
  divisa: string
  descripcion?: string
  tags?: string[]
}

export interface UpdateAccountDto {
  nombre?: string
  tipo?: AccountType
  divisa?: string
  descripcion?: string
  tags?: string[]
  activa?: boolean
}
