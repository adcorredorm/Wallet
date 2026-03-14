/**
 * Categories API Client
 * Handles all HTTP requests related to transaction categories
 */

import apiClient from './index'
import type { Category, CreateCategoryDto, UpdateCategoryDto, CategoryType } from '@/types'

export const categoriesApi = {
  /**
   * Get all categories
   * @param tipo - Filter by category type (optional)
   */
  getAll(type?: CategoryType, includeArchived = false): Promise<Category[]> {
    const params: Record<string, unknown> = {}
    if (type) params.type = type
    if (includeArchived) params.include_archived = true
    return apiClient.get('/categories', { params })
  },

  /**
   * Get a single category by ID
   * @param id - Category UUID
   */
  getById(id: string): Promise<Category> {
    return apiClient.get(`/categories/${id}`)
  },

  /**
   * Get subcategories of a parent category
   * @param parentId - Parent category UUID
   */
  getSubcategories(parentId: string): Promise<Category[]> {
    return apiClient.get(`/categories/${parentId}/subcategories`)
  },

  /**
   * Create a new category
   * @param data - Category creation data
   */
  create(data: CreateCategoryDto): Promise<Category> {
    return apiClient.post('/categories', data)
  },

  /**
   * Update an existing category
   * @param id - Category UUID
   * @param data - Category update data
   */
  update(id: string, data: UpdateCategoryDto): Promise<Category> {
    return apiClient.put(`/categories/${id}`, data)
  },

  /**
   * Archive a category (soft delete - sets active to false)
   * @param id - Category UUID
   */
  archive(id: string): Promise<void> {
    return apiClient.delete(`/categories/${id}`)
  },

  /**
   * Delete a category (soft delete - sets active to false)
   * Alias for archive() kept for backward compatibility
   * @param id - Category UUID
   */
  delete(id: string): Promise<void> {
    return apiClient.delete(`/categories/${id}`)
  },

  /**
   * Permanently delete a category (hard delete - removes from database)
   * @param id - Category UUID
   */
  hardDelete(id: string): Promise<void> {
    return apiClient.delete(`/categories/${id}/permanent`)
  }
}
