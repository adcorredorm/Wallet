import { handlerRegistry } from '../handler-registry'
import { transfersApi } from '@/api/transfers'
import type { PendingMutation } from '../types'
import type { Transfer, CreateTransferDto, UpdateTransferDto } from '@/types'

const transferHandler = {
  async create(_mutation: PendingMutation, payload: Record<string, unknown>): Promise<Transfer> {
    const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return transfersApi.create(createPayload as unknown as CreateTransferDto)
  },

  async update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<Transfer> {
    const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return transfersApi.update(mutation.entity_id, updatePayload as unknown as UpdateTransferDto)
  },

  async delete(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<Transfer> {
    await transfersApi.delete(mutation.entity_id)
    return { id: mutation.entity_id } as Transfer
  },

  async delete_permanent(_mutation: PendingMutation, _payload: Record<string, unknown>): Promise<unknown> {
    throw new Error('delete_permanent not supported for transfer')
  },
}

handlerRegistry.register('transfer', transferHandler)
