import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SetupChecklist from '../SetupChecklist.vue'

// Mock router — using vi.fn() so individual tests can override the return value
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({ push: mockPush }))
}))

// Mock stores
vi.mock('@/stores', () => ({
  useAccountsStore: vi.fn(),
  useCategoriesStore: vi.fn(),
}))

import { useAccountsStore, useCategoriesStore } from '@/stores'

function mountWith({ hasAccounts = false, hasCategories = false }) {
  ;(useAccountsStore as any).mockReturnValue({
    activeAccounts: hasAccounts ? [{ id: '1', name: 'Cuenta' }] : []
  })
  ;(useCategoriesStore as any).mockReturnValue({
    activeCategories: hasCategories ? [{ id: '1', name: 'Cat' }] : []
  })
  return mount(SetupChecklist)
}

describe('SetupChecklist', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows both rows when nothing exists', () => {
    const w = mountWith({})
    expect(w.text()).toContain('Crea tu primera cuenta')
    expect(w.text()).toContain('Crea tu primera categoría')
    expect(w.text()).toContain('Configura tu wallet')
  })

  it('marks account row as done when account exists', () => {
    const w = mountWith({ hasAccounts: true })
    expect(w.find('[data-testid="account-done"]').exists()).toBe(true)
    expect(w.find('[data-testid="account-create-btn"]').exists()).toBe(false)
    expect(w.text()).toContain('Un paso más')
  })

  it('marks category row as done when category exists', () => {
    const w = mountWith({ hasCategories: true })
    expect(w.find('[data-testid="category-done"]').exists()).toBe(true)
    expect(w.find('[data-testid="category-create-btn"]').exists()).toBe(false)
  })

  it('account create button navigates to /accounts/new', async () => {
    mockPush.mockClear()
    const w = mountWith({})
    await w.find('[data-testid="account-create-btn"]').trigger('click')
    expect(mockPush).toHaveBeenCalledWith('/accounts/new')
  })

  it('category create button navigates to /categories/new', async () => {
    mockPush.mockClear()
    const w = mountWith({})
    await w.find('[data-testid="category-create-btn"]').trigger('click')
    expect(mockPush).toHaveBeenCalledWith('/categories/new')
  })
})
