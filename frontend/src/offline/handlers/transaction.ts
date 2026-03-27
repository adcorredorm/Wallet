import { handlerRegistry } from '../handler-registry'
import { transactionsApi } from '@/api/transactions'
import type { PendingMutation } from '../types'
import type { Transaction, CreateTransactionDto, UpdateTransactionDto } from '@/types'

const transactionHandler = {
  async create(_mutation: PendingMutation, payload: Record<string, unknown>): Promise<Transaction> {
    const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return transactionsApi.create(createPayload as unknown as CreateTransactionDto)
  },

  async update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<Transaction> {
    const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return transactionsApi.update(mutation.entity_id, updatePayload as unknown as UpdateTransactionDto)
  },

  async delete(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<Transaction> {
    await transactionsApi.delete(mutation.entity_id)
    return { id: mutation.entity_id } as Transaction
  },

  async delete_permanent(_mutation: PendingMutation, _payload: Record<string, unknown>): Promise<unknown> {
    throw new Error('delete_permanent not supported for transaction')
  },
}

handlerRegistry.register('transaction', transactionHandler)
