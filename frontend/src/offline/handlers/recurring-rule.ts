import { handlerRegistry } from '../handler-registry'
import { recurringRulesApi } from '@/api/recurring-rules'
import type { PendingMutation } from '../types'
import type { RecurringRule, CreateRecurringRuleDto, UpdateRecurringRuleDto } from '@/types/recurring-rule'

const recurringRuleHandler = {
  async create(_mutation: PendingMutation, payload: Record<string, unknown>): Promise<RecurringRule> {
    const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return recurringRulesApi.create(createPayload as unknown as CreateRecurringRuleDto)
  },

  async update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<RecurringRule> {
    const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return recurringRulesApi.update(mutation.entity_id, updatePayload as unknown as UpdateRecurringRuleDto)
  },

  async delete(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<RecurringRule> {
    await recurringRulesApi.delete(mutation.entity_id)
    return { id: mutation.entity_id } as RecurringRule
  },

  async delete_permanent(_mutation: PendingMutation, _payload: Record<string, unknown>): Promise<unknown> {
    throw new Error('delete_permanent not supported for recurring_rule')
  },
}

handlerRegistry.register('recurring_rule', recurringRuleHandler)
