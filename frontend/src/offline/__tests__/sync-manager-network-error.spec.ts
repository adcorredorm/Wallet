/**
 * sync-manager-network-error.spec.ts
 *
 * Tests for the 3-category error classification in handleError() and the
 * isNetworkError() helper.
 *
 * Strategy: test isNetworkError() directly by importing the helper (we will
 * export it for testability), and test handleError() behaviour indirectly
 * through the observable side effects:
 *   - network error → mutation stays in queue (incrementRetry NOT called)
 *   - 4xx           → markError called, mutation removed from queue
 *   - 5xx           → incrementRetry called, mutation NOT removed (unless max retries)
 *
 * Why mock the entire sync-manager module dependencies but not the class?
 * handleError() is a private method. We test it via a thin public wrapper or
 * by calling processQueue() with a pre-loaded mock queue. The simplest approach
 * is to test isNetworkError() directly (export it) and validate handleError()
 * behaviour by observing which db/mutationQueue calls are made.
 */

import { describe, it, expect, vi } from 'vitest'

// ── Shared mocks ─────────────────────────────────────────────────────────────

const { mockIncrementRetry, mockRemove, mockAccountsUpdate } = vi.hoisted(() => ({
  mockIncrementRetry: vi.fn().mockResolvedValue(undefined),
  mockRemove: vi.fn().mockResolvedValue(undefined),
  mockAccountsUpdate: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('@/offline/db', () => ({
  db: {
    accounts: { update: mockAccountsUpdate },
    transactions: { update: vi.fn() },
    transfers: { update: vi.fn() },
    categories: { update: vi.fn() },
    settings: { update: vi.fn() },
    dashboards: { update: vi.fn() },
    dashboardWidgets: { update: vi.fn() },
    pendingMutations: { update: vi.fn() },
  },
}))

vi.mock('@/offline/mutation-queue', () => ({
  mutationQueue: {
    getAll: vi.fn().mockResolvedValue([]),
    incrementRetry: mockIncrementRetry,
    remove: mockRemove,
    markBlocked: vi.fn().mockResolvedValue(undefined),
    count: vi.fn().mockResolvedValue(0),
  },
}))

// Import the helper under test AFTER mocks are registered
import { isNetworkError } from '@/offline/sync-manager'

describe('isNetworkError()', () => {
  it('returns true when error has no response property', () => {
    const err = { code: 'ERR_NETWORK' }
    expect(isNetworkError(err as any)).toBe(true)
  })

  it('returns true for code ERR_NETWORK even if response exists', () => {
    const err = { response: { status: 503 }, code: 'ERR_NETWORK' }
    expect(isNetworkError(err as any)).toBe(true)
  })

  it('returns true for code ECONNABORTED', () => {
    const err = { code: 'ECONNABORTED' }
    expect(isNetworkError(err as any)).toBe(true)
  })

  it('returns true for code ERR_CONNECTION_REFUSED', () => {
    const err = { code: 'ERR_CONNECTION_REFUSED' }
    expect(isNetworkError(err as any)).toBe(true)
  })

  it('returns false for a 503 with a response and no matching code', () => {
    const err = { response: { status: 503 } }
    expect(isNetworkError(err as any)).toBe(false)
  })

  it('returns false for a 422 (4xx permanent error)', () => {
    const err = { response: { status: 422 } }
    expect(isNetworkError(err as any)).toBe(false)
  })

  it('returns true when error has no response and no code', () => {
    const err = new Error('fetch failed')
    expect(isNetworkError(err as any)).toBe(true)
  })
})
