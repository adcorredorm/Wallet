export type RecurringFrequency = 'daily' | 'weekly' | 'monthly' | 'yearly'
export type RecurringRuleStatus = 'active' | 'paused' | 'completed'

export interface RecurringRule {
  id: string
  offline_id?: string
  title: string
  type: 'income' | 'expense'
  amount: number
  account_id: string
  category_id: string
  description?: string | null
  tags: string[]
  requires_confirmation: boolean
  frequency: RecurringFrequency
  interval: number
  day_of_week?: number | null   // 0-6, for weekly
  day_of_month?: number | null  // 1-31, for monthly/yearly
  start_date: string            // YYYY-MM-DD
  end_date?: string | null      // YYYY-MM-DD
  max_occurrences?: number | null
  occurrences_created: number
  next_occurrence_date: string  // YYYY-MM-DD
  status: RecurringRuleStatus
  created_at: string
  updated_at: string
}

export interface CreateRecurringRuleDto {
  offline_id?: string
  title: string
  type: 'income' | 'expense'
  amount: number
  account_id: string
  category_id: string
  description?: string | null
  tags?: string[]
  requires_confirmation?: boolean
  frequency: RecurringFrequency
  interval?: number
  day_of_week?: number | null
  day_of_month?: number | null
  start_date: string
  end_date?: string | null
  max_occurrences?: number | null
  next_occurrence_date: string
  status?: RecurringRuleStatus
}

export interface UpdateRecurringRuleDto {
  title?: string
  amount?: number
  account_id?: string
  category_id?: string
  description?: string | null
  tags?: string[]
  requires_confirmation?: boolean
  frequency?: RecurringFrequency
  interval?: number
  day_of_week?: number | null
  day_of_month?: number | null
  end_date?: string | null
  max_occurrences?: number | null
  next_occurrence_date?: string
  occurrences_created?: number
  status?: RecurringRuleStatus
}
