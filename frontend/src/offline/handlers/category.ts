import { handlerRegistry } from '../handler-registry'
import { categoriesApi } from '@/api/categories'
import type { PendingMutation } from '../types'
import type { Category, CreateCategoryDto, UpdateCategoryDto } from '@/types'

const categoryHandler = {
  async create(_mutation: PendingMutation, payload: Record<string, unknown>): Promise<Category> {
    const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return categoriesApi.create(createPayload as unknown as CreateCategoryDto)
  },

  async update(mutation: PendingMutation, payload: Record<string, unknown>): Promise<Category> {
    const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
    void _id
    return categoriesApi.update(mutation.entity_id, updatePayload as unknown as UpdateCategoryDto)
  },

  async delete(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<Category> {
    await categoriesApi.delete(mutation.entity_id)
    return { id: mutation.entity_id } as Category
  },

  async delete_permanent(mutation: PendingMutation, _payload: Record<string, unknown>): Promise<Category> {
    await categoriesApi.hardDelete(mutation.entity_id)
    return { id: mutation.entity_id } as Category
  },
}

handlerRegistry.register('category', categoryHandler)
