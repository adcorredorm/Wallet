import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SetupChecklist from '../SetupChecklist.vue'

// Mock stores
vi.mock('@/stores', () => ({
  useAccountsStore: vi.fn(),
  useCategoriesStore: vi.fn(),
}))

import { useAccountsStore, useCategoriesStore } from '@/stores'

// RouterLink stub: renders an <a> that forwards href and data-testid so assertions work
const RouterLinkStub = {
  template: '<a :href="to" v-bind="$attrs"><slot /></a>',
  props: ['to'],
}

function mountWith({ hasAccounts = false, hasCategories = false }) {
  ;(useAccountsStore as any).mockReturnValue({
    activeAccounts: hasAccounts ? [{ id: '1', name: 'Cuenta' }] : []
  })
  ;(useCategoriesStore as any).mockReturnValue({
    activeCategories: hasCategories ? [{ id: '1', name: 'Cat' }] : []
  })
  return mount(SetupChecklist, {
    global: {
      stubs: { RouterLink: RouterLinkStub },
    },
  })
}

describe('SetupChecklist', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
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

  it('account create button links to /accounts/new', () => {
    const w = mountWith({})
    const link = w.find('[data-testid="account-create-btn"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('/accounts/new')
  })

  it('category create button links to /categories/new', () => {
    const w = mountWith({})
    const link = w.find('[data-testid="category-create-btn"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('/categories/new')
  })
})
