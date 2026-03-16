/**
 * SettingsView-auth.spec.ts
 *
 * Tests for the authentication-related additions to SettingsView.vue:
 * 1. Greeting at the top — "Hola, [nombre]" or "Hola, Invitado"
 * 2. "Cerrar sesión" button — only visible when authenticated
 * 3. Logout modal — shows both options (keep data / delete all)
 * 4. Logout modal — calls correct authStore.logout(false/true) on each choice
 *
 * Strategy:
 * - Mock useAuthStore, useSettingsStore, useSyncStore, syncManager
 * - Mount SettingsView with @vue/test-utils
 * - Assert DOM state and emitted actions
 *
 * Why mock syncManager?
 * SettingsView calls syncManager.forceFullSync() on a button click. We don't
 * want real sync operations in unit tests — just verify the call.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

// ---------------------------------------------------------------------------
// Hoisted mock state
// ---------------------------------------------------------------------------
const mockAuthState = vi.hoisted(() => ({
  isAuthenticated: false,
  user: null as { id: string; email: string; name: string } | null,
  logout: vi.fn(),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => mockAuthState,
}))

vi.mock('@/stores/settings', () => ({
  useSettingsStore: () => ({
    primaryCurrency: 'USD',
    loading: false,
    setPrimaryCurrency: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/stores/sync', () => ({
  useSyncStore: () => ({
    isSyncing: false,
  }),
}))

vi.mock('@/offline/sync-manager', () => ({
  syncManager: {
    forceFullSync: vi.fn().mockResolvedValue(undefined),
  },
}))

vi.mock('@/utils/constants', () => ({
  SUPPORTED_CURRENCIES: [
    { code: 'USD', name: 'US Dollar', symbol: '$' },
    { code: 'EUR', name: 'Euro', symbol: '€' },
  ],
}))

vi.mock('@/components/ui/BaseSelect.vue', () => ({
  default: {
    name: 'BaseSelect',
    template: '<select><slot /></select>',
    props: ['modelValue', 'options', 'label', 'disabled'],
  },
}))

// Import AFTER mocks
import SettingsView from '../SettingsView.vue'

// ---------------------------------------------------------------------------
// Helper: create a minimal router
// ---------------------------------------------------------------------------
function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/settings', component: SettingsView },
    ],
  })
}

// ---------------------------------------------------------------------------
// Helper: mount with attachTo document.body so Teleport works correctly.
//
// Why attachTo: document.body?
// Vue's <Teleport to="body"> moves the teleported content outside the
// component's DOM subtree — it is rendered directly into document.body.
// When VTU mounts a component in a detached div (default), Teleport
// still renders to document.body but the content is not accessible via
// wrapper.find(). Using `attachTo: document.body` ensures the component
// is mounted IN the document, making both the component content AND the
// teleported modal content accessible in the same document.find() scope.
//
// The appended div is removed in afterEach via document.body cleanup,
// but VTU handles this automatically when wrapper.unmount() is called.
// ---------------------------------------------------------------------------
function mountSettings() {
  const div = document.createElement('div')
  document.body.appendChild(div)

  return mount(SettingsView, {
    attachTo: div,
    global: { plugins: [createTestRouter()] },
  })
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------
beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockAuthState.isAuthenticated = false
  mockAuthState.user = null
  mockAuthState.logout = vi.fn().mockResolvedValue(undefined)
})

// ---------------------------------------------------------------------------
// Greeting
// ---------------------------------------------------------------------------
describe('SettingsView — greeting', () => {
  it('shows "Hola, Invitado" when user is null (guest mode)', () => {
    mockAuthState.isAuthenticated = false
    mockAuthState.user = null

    const wrapper = mountSettings()

    expect(wrapper.text()).toContain('Hola')
    expect(wrapper.text()).toContain('Invitado')
    wrapper.unmount()
  })

  it('shows "Hola, [nombre]" when user is authenticated', () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.user = { id: 'user-1', email: 'angel@example.com', name: 'Angel Test' }

    const wrapper = mountSettings()

    expect(wrapper.text()).toContain('Hola')
    expect(wrapper.text()).toContain('Angel Test')
    wrapper.unmount()
  })
})

// ---------------------------------------------------------------------------
// Cerrar sesión button visibility
// ---------------------------------------------------------------------------
describe('SettingsView — cerrar sesión button', () => {
  it('is NOT visible when user is not authenticated (guest)', () => {
    mockAuthState.isAuthenticated = false
    mockAuthState.user = null

    const wrapper = mountSettings()

    expect(wrapper.text()).not.toContain('Cerrar sesión')
    wrapper.unmount()
  })

  it('IS visible when user is authenticated', () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.user = { id: 'user-1', email: 'angel@example.com', name: 'Angel Test' }

    const wrapper = mountSettings()

    expect(wrapper.text()).toContain('Cerrar sesión')
    wrapper.unmount()
  })
})

// ---------------------------------------------------------------------------
// Logout modal
// ---------------------------------------------------------------------------
describe('SettingsView — logout modal', () => {
  it('shows logout modal when "Cerrar sesión" is clicked', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.user = { id: 'user-1', email: 'angel@example.com', name: 'Angel Test' }

    const wrapper = mountSettings()

    // Find and click the "Cerrar sesión" button
    const logoutBtn = wrapper.findAll('button').find(b => b.text().includes('Cerrar sesión'))
    expect(logoutBtn).toBeDefined()
    await logoutBtn!.trigger('click')
    await flushPromises()

    // Modal is teleported to document.body — check body text
    expect(document.body.textContent).toContain('datos locales')
    wrapper.unmount()
  })

  it('modal shows "Mantener en modo invitado" option', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.user = { id: 'user-1', email: 'angel@example.com', name: 'Angel Test' }

    const wrapper = mountSettings()

    const logoutBtn = wrapper.findAll('button').find(b => b.text().includes('Cerrar sesión'))
    await logoutBtn!.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('Mantener')
    wrapper.unmount()
  })

  it('modal shows "Borrar todo" option', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.user = { id: 'user-1', email: 'angel@example.com', name: 'Angel Test' }

    const wrapper = mountSettings()

    const logoutBtn = wrapper.findAll('button').find(b => b.text().includes('Cerrar sesión'))
    await logoutBtn!.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('Borrar')
    wrapper.unmount()
  })

  it('calls authStore.logout(false) when "Mantener en modo invitado" is chosen', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.user = { id: 'user-1', email: 'angel@example.com', name: 'Angel Test' }

    const wrapper = mountSettings()

    // Open modal
    const logoutBtn = wrapper.findAll('button').find(b => b.text().includes('Cerrar sesión'))
    await logoutBtn!.trigger('click')
    await flushPromises()

    // Click "Mantener" option — it's in document.body, use querySelectorAll
    const buttons = Array.from(document.body.querySelectorAll('button'))
    const mantenerBtn = buttons.find(b => b.textContent?.includes('Mantener'))
    expect(mantenerBtn).toBeDefined()
    mantenerBtn!.click()
    await flushPromises()

    expect(mockAuthState.logout).toHaveBeenCalledWith(false)
    wrapper.unmount()
  })

  it('calls authStore.logout(true) when "Borrar todo" is chosen', async () => {
    mockAuthState.isAuthenticated = true
    mockAuthState.user = { id: 'user-1', email: 'angel@example.com', name: 'Angel Test' }

    const wrapper = mountSettings()

    // Open modal
    const logoutBtn = wrapper.findAll('button').find(b => b.text().includes('Cerrar sesión'))
    await logoutBtn!.trigger('click')
    await flushPromises()

    // Click "Borrar todo" option — it's in document.body
    const buttons = Array.from(document.body.querySelectorAll('button'))
    const borrarBtn = buttons.find(b => b.textContent?.includes('Borrar todo'))
    expect(borrarBtn).toBeDefined()
    borrarBtn!.click()
    await flushPromises()

    expect(mockAuthState.logout).toHaveBeenCalledWith(true)
    wrapper.unmount()
  })
})
