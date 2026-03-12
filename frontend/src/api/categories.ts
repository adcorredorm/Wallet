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
  getAll(type?: CategoryType): Promise<Category[]> {
    const params = type ? { type } : {}
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
   * Delete a category
   * @param id - Category UUID
   */
  delete(id: string): Promise<void> {
    return apiClient.delete(`/categories/${id}`)
  }
}
