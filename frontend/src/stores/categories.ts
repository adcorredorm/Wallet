/**
 * Categories Store
 *
 * Manages transaction categories with hierarchy support
 * - Parent/child category relationships
 * - Filter by type (income, expense, both)
 * - CRUD operations
 *
 * Phase 3 change: write actions now follow the offline-first pattern.
 * Writes go to IndexedDB and the mutation queue immediately; the UI updates
 * optimistically. The SyncManager (Phase 4) will flush to the server.
 *
 * Note on parent_category_id: if a user creates a parent category offline and
 * then creates a child category in the same session, parent_category_id in the
 * child's payload will be a temp-* ID. The SyncManager resolves it before the
 * network call, in FIFO order so the parent is created on the server first.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { categoriesApi } from '@/api/categories'
import { CategoryType } from '@/types/category'
import type { CreateCategoryDto, UpdateCategoryDto } from '@/types'
import { db, fetchAllWithRevalidation, fetchByIdWithRevalidation, generateTempId, mutationQueue } from '@/offline'
import type { LocalCategory } from '@/offline'

/**
 * CategoryGroup — a parent category with its direct children.
 * Used by categoryTree to present a grouped, 2-level hierarchy.
 */
export interface CategoryGroup {
  parent: LocalCategory
  children: LocalCategory[]
}

export const useCategoriesStore = defineStore('categories', () => {
  // State
  // Why LocalCategory[] instead of Category[]?
  // LocalCategory extends Category, so all consumers continue to work.
  const categories = ref<LocalCategory[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const incomeCategories = computed(() =>
    categories.value.filter(cat =>
      cat.type === 'income' || cat.type === 'both'
    )
  )

  const expenseCategories = computed(() =>
    categories.value.filter(cat =>
      cat.type === 'expense' || cat.type === 'both'
    )
  )

  const parentCategories = computed(() =>
    categories.value.filter(cat => !cat.parent_category_id)
  )

  // Helper to get subcategories of a parent
  const getSubcategories = (parentId: string) =>
    categories.value.filter(cat => cat.parent_category_id === parentId)

  /**
   * categoryTree — groups all categories into a 2-level hierarchy.
   *
   * Each CategoryGroup has a parent and its direct children.
   * Sorting: groups with children come first (alphabetical by name),
   * then standalone categories (no children, alphabetical by name).
   * Orphaned children (parent_id set but parent not in store) are treated
   * as standalone root entries.
   */
  const categoryTree = computed<CategoryGroup[]>(() => {
    const byId = new Map<string, LocalCategory>()
    for (const cat of categories.value) {
      byId.set(cat.id, cat)
    }

    // Identify root categories: no parent_category_id, or parent_category_id not found in store
    const roots: LocalCategory[] = []
    const childrenMap = new Map<string, LocalCategory[]>()

    for (const cat of categories.value) {
      if (!cat.parent_category_id || !byId.has(cat.parent_category_id)) {
        // This is a root (or an orphan treated as root)
        roots.push(cat)
      } else {
        // This is a valid child
        const parentId = cat.parent_category_id
        if (!childrenMap.has(parentId)) {
          childrenMap.set(parentId, [])
        }
        childrenMap.get(parentId)!.push(cat)
      }
    }

    // Build groups
    const groups: CategoryGroup[] = roots.map(root => ({
      parent: root,
      children: (childrenMap.get(root.id) ?? []).sort((a, b) =>
        a.name.localeCompare(b.name)
      )
    }))

    // Sort: groups with children first (alpha), then standalone (alpha)
    const withChildren = groups
      .filter(g => g.children.length > 0)
      .sort((a, b) => a.parent.name.localeCompare(b.parent.name))
    const standalone = groups
      .filter(g => g.children.length === 0)
      .sort((a, b) => a.parent.name.localeCompare(b.parent.name))

    return [...withChildren, ...standalone]
  })

  /**
   * compatibleParentCategories — returns root categories eligible as parents
   * for a category of the given type.
   *
   * Rules:
   * - Only root categories can be parents (no parent_category_id).
   *   This enforces the 2-level limit: a child cannot itself become a parent.
   * - A root category that already has children CAN still accept more children.
   * - Type compatibility: income -> income|both, expense -> expense|both, both -> both only
   * - Excludes excludeId (self) and its children (prevents circular references)
   */
  function compatibleParentCategories(type: CategoryType, excludeId?: string): LocalCategory[] {
    return categories.value.filter(cat => {
      // Must be root (no parent) — this is the 2-level limit:
      // a category that already has a parent cannot itself become a parent
      if (cat.parent_category_id) return false

      // Exclude self
      if (excludeId && cat.id === excludeId) return false

      // Exclude children of the excluded category (prevents circular)
      if (excludeId && cat.parent_category_id === excludeId) return false

      // Type compatibility:
      // income child -> parent must be income or both
      // expense child -> parent must be expense or both
      // both child   -> parent must be both
      const t = type as string
      const ct = cat.type as string
      if (t === 'income') {
        return ct === 'income' || ct === 'both'
      }
      if (t === 'expense') {
        return ct === 'expense' || ct === 'both'
      }
      if (t === 'both') {
        return ct === 'both'
      }

      return false
    })
  }

  // ---------------------------------------------------------------------------
  // Actions — Reads (offline-first, stale-while-revalidate)
  // ---------------------------------------------------------------------------

  async function fetchCategories(type?: CategoryType) {
    // Reset error state at the start of each fetch.
    // This ensures previous errors don't block new attempts.
    error.value = null
    loading.value = true

    try {
      // Note: the original store does NOT re-throw on error for categories,
      // because category load failures should not break navigation. We
      // preserve that behaviour here.
      //
      // fetchAllWithRevalidation will:
      //   - Serve local cache immediately (even if type filter can't be
      //     applied locally — we filter client-side below as a fallback).
      //   - Revalidate with the API in the background with the proper type
      //     filter applied server-side.
      const localData = await fetchAllWithRevalidation(
        db.categories,
        () => categoriesApi.getAll(type),
        (freshItems) => {
          // Background revalidation succeeded — replace with correctly
          // filtered server data.
          categories.value = freshItems
        }
      )

      // Apply client-side filter on the stale local data so the UI shows
      // only the requested category type while waiting for the network.
      categories.value = type
        ? localData.filter(cat => cat.type === type || cat.type === 'both')
        : localData

      return categories.value
    } catch (err: any) {
      console.error('Categories store fetch error:', err)
      error.value = err.message || 'Error al cargar categorías'
      // Don't throw — let the component handle the error state.
      // This prevents the error from bubbling up and breaking navigation.
      return []
    } finally {
      loading.value = false
    }
  }

  async function fetchCategoryById(id: string) {
    loading.value = true
    error.value = null
    try {
      const localItem = await fetchByIdWithRevalidation(
        db.categories,
        id,
        (catId) => categoriesApi.getById(catId),
        (freshItem) => {
          const index = categories.value.findIndex(c => c.id === id)
          if (index >= 0) {
            categories.value[index] = freshItem
          } else {
            categories.value.push(freshItem)
          }
        }
      )

      if (localItem) {
        const index = categories.value.findIndex(c => c.id === id)
        if (index >= 0) {
          categories.value[index] = localItem
        } else {
          categories.value.push(localItem)
        }
        return localItem
      }
    } catch (err: any) {
      error.value = err.message || 'Error al cargar categoría'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // Actions — Writes (Phase 3: offline-first pattern)
  // ---------------------------------------------------------------------------

  async function createCategory(data: CreateCategoryDto) {
    const tempId = generateTempId()
    const now = new Date().toISOString()

    // Build the full local category record.
    // parent_category_id is optional in both Category and CreateCategoryDto —
    // we carry it through as-is. If the parent was created offline its value
    // will be a temp-* ID; the SyncManager resolves it before the network call.
    const localCategory: LocalCategory = {
      id: tempId,
      name: data.name,
      type: data.type,
      icon: data.icon,
      color: data.color,
      parent_category_id: data.parent_category_id,
      created_at: now,
      updated_at: now,
      _sync_status: 'pending',
      _local_updated_at: now
    }

    loading.value = true
    error.value = null
    try {
      // Step 1 — IndexedDB write.
      await db.categories.add(localCategory)

      // Step 2 — Optimistic UI update.
      // push keeps parent categories before their children, which is consistent
      // with how the existing read actions populate the array.
      categories.value.push(localCategory)

      // Step 3 — Enqueue CREATE mutation.
      await mutationQueue.enqueue({
        entity_type: 'category',
        entity_id: tempId,
        operation: 'create',
        payload: { ...data, client_id: tempId }
      })

      return localCategory
    } catch (err: any) {
      error.value = err.message || 'Error al crear categoría'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateCategory(id: string, data: UpdateCategoryDto) {
    const localUpdatedAt = new Date().toISOString()

    loading.value = true
    error.value = null
    try {
      // Step 1 — Partial IndexedDB update.
      await db.categories.update(id, {
        ...data,
        _sync_status: 'pending',
        _local_updated_at: localUpdatedAt
      })

      // Step 2 — Reactive ref update.
      const idx = categories.value.findIndex(c => c.id === id)
      if (idx !== -1) {
        categories.value[idx] = {
          ...categories.value[idx],
          ...data,
          _sync_status: 'pending',
          _local_updated_at: localUpdatedAt
        }
      }

      // Step 3 — Merge optimisation: collapse UPDATE into pending CREATE.
      const pendingCreate = await mutationQueue.findPendingCreate('category', id)
      if (pendingCreate && pendingCreate.id != null) {
        await mutationQueue.updatePayload(pendingCreate.id, {
          ...pendingCreate.payload,
          ...data
        })
      } else {
        await mutationQueue.enqueue({
          entity_type: 'category',
          entity_id: id,
          operation: 'update',
          payload: data as Record<string, unknown>
        })
      }
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
      // Cancellation optimisation: if the CREATE is still pending, remove
      // everything locally without sending anything to the server.
      const pendingCreate = await mutationQueue.findPendingCreate('category', id)
      if (pendingCreate && pendingCreate.id != null) {
        await mutationQueue.remove(pendingCreate.id)
        await db.categories.delete(id)
        categories.value = categories.value.filter(c => c.id !== id)
        return
      }

      // Entity exists on the server — mark pending, remove from UI, enqueue DELETE.
      await db.categories.update(id, { _sync_status: 'pending' })
      categories.value = categories.value.filter(c => c.id !== id)

      await mutationQueue.enqueue({
        entity_type: 'category',
        entity_id: id,
        operation: 'delete',
        payload: { id }
      })
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar categoría'
      throw err
    } finally {
      loading.value = false
    }
  }

  function getCategoryById(id: string): LocalCategory | undefined {
    return categories.value.find(c => c.id === id)
  }

  async function refreshFromDB() {
    const data = await db.categories.toArray()
    categories.value = data
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
    categoryTree,
    // Functions
    compatibleParentCategories,
    // Actions
    fetchCategories,
    fetchCategoryById,
    createCategory,
    updateCategory,
    deleteCategory,
    getCategoryById,
    getSubcategories,
    refreshFromDB
  }
})
