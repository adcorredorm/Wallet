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
 *
 * Archive/hard-delete change:
 * - archiveCategory: sets active=false for the category and all its active
 *   children. Children are archived first so the parent is always archived last.
 *   Backend interprets DELETE as a soft-delete (archive).
 * - hardDeleteCategory: permanently removes the record from IndexedDB and
 *   enqueues a delete_permanent mutation. Only allowed when no transactions
 *   reference the category.
 * - restoreCategory: flips active back to true for a single category.
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

  // activeCategories — only categories with active=true.
  // Why expose this separately from `categories`?
  // Dropdowns (category pickers on transaction/transfer forms) must only show
  // active categories. Having a dedicated computed avoids sprinkling
  // `.filter(c => c.active)` calls across every component that needs a picker.
  const activeCategories = computed(() =>
    categories.value.filter(cat => cat.active !== false)
  )

  // archivedCategories — only categories with active=false.
  // Used by the archive management view to list items that can be restored
  // or hard-deleted.
  const archivedCategories = computed(() =>
    categories.value.filter(cat => cat.active === false)
  )

  const incomeCategories = computed(() =>
    activeCategories.value.filter(cat =>
      cat.type === 'income' || cat.type === 'both'
    )
  )

  const expenseCategories = computed(() =>
    activeCategories.value.filter(cat =>
      cat.type === 'expense' || cat.type === 'both'
    )
  )

  const parentCategories = computed(() =>
    activeCategories.value.filter(cat => !cat.parent_category_id)
  )

  // Helper to get ACTIVE subcategories of a parent.
  // Why filter active !== false?
  // Archived subcategories should not count toward the "has active subcategories"
  // guard in CategoryEditView, and the tree/cascade UI only cares about live
  // children. Using active !== false mirrors the convention used elsewhere in
  // this store (activeCategories computed) and guards against older IndexedDB
  // records where active may be undefined.
  const getSubcategories = (parentId: string) =>
    categories.value.filter(
      cat => cat.parent_category_id === parentId && cat.active !== false
    )

  /**
   * categoryTree — groups all ACTIVE categories into a 2-level hierarchy.
   *
   * Why filter to active only?
   * The tree is used by the transaction/category management UI. Archived
   * categories should not appear in the tree — they belong in the archive view.
   *
   * Each CategoryGroup has a parent and its direct children.
   * Sorting: groups with children come first (alphabetical by name),
   * then standalone categories (no children, alphabetical by name).
   * Orphaned children (parent_id set but parent not in store) are treated
   * as standalone root entries.
   */
  const categoryTree = computed<CategoryGroup[]>(() => {
    // Only build the tree from active categories
    const activeCats = categories.value.filter(cat => cat.active !== false)

    const byId = new Map<string, LocalCategory>()
    for (const cat of activeCats) {
      byId.set(cat.id, cat)
    }

    // Identify root categories: no parent_category_id, or parent_category_id not found in store
    const roots: LocalCategory[] = []
    const childrenMap = new Map<string, LocalCategory[]>()

    for (const cat of activeCats) {
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
   * - Only considers active categories (archived cannot be a parent)
   */
  function compatibleParentCategories(type: CategoryType, excludeId?: string): LocalCategory[] {
    return activeCategories.value.filter(cat => {
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

  async function fetchCategories() {
    error.value = null
    loading.value = true
    try {
      await refreshFromDB()
    } catch (err: any) {
      console.error('Categories store fetch error:', err)
      error.value = err.message || 'Error al cargar categorías'
      // Don't throw — let the component handle the error state.
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
    //
    // Why active: true here?
    // Category.active is a required field (non-optional boolean). New categories
    // are always active by definition — only an archive action sets active=false.
    // Without this field the object would fail the LocalCategory type check
    // because active is required on the Category base interface.
    const localCategory: LocalCategory = {
      id: tempId,
      name: data.name,
      type: data.type,
      icon: data.icon,
      color: data.color,
      parent_category_id: data.parent_category_id,
      active: true,
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

  /**
   * Archive a category — soft-delete that sets active=false.
   *
   * Why cascade to children first?
   * A parent cannot be left active while its children are archived in an
   * inconsistent state, and the 2-level limit means there are at most one
   * level of children to consider. Archiving children before the parent
   * ensures the tree is always coherent: if the parent is archived the
   * children are too.
   *
   * Why archive children that are already inactive?
   * We skip already-archived children (active === false) to avoid redundant
   * DB writes and duplicate mutation queue entries.
   *
   * Returns { cascaded: number } — total categories archived (parent + children).
   */
  async function archiveCategory(id: string): Promise<{ cascaded: number }> {
    loading.value = true
    error.value = null
    try {
      const now = new Date().toISOString()
      let cascaded = 0

      // Find active children directly from Dexie — avoids a race condition
      // where a concurrent background revalidation replaces categories.value
      // between loop iterations, causing only the first child to be archived.
      const activeChildren = await db.categories
        .where('parent_category_id')
        .equals(id)
        .filter(c => c.active !== false)
        .toArray()

      // Archive each active child first.
      for (const child of activeChildren) {
        // Step 1 — IndexedDB update for child.
        await db.categories.update(child.id, {
          active: false,
          _sync_status: 'pending',
          _local_updated_at: now
        })

        // Step 2 — Reactive ref update for child.
        const childIdx = categories.value.findIndex(c => c.id === child.id)
        if (childIdx !== -1) {
          categories.value[childIdx] = {
            ...categories.value[childIdx],
            active: false,
            _sync_status: 'pending',
            _local_updated_at: now
          }
        }

        // Step 3 — Enqueue DELETE mutation for child.
        // Backend treats DELETE as soft-delete (archive).
        await mutationQueue.enqueue({
          entity_type: 'category',
          entity_id: child.id,
          operation: 'delete',
          payload: { id: child.id }
        })

        cascaded++
      }

      // Now archive the parent itself.
      await db.categories.update(id, {
        active: false,
        _sync_status: 'pending',
        _local_updated_at: now
      })

      const idx = categories.value.findIndex(c => c.id === id)
      if (idx !== -1) {
        categories.value[idx] = {
          ...categories.value[idx],
          active: false,
          _sync_status: 'pending',
          _local_updated_at: now
        }
      }

      await mutationQueue.enqueue({
        entity_type: 'category',
        entity_id: id,
        operation: 'delete',
        payload: { id }
      })

      cascaded++ // count the parent

      return { cascaded }
    } catch (err: any) {
      error.value = err.message || 'Error al archivar categoría'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Hard-delete a category — permanently removes the record from IndexedDB
   * and enqueues a delete_permanent mutation for the backend.
   *
   * Why verify zero transactions first?
   * Hard delete is only valid when the category has no associated transaction
   * history. The UI disables the button, but this guard protects against
   * programmatic misuse and race conditions.
   */
  async function hardDeleteCategory(id: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      // Guard: verify no transactions reference this category.
      const txCount = await db.transactions.where('category_id').equals(id).count()
      if (txCount > 0) {
        throw new Error(
          'Cannot hard-delete a category that has transactions. Archive it instead.'
        )
      }

      // Step 1 — Remove from IndexedDB entirely.
      await db.categories.delete(id)

      // Step 2 — Remove from reactive state.
      categories.value = categories.value.filter(c => c.id !== id)

      // Step 3 — Enqueue delete_permanent mutation.
      await mutationQueue.enqueue({
        entity_type: 'category',
        entity_id: id,
        operation: 'delete_permanent',
        payload: { id }
      })
    } catch (err: any) {
      error.value = err.message || 'Error al eliminar categoría permanentemente'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Restore an archived category — flips active back to true.
   *
   * Why not cascade restore to children?
   * Children were individually archived and should be restored individually.
   * The user may intentionally want some children to remain archived. Cascading
   * restore would override those individual decisions.
   */
  async function restoreCategory(id: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const localUpdatedAt = new Date().toISOString()

      // Step 1 — Update IndexedDB: flip active back to true.
      await db.categories.update(id, {
        active: true,
        _sync_status: 'pending',
        _local_updated_at: localUpdatedAt
      })

      // Step 2 — Update reactive ref.
      const idx = categories.value.findIndex(c => c.id === id)
      if (idx !== -1) {
        categories.value[idx] = {
          ...categories.value[idx],
          active: true,
          _sync_status: 'pending',
          _local_updated_at: localUpdatedAt
        }
      }

      // Step 3 — Enqueue update mutation with { active: true }.
      await mutationQueue.enqueue({
        entity_type: 'category',
        entity_id: id,
        operation: 'update',
        payload: { active: true }
      })
    } catch (err: any) {
      error.value = err.message || 'Error al restaurar categoría'
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
    activeCategories,
    archivedCategories,
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
    archiveCategory,
    hardDeleteCategory,
    restoreCategory,
    getCategoryById,
    getSubcategories,
    refreshFromDB
  }
})
