import { handlerRegistry } from '../handler-registry'
import { db } from '../db'
import { accountsApi } from '@/api/accounts'
import type { PendingMutation } from '../types'
import type { Account, CreateAccountDto, UpdateAccountDto } from '@/types'

const accountHandler = {
  async create(_mutation: PendingMutation, payload: Record<string, unknown>): Promise<Account> {
    const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return accountsApi.create(createPayload as unknown as CreateAccountDto)
  },

  async update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<Account> {
    const entity = await db.accounts.get(mutation.entity_id)
    const localUpdatedAt = entity?._local_updated_at ?? new Date().toISOString()
    void localUpdatedAt

    const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return accountsApi.update(mutation.entity_id, updatePayload as unknown as UpdateAccountDto)
  },

  async delete(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<Account> {
    await accountsApi.delete(mutation.entity_id)
    return { id: mutation.entity_id } as Account
  },

  async delete_permanent(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<Account> {
    await accountsApi.hardDelete(mutation.entity_id)
    return { id: mutation.entity_id } as Account
  },
}

handlerRegistry.register('account', accountHandler)
