// frontend/src/api/budgets.ts
import apiClient from './index'
import type { Budget, CreateBudgetDto, UpdateBudgetDto } from '@/types/budget'

export const budgetsApi = {
  list(): Promise<Budget[]> {
    return apiClient.get('/budgets?limit=10000')
  },

  create(data: CreateBudgetDto): Promise<Budget> {
    return apiClient.post('/budgets', data)
  },

  update(id: string, data: UpdateBudgetDto): Promise<Budget> {
    return apiClient.patch(`/budgets/${id}`, data)
  },

  delete(id: string): Promise<void> {
    return apiClient.delete(`/budgets/${id}`)
  },

  hardDelete(id: string): Promise<void> {
    return apiClient.delete(`/budgets/${id}/permanent`)
  },
}
