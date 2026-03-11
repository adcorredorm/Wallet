/**
 * categories-hierarchy.spec.ts
 *
 * Unit tests for the categoryTree computed and compatibleParentCategories
 * function added to the categories store for the hierarchy feature.
 *
 * Mock strategy: same as accounts.spec.ts — mock @/offline barrel and
 * @/api/categories to avoid real IndexedDB and network calls in jsdom.
 */

import { setActivePinia } from 'pinia'
import { createTestingPinia } from '@pinia/testing'
import { useCategoriesStore } from '../categories'
import type { LocalCategory } from '@/offline'
import { CategoryType } from '@/types/category'

// ---------------------------------------------------------------------------
// Module-level mocks
// ---------------------------------------------------------------------------

vi.mock('@/offline', () => ({
  db: {
    categories: {
      toArray: vi.fn().mockResolvedValue([]),
      update: vi.fn().mockResolvedValue(undefined),
      add: vi.fn().mockResolvedValue(undefined),
      delete: vi.fn().mockResolvedValue(undefined),
    },
  },
  fetchAllWithRevalidation: vi.fn().mockResolvedValue([]),
  fetchByIdWithRevalidation: vi.fn().mockResolvedValue(undefined),
  generateTempId: vi.fn().mockReturnValue('temp-test-id'),
  isTempId: vi.fn((id: string) => id.startsWith('temp-')),
  mutationQueue: {
    enqueue: vi.fn().mockResolvedValue(1),
    findPendingCreate: vi.fn().mockResolvedValue(undefined),
    updatePayload: vi.fn().mockResolvedValue(undefined),
    remove: vi.fn().mockResolvedValue(undefined),
    count: vi.fn().mockResolvedValue(0),
  },
  syncManager: {},
  MutationQueue: vi.fn(),
  SyncManager: vi.fn(),
}))

vi.mock('@/api/categories', () => ({
  categoriesApi: {
    getAll: vi.fn().mockResolvedValue([]),
    getById: vi.fn().mockResolvedValue(null),
    create: vi.fn().mockResolvedValue(null),
    update: vi.fn().mockResolvedValue(null),
    delete: vi.fn().mockResolvedValue(undefined),
  },
}))

// ---------------------------------------------------------------------------
// Fixture factory
// ---------------------------------------------------------------------------

function makeCat(overrides: Partial<LocalCategory> = {}): LocalCategory {
  return {
    id: 'cat-1',
    nombre: 'Test Category',
    tipo: CategoryType.GASTO,
    created_at: '2024-01-01T00:00:00.000Z',
    updated_at: '2024-01-01T00:00:00.000Z',
    _sync_status: 'synced',
    _local_updated_at: '2024-01-01T00:00:00.000Z',
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Setup helper
// ---------------------------------------------------------------------------

function setup() {
  setActivePinia(createTestingPinia({ stubActions: false }))
  return useCategoriesStore()
}

// ---------------------------------------------------------------------------
// categoryTree
// ---------------------------------------------------------------------------

describe('useCategoriesStore — categoryTree', () => {
  it('groups parent-child relationships correctly', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'parent-1', nombre: 'Alimentación', tipo: CategoryType.GASTO }),
      makeCat({ id: 'child-1', nombre: 'Restaurantes', tipo: CategoryType.GASTO, categoria_padre_id: 'parent-1' }),
      makeCat({ id: 'child-2', nombre: 'Supermercado', tipo: CategoryType.GASTO, categoria_padre_id: 'parent-1' }),
    ]

    const tree = store.categoryTree
    expect(tree).toHaveLength(1)
    expect(tree[0].parent.id).toBe('parent-1')
    expect(tree[0].children).toHaveLength(2)
    expect(tree[0].children.map(c => c.id)).toEqual(['child-1', 'child-2'])
  })

  it('sorts groups with children first (alpha), then standalone (alpha)', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'standalone-z', nombre: 'Zzz Standalone' }),
      makeCat({ id: 'standalone-a', nombre: 'Aaa Standalone' }),
      makeCat({ id: 'parent-b', nombre: 'Bbb Parent' }),
      makeCat({ id: 'child-b1', nombre: 'Child B1', categoria_padre_id: 'parent-b' }),
      makeCat({ id: 'parent-a', nombre: 'Aaa Parent' }),
      makeCat({ id: 'child-a1', nombre: 'Child A1', categoria_padre_id: 'parent-a' }),
    ]

    const tree = store.categoryTree
    // Groups with children first, alphabetically
    expect(tree[0].parent.nombre).toBe('Aaa Parent')
    expect(tree[1].parent.nombre).toBe('Bbb Parent')
    // Then standalone, alphabetically
    expect(tree[2].parent.nombre).toBe('Aaa Standalone')
    expect(tree[3].parent.nombre).toBe('Zzz Standalone')
  })

  it('treats orphaned children (parent not in store) as standalone roots', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'orphan-1', nombre: 'Orphan', categoria_padre_id: 'nonexistent-parent' }),
      makeCat({ id: 'normal-1', nombre: 'Normal' }),
    ]

    const tree = store.categoryTree
    expect(tree).toHaveLength(2)
    // Both should be standalone (no children)
    expect(tree.every(g => g.children.length === 0)).toBe(true)
    // Alphabetical: Normal before Orphan
    expect(tree[0].parent.nombre).toBe('Normal')
    expect(tree[1].parent.nombre).toBe('Orphan')
  })

  it('returns empty array when categories is empty', () => {
    const store = setup()
    store.categories = []

    expect(store.categoryTree).toEqual([])
  })

  it('sorts children within a group alphabetically by nombre', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'parent', nombre: 'Parent' }),
      makeCat({ id: 'child-z', nombre: 'Zzz', categoria_padre_id: 'parent' }),
      makeCat({ id: 'child-a', nombre: 'Aaa', categoria_padre_id: 'parent' }),
      makeCat({ id: 'child-m', nombre: 'Mmm', categoria_padre_id: 'parent' }),
    ]

    const tree = store.categoryTree
    expect(tree[0].children.map(c => c.nombre)).toEqual(['Aaa', 'Mmm', 'Zzz'])
  })
})

// ---------------------------------------------------------------------------
// compatibleParentCategories
// ---------------------------------------------------------------------------

describe('useCategoriesStore — compatibleParentCategories', () => {
  it('returns only gasto and ambos parents for tipo=gasto', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'cat-gasto', nombre: 'Gasto Cat', tipo: CategoryType.GASTO }),
      makeCat({ id: 'cat-ingreso', nombre: 'Ingreso Cat', tipo: CategoryType.INGRESO }),
      makeCat({ id: 'cat-ambos', nombre: 'Ambos Cat', tipo: CategoryType.AMBOS }),
    ]

    const result = store.compatibleParentCategories(CategoryType.GASTO)
    const ids = result.map(c => c.id)
    expect(ids).toContain('cat-gasto')
    expect(ids).toContain('cat-ambos')
    expect(ids).not.toContain('cat-ingreso')
  })

  it('returns only ingreso and ambos parents for tipo=ingreso', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'cat-gasto', nombre: 'Gasto Cat', tipo: CategoryType.GASTO }),
      makeCat({ id: 'cat-ingreso', nombre: 'Ingreso Cat', tipo: CategoryType.INGRESO }),
      makeCat({ id: 'cat-ambos', nombre: 'Ambos Cat', tipo: CategoryType.AMBOS }),
    ]

    const result = store.compatibleParentCategories(CategoryType.INGRESO)
    const ids = result.map(c => c.id)
    expect(ids).toContain('cat-ingreso')
    expect(ids).toContain('cat-ambos')
    expect(ids).not.toContain('cat-gasto')
  })

  it('returns only ambos parents for tipo=ambos', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'cat-gasto', nombre: 'Gasto Cat', tipo: CategoryType.GASTO }),
      makeCat({ id: 'cat-ingreso', nombre: 'Ingreso Cat', tipo: CategoryType.INGRESO }),
      makeCat({ id: 'cat-ambos', nombre: 'Ambos Cat', tipo: CategoryType.AMBOS }),
    ]

    const result = store.compatibleParentCategories(CategoryType.AMBOS)
    const ids = result.map(c => c.id)
    expect(ids).toEqual(['cat-ambos'])
  })

  it('excludes excludeId and its children from results', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'cat-a', nombre: 'Cat A', tipo: CategoryType.GASTO }),
      makeCat({ id: 'cat-b', nombre: 'Cat B', tipo: CategoryType.GASTO }),
      makeCat({ id: 'child-a', nombre: 'Child A', tipo: CategoryType.GASTO, categoria_padre_id: 'cat-a' }),
    ]

    const result = store.compatibleParentCategories(CategoryType.GASTO, 'cat-a')
    const ids = result.map(c => c.id)
    expect(ids).not.toContain('cat-a')
    // child-a is not root, so wouldn't be returned anyway
    expect(ids).not.toContain('child-a')
    expect(ids).toContain('cat-b')
  })

  it('includes root categories that already have children (they can accept more children)', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'parent-with-child', nombre: 'Has Child', tipo: CategoryType.GASTO }),
      makeCat({ id: 'child-1', nombre: 'Child', tipo: CategoryType.GASTO, categoria_padre_id: 'parent-with-child' }),
      makeCat({ id: 'no-children', nombre: 'No Children', tipo: CategoryType.GASTO }),
    ]

    const result = store.compatibleParentCategories(CategoryType.GASTO)
    const ids = result.map(c => c.id)
    // Both root categories are valid parents regardless of whether they already have children
    expect(ids).toContain('parent-with-child')
    expect(ids).toContain('no-children')
    // The child itself is not a valid parent (2-level limit via root-only filter)
    expect(ids).not.toContain('child-1')
  })

  it('only returns root categories — excludes categories that already have a parent (2-level limit)', () => {
    const store = setup()
    store.categories = [
      makeCat({ id: 'root', nombre: 'Root', tipo: CategoryType.GASTO }),
      makeCat({ id: 'child', nombre: 'Child', tipo: CategoryType.GASTO, categoria_padre_id: 'root' }),
    ]

    const result = store.compatibleParentCategories(CategoryType.GASTO)
    const ids = result.map(c => c.id)
    // child has a parent so cannot itself be a parent
    expect(ids).not.toContain('child')
    // root is valid — it can accept children even though it already has one
    expect(ids).toContain('root')
  })

  it('returns empty array when no categories exist', () => {
    const store = setup()
    store.categories = []

    const result = store.compatibleParentCategories(CategoryType.GASTO)
    expect(result).toEqual([])
  })
})
