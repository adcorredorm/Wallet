// frontend/src/types/budget.ts

export type BudgetType = 'recurring' | 'one_time'
export type BudgetStatus = 'active' | 'paused' | 'archived'
export type BudgetFrequency = 'daily' | 'weekly' | 'monthly' | 'yearly'

export interface Budget {
  id: string
  offline_id?: string
  name: string
  account_id: string | null
  category_id: string | null
  amount_limit: number
  currency: string
  budget_type: BudgetType
  frequency?: BudgetFrequency | null
  interval?: number
  reference_date?: string | null   // YYYY-MM-DD
  start_date?: string | null       // YYYY-MM-DD
  end_date?: string | null         // YYYY-MM-DD
  status: BudgetStatus
  icon?: string | null
  color?: string | null
  created_at: string
  updated_at: string
}

export interface CreateBudgetDto {
  offline_id?: string
  name: string
  account_id?: string | null
  category_id?: string | null
  amount_limit: number
  currency: string
  budget_type: BudgetType
  frequency?: BudgetFrequency | null
  interval?: number
  reference_date?: string | null
  start_date?: string | null
  end_date?: string | null
  status?: BudgetStatus
  icon?: string | null
  color?: string | null
}

export interface UpdateBudgetDto {
  name?: string
  amount_limit?: number
  currency?: string
  frequency?: BudgetFrequency | null
  interval?: number
  reference_date?: string | null
  start_date?: string | null
  end_date?: string | null
  status?: BudgetStatus
  icon?: string | null
  color?: string | null
}
