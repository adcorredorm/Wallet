import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'

vi.mock('@/stores', () => ({
  useAccountsStore: vi.fn(),
  useTransactionsStore: vi.fn(),
  useCategoriesStore: vi.fn(),
  useUiStore: vi.fn(),
}))

vi.mock('@/components/dashboard/NetWorthCard.vue', () => ({ default: { template: '<div data-testid="net-worth-card" />' } }))
vi.mock('@/components/dashboard/NetWorthChart.vue', () => ({ default: { template: '<div data-testid="net-worth-chart" />' } }))
vi.mock('@/components/dashboard/SetupChecklist.vue', () => ({ default: { template: '<div data-testid="setup-checklist" />' } }))
vi.mock('@/components/ui/FloatingActionButton.vue', () => ({ default: { props: ['disabled'], template: '<button data-testid="fab" :disabled="disabled" />' } }))
vi.mock('@/composables/useMovements', () => ({ useMovements: () => ({ items: [], currentPage: 1, totalPages: 1, loading: false, goToPage: vi.fn() }) }))

import { useAccountsStore, useTransactionsStore, useCategoriesStore, useUiStore } from '@/stores'
import DashboardView from '../DashboardView.vue'

function mockStores({ hasAccounts = true, hasCategories = true } = {}) {
  ;(useAccountsStore as any).mockReturnValue({
    activeAccounts: hasAccounts ? [{ id: '1' }] : [],
    accountsWithBalances: [],
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
  })
  ;(useTransactionsStore as any).mockReturnValue({
    fetchTransactions: vi.fn().mockResolvedValue(undefined),
    loading: false,
  })
  ;(useCategoriesStore as any).mockReturnValue({
    activeCategories: hasCategories ? [{ id: '1' }] : [],
    fetchCategories: vi.fn().mockResolvedValue(undefined),
  })
  ;(useUiStore as any).mockReturnValue({ showError: vi.fn() })
}

async function mountDashboard() {
  const router = createRouter({ history: createWebHistory(), routes: [{ path: '/', component: DashboardView }] })
  const wrapper = mount(DashboardView, {
    global: { plugins: [createPinia(), router] }
  })
  await router.isReady()
  return wrapper
}

describe('DashboardView setup checklist', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('shows setup checklist and disables FAB when no accounts and no categories', async () => {
    mockStores({ hasAccounts: false, hasCategories: false })
    const w = await mountDashboard()
    expect(w.find('[data-testid="setup-checklist"]').exists()).toBe(true)
    expect(w.find('[data-testid="net-worth-chart"]').exists()).toBe(false)
    expect(w.find('[data-testid="fab"]').attributes('disabled')).toBeDefined()
  })

  it('shows chart and enables FAB when both exist', async () => {
    mockStores({ hasAccounts: true, hasCategories: true })
    const w = await mountDashboard()
    expect(w.find('[data-testid="setup-checklist"]').exists()).toBe(false)
    expect(w.find('[data-testid="net-worth-chart"]').exists()).toBe(true)
    expect(w.find('[data-testid="fab"]').attributes('disabled')).toBeUndefined()
  })

  it('does NOT render AccountsOverview', async () => {
    mockStores()
    const w = await mountDashboard()
    expect(w.find('[data-testid="accounts-overview"]').exists()).toBe(false)
  })
})
