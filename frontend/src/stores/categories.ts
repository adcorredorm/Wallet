/**
 * Categories Store
 *
 * Manages transaction categories with hierarchy support
 * - Parent/child category relationships
 * - Filter by type (ingreso, gasto, ambos)
 * - CRUD operations
 *
 * Phase 3 change: write actions now follow the offline-first pattern.
 * Writes go to IndexedDB and the mutation queue immediately; the UI updates
 * optimistically. The SyncManager (Phase 4) will flush to the server.
 *
 * Note on categoria_padre_id: if a user creates a parent category offline and
 * then creates a child category in the same session, categoria_padre_id in the
 * child's payload will be a temp-* ID. The SyncManager resolves it before the
 * network call, in FIFO order so the parent is created on the server first.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { categoriesApi } from '@/api/categories'
import type { CreateCategoryDto, UpdateCategoryDto, CategoryType } from '@/types'
import { db, fetchAllWithRevalidation, fetchByIdWithRevalidation, generateTempId, mutationQueue } from '@/offline'
import type { LocalCategory } from '@/offline'

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

  // ---------------------------------------------------------------------------
  // Actions — Reads (offline-first, stale-while-revalidate)
  // ---------------------------------------------------------------------------

  async function fetchCategories(tipo?: CategoryType) {
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
      //   - Serve local cache immediately (even if tipo filter can't be
      //     applied locally — we filter client-side below as a fallback).
      //   - Revalidate with the API in the background with the proper tipo
      //     filter applied server-side.
      const localData = await fetchAllWithRevalidation(
        db.categories,
        () => categoriesApi.getAll(tipo),
        (freshItems) => {
          // Background revalidation succeeded — replace with correctly
          // filtered server data.
          categories.value = freshItems
        }
      )

      // Apply client-side filter on the stale local data so the UI shows
      // only the requested category type while waiting for the network.
      categories.value = tipo
        ? localData.filter(cat => cat.tipo === tipo || cat.tipo === 'ambos')
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
    // categoria_padre_id is optional in both Category and CreateCategoryDto —
    // we carry it through as-is. If the parent was created offline its value
    // will be a temp-* ID; the SyncManager resolves it before the network call.
    const localCategory: LocalCategory = {
      id: tempId,
      nombre: data.nombre,
      tipo: data.tipo,
      icono: data.icono,
      color: data.color,
      categoria_padre_id: data.categoria_padre_id,
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
