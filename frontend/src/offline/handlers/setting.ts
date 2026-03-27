import { handlerRegistry } from '../handler-registry'
import type { PendingMutation } from '../types'

const settingHandler = {
  async create(_mutation: PendingMutation, _payload: Record<string, unknown>): Promise<unknown> {
    throw new Error('create not supported for setting — settings use upsert (update)')
  },

  async update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<{ id: string; updated_at?: string }> {
    const { updateSetting } = await import('@/api/settings')
    const key = payload['key'] as string ?? mutation.entity_id
    const value = payload['value']
    await updateSetting(key, value)
    return { id: key, updated_at: new Date().toISOString() }
  },

  async delete(_mutation: PendingMutation, _payload: Record<string, unknown>): Promise<unknown> {
    throw new Error('delete not supported for setting')
  },
}

handlerRegistry.register('setting', settingHandler)
