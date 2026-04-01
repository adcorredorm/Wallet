// frontend/src/offline/handlers/budget.ts
import { handlerRegistry } from '../handler-registry'
import { budgetsApi } from '@/api/budgets'
import type { PendingMutation } from '../types'
import type { Budget, CreateBudgetDto, UpdateBudgetDto } from '@/types/budget'

const budgetHandler = {
  async create(_mutation: PendingMutation, payload: Record<string, unknown>): Promise<Budget> {
    const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return budgetsApi.create(createPayload as unknown as CreateBudgetDto)
  },

  async update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<Budget> {
    const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return budgetsApi.update(mutation.entity_id, updatePayload as unknown as UpdateBudgetDto)
  },

  async delete(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<{ id: string }> {
    await budgetsApi.delete(mutation.entity_id)
    return { id: mutation.entity_id }
  },

  async delete_permanent(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<{ id: string }> {
    await budgetsApi.hardDelete(mutation.entity_id)
    return { id: mutation.entity_id }
  },
}

handlerRegistry.register('budget', budgetHandler)
