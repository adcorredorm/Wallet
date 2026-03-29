/**
 * Recurring Rules API Client
 * Handles HTTP requests for recurring transaction rules.
 */

import apiClient from './index'
import type { RecurringRule, CreateRecurringRuleDto, UpdateRecurringRuleDto } from '@/types/recurring-rule'

export const recurringRulesApi = {
  list(): Promise<RecurringRule[]> {
    return apiClient.get('/recurring-rules?limit=10000')
  },

  create(data: CreateRecurringRuleDto): Promise<RecurringRule> {
    return apiClient.post('/recurring-rules', data)
  },

  update(id: string, data: UpdateRecurringRuleDto): Promise<RecurringRule> {
    return apiClient.patch(`/recurring-rules/${id}`, data)
  },

  delete(id: string): Promise<void> {
    return apiClient.delete(`/recurring-rules/${id}`)
  },
}
