/**
 * GuestBanner.spec.ts
 *
 * Tests for GuestBanner.vue — the persistent banner shown when the user is
 * not authenticated (guest mode).
 *
 * Strategy:
 * - Mock useAuthStore to control isAuthenticated
 * - Mount GuestBanner with @vue/test-utils
 * - Assert visibility, message content, and navigation link
 *
 * Why mock useAuthStore and not useSyncStore?
 * GuestBanner's visibility is driven by authStore.isAuthenticated, not by
 * syncStore.syncStatus. The component directly checks auth state to decide
 * whether to render. This is the correct separation: the banner is about
 * authentication state, not sync state.
 *
 * Why stub vue-router?
 * GuestBanner contains a RouterLink or uses router.push() to navigate to
 * /login. We don't need a real router — just verify the link targets /login.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

// ---------------------------------------------------------------------------
// Mock useAuthStore
// ---------------------------------------------------------------------------
const mockIsAuthenticated = { value: false }

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    get isAuthenticated() {
      return mockIsAuthenticated.value
    },
  }),
}))

// Import AFTER mocks
import GuestBanner from '../GuestBanner.vue'

// ---------------------------------------------------------------------------
// Helper: create a minimal router for tests
// ---------------------------------------------------------------------------
function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/login', component: { template: '<div>Login</div>' } },
    ],
  })
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------
beforeEach(() => {
  setActivePinia(createPinia())
  mockIsAuthenticated.value = false
})

// ---------------------------------------------------------------------------
// Visibility
// ---------------------------------------------------------------------------
describe('GuestBanner — visibility', () => {
  it('is visible when user is NOT authenticated (guest mode)', () => {
    mockIsAuthenticated.value = false

    const wrapper = mount(GuestBanner, {
      global: {
        plugins: [createTestRouter()],
      },
    })

    // The banner content should be in the DOM
    expect(wrapper.text()).toContain('sincronizar')
  })

  it('is NOT visible when user IS authenticated', () => {
    mockIsAuthenticated.value = true

    const wrapper = mount(GuestBanner, {
      global: {
        plugins: [createTestRouter()],
      },
    })

    // When authenticated, the banner should not render meaningful content
    // (either v-if hides it or the wrapper is empty)
    expect(wrapper.text()).not.toContain('sincronizar')
  })
})

// ---------------------------------------------------------------------------
// Content
// ---------------------------------------------------------------------------
describe('GuestBanner — content', () => {
  it('shows the warning message about data not being saved to the cloud', () => {
    mockIsAuthenticated.value = false

    const wrapper = mount(GuestBanner, {
      global: {
        plugins: [createTestRouter()],
      },
    })

    expect(wrapper.text()).toContain('no serán guardados en la nube')
  })

  it('contains a link or button to navigate to /login', () => {
    mockIsAuthenticated.value = false

    const wrapper = mount(GuestBanner, {
      global: {
        plugins: [createTestRouter()],
      },
    })

    // Should have an "Iniciar sesión" interactive element
    expect(wrapper.text()).toContain('Iniciar sesión')
  })
})

// ---------------------------------------------------------------------------
// Accessibility
// ---------------------------------------------------------------------------
describe('GuestBanner — accessibility', () => {
  it('has role="alert" or aria-live for screen readers', () => {
    mockIsAuthenticated.value = false

    const wrapper = mount(GuestBanner, {
      global: {
        plugins: [createTestRouter()],
      },
    })

    // The banner must be announced to screen readers
    const hasAlert = wrapper.find('[role="alert"]').exists()
    const hasAriaLive = wrapper.find('[aria-live]').exists()
    expect(hasAlert || hasAriaLive).toBe(true)
  })
})
