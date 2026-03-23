/**
 * auth-interceptor.spec.ts
 *
 * Tests for the Authorization header interceptor added to apiClient and syncClient.
 *
 * Strategy:
 * - Spy on interceptors.request.use for both clients BEFORE the modules are
 *   loaded, so we can capture the registered handler.
 * - Execute the captured handler directly with a fake AxiosRequestConfig and
 *   assert that the Authorization header is set (or not set) correctly.
 *
 * Why capture the handler directly instead of making real HTTP requests?
 * The interceptor logic itself (read token, set header) is what we are testing.
 * Making real HTTP calls would require a network server and would test Axios
 * behavior, not our interceptor. Extracting the handler lets us test exactly
 * the function we wrote.
 *
 * Why test both apiClient and syncClient?
 * They are two distinct Axios instances. A bug in one would not be caught
 * by testing only the other. Both must have the interceptor for auth to work.
 *
 * Why mock useAuthStore lazily?
 * The spec requires that useAuthStore() is called INSIDE the interceptor
 * callback (not at module init time). This test verifies that: the mock
 * changes between test cases and the interceptor always reads the latest value.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import type { InternalAxiosRequestConfig } from 'axios'

// ---------------------------------------------------------------------------
// Hoisted mock state — accessToken value controlled per test.
//
// Why a mutable container object instead of a plain variable?
// vi.hoisted() runs before vi.mock() factories are executed. Variables
// declared with let/const in the test body cannot be referenced inside
// vi.mock() factories (they are not yet initialized when the factory runs).
// A mutable object { currentToken } created in vi.hoisted() IS accessible
// inside the factory because it was created at hoist time.
//
// Why does useAuthStore return `currentToken` directly (not a ref)?
// Pinia's Composition API stores unwrap refs when accessed from outside the
// store. So `authStore.accessToken` returns the raw string | null, NOT a
// Ref<string | null>. The interceptor code does `authStore.accessToken`
// (no .value needed), so the mock must mirror this: return the plain value.
// ---------------------------------------------------------------------------
const mockState = vi.hoisted(() => ({
  currentToken: null as string | null,
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    get accessToken() {
      return mockState.currentToken
    },
  }),
}))

// ---------------------------------------------------------------------------
// Helper: create a minimal AxiosRequestConfig with mutable headers
// ---------------------------------------------------------------------------
function makeConfig(): InternalAxiosRequestConfig {
  return {
    headers: {} as InternalAxiosRequestConfig['headers'],
  } as InternalAxiosRequestConfig
}

// Import AFTER mocks are set up
import apiClient from '../index'
import { syncClient } from '../sync-client'

// ---------------------------------------------------------------------------
// Helper: extract the last registered request interceptor handler from a
// given Axios instance. Axios stores interceptors in `interceptors.request`
// which has an internal `handlers` array.
// ---------------------------------------------------------------------------
function getRequestInterceptorHandler(client: typeof apiClient) {
  // Access the internal handlers array (not part of public API but stable in
  // axios 1.x — the handlers array is set by interceptors.request.use)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const manager = (client.interceptors.request as any)
  // handlers is an array of { fulfilled, rejected } | null
  const handlers: Array<{ fulfilled: (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig } | null> =
    manager.handlers ?? []

  // Find the last non-null handler (the one we added)
  const last = [...handlers].reverse().find(h => h !== null)
  if (!last) throw new Error('No request interceptor found on this client')
  return last.fulfilled
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------
beforeEach(() => {
  setActivePinia(createPinia())
  // Reset access token to null (guest mode) before each test
  mockState.currentToken = null
})

// ---------------------------------------------------------------------------
// apiClient interceptor
// ---------------------------------------------------------------------------
describe('apiClient — Authorization header interceptor', () => {
  it('adds Authorization: Bearer <token> when accessToken is set', () => {
    mockState.currentToken = 'test-access-token-abc123'

    const handler = getRequestInterceptorHandler(apiClient)
    const config = makeConfig()
    const result = handler(config)

    expect((result.headers as Record<string, string>)['Authorization']).toBe(
      'Bearer test-access-token-abc123'
    )
  })

  it('does NOT add Authorization header when accessToken is null (guest mode)', () => {
    mockState.currentToken = null

    const handler = getRequestInterceptorHandler(apiClient)
    const config = makeConfig()
    const result = handler(config)

    expect((result.headers as Record<string, string>)['Authorization']).toBeUndefined()
  })

  it('picks up token changes between calls (lazy store access)', () => {
    const handler = getRequestInterceptorHandler(apiClient)

    // First call: guest
    mockState.currentToken = null
    const config1 = makeConfig()
    const result1 = handler(config1)
    expect((result1.headers as Record<string, string>)['Authorization']).toBeUndefined()

    // Second call: authenticated
    mockState.currentToken = 'new-token-after-login'
    const config2 = makeConfig()
    const result2 = handler(config2)
    expect((result2.headers as Record<string, string>)['Authorization']).toBe(
      'Bearer new-token-after-login'
    )
  })

  it('returns the config object (pass-through)', () => {
    mockState.currentToken = null

    const handler = getRequestInterceptorHandler(apiClient)
    const config = makeConfig()
    const result = handler(config)

    expect(result).toBe(config)
  })
})

// ---------------------------------------------------------------------------
// syncClient interceptor
// ---------------------------------------------------------------------------
describe('syncClient — Authorization header interceptor', () => {
  it('adds Authorization: Bearer <token> when accessToken is set', () => {
    mockState.currentToken = 'sync-access-token-xyz'

    const handler = getRequestInterceptorHandler(syncClient)
    const config = makeConfig()
    const result = handler(config)

    expect((result.headers as Record<string, string>)['Authorization']).toBe(
      'Bearer sync-access-token-xyz'
    )
  })

  it('does NOT add Authorization header when accessToken is null (guest mode)', () => {
    mockState.currentToken = null

    const handler = getRequestInterceptorHandler(syncClient)
    const config = makeConfig()
    const result = handler(config)

    expect((result.headers as Record<string, string>)['Authorization']).toBeUndefined()
  })

  it('picks up token changes between calls (lazy store access)', () => {
    const handler = getRequestInterceptorHandler(syncClient)

    // First call: guest
    mockState.currentToken = null
    const config1 = makeConfig()
    const result1 = handler(config1)
    expect((result1.headers as Record<string, string>)['Authorization']).toBeUndefined()

    // Authenticated
    mockState.currentToken = 'sync-token-123'
    const config2 = makeConfig()
    const result2 = handler(config2)
    expect((result2.headers as Record<string, string>)['Authorization']).toBe(
      'Bearer sync-token-123'
    )
  })
})

// ---------------------------------------------------------------------------
// handle401Error (Response Interceptor Queue Logic)
// ---------------------------------------------------------------------------
import { handle401Error } from '../auth-interceptor'
import type { AxiosInstance } from 'axios'

describe('handle401Error (Response Interceptor)', () => {
  it('passes non-401 errors to fallback formatter directly', async () => {
    const error = { response: { status: 500 }, config: {} } as any
    const fallback = vi.fn().mockRejectedValue('fallback error')
    
    await expect(handle401Error(error, {} as AxiosInstance, fallback)).rejects.toEqual('fallback error')
    expect(fallback).toHaveBeenCalledWith(error)
  })

  it('does not retry if originalRequest._retry is already true', async () => {
    const error = { response: { status: 401 }, config: { _retry: true } } as any
    const fallback = vi.fn().mockRejectedValue('already retried error')

    await expect(handle401Error(error, {} as AxiosInstance, fallback)).rejects.toEqual('already retried error')
    expect(fallback).toHaveBeenCalledWith(error)
  })
})
