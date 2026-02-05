/**
 * Categories Store
 *
 * Manages transaction categories with hierarchy support
 * - Parent/child category relationships
 * - Filter by type (ingreso, gasto, ambos)
 * - CRUD operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { categoriesApi } from '@/api/categories'
import type { Category, CreateCategoryDto, UpdateCategoryDto, CategoryType } from '@/types'

export const useCategoriesStore = defineStore('categories', () => {
  // State
  const categories = ref<Category[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const incomeCategories = computed(() =>
    categories.value.filter(cat =>
      cat.tipo === 'ingreso' || cat.tipo === 'ambos'
    )
  )

  const expenseCategories = computed(() =>
    categories.value.filter(cat =>
      cat.tipo === 'gasto' || cat.tipo === 'ambos'
    )
  )

  const parentCategories = computed(() =>
    categories.value.filter(cat => !cat.categoria_padre_id)
  )

  // Helper to get subcategories of a parent
  const getSubcategories = (parentId: string) =>
    categories.value.filter(cat => cat.categoria_padre_id === parentId)

  // Actions
  async function fetchCategories(tipo?: CategoryType) {
    // Reset error state at the start of each fetch
    // This ensures previous errors don't block new attempts
    error.value = null
    loading.value = true

    try {
      const fetchedCategories = await categoriesApi.getAll(tipo)
      categories.value = fetchedCategories
      return fetchedCategories
    } catch (err: any) {
      console.error('Categories store fetch error:', err)
      error.value = err.message || 'Error al cargar categorías'
      // Don't throw - let the component handle the error state
      // This prevents the error from bubbling up and breaking navigation
      return []
    } finally {
      loading.value = false
    }
  }

  async function fetchCategoryById(id: string) {
    loading.value = true
    error.value = null
    try {
      const category = await categoriesApi.getById(id)
      // Update or add to categories array
      const index = categories.value.findIndex(c => c.id === id)
      if (index >= 0) {
        categories.value[index] = category
      } else {
        categories.value.push(category)
      }
      return category
    } catch (err: any) {
      error.value = err.message || 'Error al cargar categoría'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createCategory(data: CreateCategoryDto) {
    loading.value = true
    error.value = null
    try {
      const newCategory = await categoriesApi.create(data)
      categories.value.push(newCategory)
      return newCategory
    } catch (err: any) {
      error.value = err.message || 'Error al crear categoría'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateCategory(id: string, data: UpdateCategoryDto) {
    loading.value = true
    error.value = null
    try {
      const updatedCategory = await categoriesApi.update(id, data)
      const index = categories.value.findIndex(c => c.id === id)
      if (index >= 0) {
        categories.value[index] = updatedCategory
      }
      return updatedCategory
    } catch (err: any) {
      error.value = err.message || 'Error al actualizar categoría'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteCategory(id: string) {
    loading.value = true
    error.value = null
    try {
      await categoriesApi.delete(id)
      categories.value = categories.value.filter(c => c.id !== id)
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar categoría'
      throw err
    } finally {
      loading.value = false
    }
  }

  function getCategoryById(id: string): Category | undefined {
    return categories.value.find(c => c.id === id)
  }

  return {
    // State
    categories,
    loading,
    error,
    // Computed
    incomeCategories,
    expenseCategories,
    parentCategories,
    // Actions
    fetchCategories,
    fetchCategoryById,
    createCategory,
    updateCategory,
    deleteCategory,
    getCategoryById,
    getSubcategories
  }
})
