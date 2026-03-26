/**
 * auth-retry.spec.ts
 *
 * Tests for the retry-with-backoff behavior in initializeFromStorage().
 *
 * Why vi.useFakeTimers?
 * The implementation uses setTimeout for delays. Fake timers let us advance
 * time programmatically without waiting real seconds in CI.
 *
 * Why mock @/offline/auth-db separately from @/api/auth?
 * auth-db is IndexedDB — not available in jsdom without a full Dexie mock.
 * We control getRefreshToken() return values directly.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// ── Hoisted mocks ────────────────────────────────────────────────────────────
const {
  mockGetRefreshToken,
  mockSetRefreshToken,
  mockDeleteRefreshToken,
  mockPostAuthRefresh,
} = vi.hoisted(() => ({
  mockGetRefreshToken: vi.fn(),
  mockSetRefreshToken: vi.fn().mockResolvedValue(undefined),
  mockDeleteRefreshToken: vi.fn().mockResolvedValue(undefined),
  mockPostAuthRefresh: vi.fn(),
}))

vi.mock('@/offline/auth-db', () => ({
  getRefreshToken: mockGetRefreshToken,
  setRefreshToken: mockSetRefreshToken,
  deleteRefreshToken: mockDeleteRefreshToken,
  setLastUserId: vi.fn(),
  getLastUserId: vi.fn(),
  deleteLastUserId: vi.fn(),
}))

vi.mock('@/api/auth', () => ({
  postAuthRefresh: mockPostAuthRefresh,
  postAuthGoogle: vi.fn(),
  postAuthLogout: vi.fn(),
}))

vi.mock('@/stores/sync', () => ({
  useSyncStore: vi.fn(() => ({
    setGuest: vi.fn(),
    isGuest: false,
  })),
}))

vi.mock('@/offline/db', () => ({
  db: { delete: vi.fn(), open: vi.fn() },
}))

// Minimal valid JWT payload (base64url-encoded `{"sub":"u1","email":"a@b.com","name":"Test"}`)
const FAKE_JWT =
  'eyJhbGciOiJub25lIn0.' +
  btoa(JSON.stringify({ sub: 'u1', email: 'a@b.com', name: 'Test' }))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '') +
  '.sig'

import { useAuthStore } from '@/stores/auth'

describe('initializeFromStorage — retry with backoff', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('succeeds immediately when refresh() succeeds on the first call', async () => {
    mockGetRefreshToken.mockResolvedValue('valid-token')
    mockPostAuthRefresh.mockResolvedValue({
      access_token: FAKE_JWT,
      refresh_token: 'new-token',
    })

    const store = useAuthStore()
    const promise = store.initializeFromStorage()
    await vi.runAllTimersAsync()
    await promise

    expect(mockPostAuthRefresh).toHaveBeenCalledTimes(1)
    expect(store.isAuthenticated).toBe(true)
  })

  it('retries up to 3 times on transient failure (token still in AuthDB)', async () => {
    // First 3 calls fail with a network error (no response), 4th succeeds
    mockGetRefreshToken.mockResolvedValue('valid-token')
    mockPostAuthRefresh
      .mockRejectedValueOnce(new Error('network error'))
      .mockRejectedValueOnce(new Error('network error'))
      .mockRejectedValueOnce(new Error('network error'))
      .mockResolvedValueOnce({ access_token: FAKE_JWT, refresh_token: 'new-tok' })

    const store = useAuthStore()
    const promise = store.initializeFromStorage()

    // Advance through delays: 5 s, 10 s, 15 s
    await vi.advanceTimersByTimeAsync(5_000)
    await vi.advanceTimersByTimeAsync(10_000)
    await vi.advanceTimersByTimeAsync(15_000)
    await promise

    expect(mockPostAuthRefresh).toHaveBeenCalledTimes(4)
    expect(store.isAuthenticated).toBe(true)
  })

  it('enters guest mode (not authenticated) after 3 retries all fail', async () => {
    mockGetRefreshToken.mockResolvedValue('valid-token')
    mockPostAuthRefresh.mockRejectedValue(new Error('server down'))

    const store = useAuthStore()
    const promise = store.initializeFromStorage()

    await vi.advanceTimersByTimeAsync(5_000)
    await vi.advanceTimersByTimeAsync(10_000)
    await vi.advanceTimersByTimeAsync(15_000)
    await promise

    // 1 initial + 3 retries = 4 total calls
    expect(mockPostAuthRefresh).toHaveBeenCalledTimes(4)
    expect(store.isAuthenticated).toBe(false)
  })

  it('does NOT retry when refresh() returns false because token was deleted (401)', async () => {
    // initializeFromStorage reads token (call 1), then refresh() reads it again (call 2).
    // After the 401, refresh() deletes the token. The retry loop checks the token (call 3+) and finds null.
    mockGetRefreshToken
      .mockResolvedValueOnce('valid-token') // call 1: initializeFromStorage top-level check
      .mockResolvedValueOnce('valid-token') // call 2: inside refresh() before calling postAuthRefresh
      .mockResolvedValue(null)             // calls 3+: token deleted by 401 path inside refresh()
    mockPostAuthRefresh.mockRejectedValueOnce({ response: { status: 401 } })

    const store = useAuthStore()
    const promise = store.initializeFromStorage()
    await vi.runAllTimersAsync()
    await promise

    expect(mockPostAuthRefresh).toHaveBeenCalledTimes(1)
    expect(store.isAuthenticated).toBe(false)
  })

  it('uses delays of 5 s, 10 s, 15 s (not longer)', async () => {
    mockGetRefreshToken.mockResolvedValue('valid-token')
    mockPostAuthRefresh.mockRejectedValue(new Error('fail'))

    const store = useAuthStore()
    const promise = store.initializeFromStorage()

    // After initial failure, wait exactly 5 s — second attempt should fire
    await vi.advanceTimersByTimeAsync(5_000)
    expect(mockPostAuthRefresh).toHaveBeenCalledTimes(2)

    await vi.advanceTimersByTimeAsync(10_000)
    expect(mockPostAuthRefresh).toHaveBeenCalledTimes(3)

    await vi.advanceTimersByTimeAsync(15_000)
    expect(mockPostAuthRefresh).toHaveBeenCalledTimes(4)

    await promise
  })
})
