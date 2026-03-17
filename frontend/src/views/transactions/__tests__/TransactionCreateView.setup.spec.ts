import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const pushMock = vi.fn()
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return { ...actual, useRouter: () => ({ push: pushMock, back: vi.fn() }), useRoute: () => ({ query: {} }) }
})

vi.mock('@/stores', () => ({
  useTransactionsStore: vi.fn(),
  useAccountsStore: vi.fn(),
  useCategoriesStore: vi.fn(),
  useUiStore: vi.fn(),
}))

vi.mock('@/components/transactions/TransactionForm.vue', () => ({ default: { template: '<div data-testid="transaction-form" />' } }))
vi.mock('@/components/shared/EmptyState.vue', () => ({
  default: {
    props: ['title', 'actionText'],
    emits: ['action'],
    template: '<div data-testid="empty-state"><button @click="$emit(\'action\')">go</button></div>'
  }
}))

import { useAccountsStore, useCategoriesStore, useUiStore, useTransactionsStore } from '@/stores'
import TransactionCreateView from '../TransactionCreateView.vue'

function mockStores({ hasAccounts = true, hasCategories = true } = {}) {
  ;(useAccountsStore as any).mockReturnValue({ activeAccounts: hasAccounts ? [{ id: '1' }] : [] })
  ;(useCategoriesStore as any).mockReturnValue({ activeCategories: hasCategories ? [{ id: '1' }] : [], categories: [] })
  ;(useUiStore as any).mockReturnValue({ showSuccess: vi.fn(), showError: vi.fn() })
  ;(useTransactionsStore as any).mockReturnValue({ createTransaction: vi.fn().mockResolvedValue(undefined), loading: false })
}

describe('TransactionCreateView safety net', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('shows form when both account and category exist', () => {
    mockStores({ hasAccounts: true, hasCategories: true })
    const w = mount(TransactionCreateView)
    expect(w.find('[data-testid="transaction-form"]').exists()).toBe(true)
    expect(w.find('[data-testid="empty-state"]').exists()).toBe(false)
  })

  it('shows blocking empty state when no accounts', () => {
    mockStores({ hasAccounts: false, hasCategories: true })
    const w = mount(TransactionCreateView)
    expect(w.find('[data-testid="empty-state"]').exists()).toBe(true)
    expect(w.find('[data-testid="transaction-form"]').exists()).toBe(false)
  })

  it('shows blocking empty state when no categories', () => {
    mockStores({ hasAccounts: true, hasCategories: false })
    const w = mount(TransactionCreateView)
    expect(w.find('[data-testid="empty-state"]').exists()).toBe(true)
  })

  it('empty state action navigates to home', async () => {
    mockStores({ hasAccounts: false, hasCategories: false })
    const w = mount(TransactionCreateView)
    await w.find('[data-testid="empty-state"] button').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/')
  })
})
