/**
 * auth.spec.ts
 *
 * Tests for the auth API functions in src/api/auth.ts.
 *
 * Strategy: mock axios at the module level to avoid real HTTP calls.
 * We test that each function:
 *   1. Calls the correct endpoint
 *   2. Sends the correct payload
 *   3. Returns the correctly shaped response data
 *   4. Propagates errors from axios
 *
 * Why mock axios and not the publicClient instance?
 * We mock the axios.create factory so the publicClient returned internally
 * by auth.ts has a spy-able post/get method. This tests the full module
 * logic (URL derivation, payload shape) without a real network.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// ---------------------------------------------------------------------------
// Mock axios before importing the module under test
// ---------------------------------------------------------------------------

// vi.mock factories are hoisted to the top of the file before variable
// initialization — so we cannot reference `const mockPost = vi.fn()` inside
// the factory. Instead we use vi.hoisted() to create the spies at hoist time,
// making them available both inside the factory and in the test body.
const { mockPost, mockApiClientPost } = vi.hoisted(() => ({
  mockPost: vi.fn(),
  mockApiClientPost: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      post: mockPost,
    })),
  },
}))

// Mock apiClient from '@/api/index' — postOnboardingSeed uses it
vi.mock('@/api/index', () => ({
  default: {
    post: mockApiClientPost,
  },
  API_BASE_URL: 'http://localhost:5001/api/v1',
}))

// Import AFTER mocks are set up
import {
  postAuthGoogle,
  postAuthRefresh,
  postAuthLogout,
  postOnboardingSeed,
  type GoogleAuthResponse,
  type RefreshResponse,
  type OnboardingSeedResponse,
} from '../auth'

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const googleResponse: GoogleAuthResponse = {
  access_token: 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJuYW1lIjoiVGVzdCBVc2VyIn0.sig',
  refresh_token: 'refresh-token-opaque-string',
  user: { id: 'user-1', email: 'test@example.com', name: 'Test User' },
  is_new_user: false,
}

const refreshResponse: RefreshResponse = {
  access_token: 'new-access-token',
  refresh_token: 'rotated-refresh-token',
}

const seedResponse: OnboardingSeedResponse = {
  accounts_created: 2,
  categories_created: 10,
  dashboard_created: true,
}

// ---------------------------------------------------------------------------
// postAuthGoogle
// ---------------------------------------------------------------------------
describe('postAuthGoogle', () => {
  beforeEach(() => {
    mockPost.mockReset()
  })

  it('calls POST /auth/google with the id_token', async () => {
    mockPost.mockResolvedValueOnce({ data: googleResponse })

    await postAuthGoogle('google-id-token-123')

    expect(mockPost).toHaveBeenCalledOnce()
    expect(mockPost).toHaveBeenCalledWith('/auth/google', {
      id_token: 'google-id-token-123',
    })
  })

  it('returns the GoogleAuthResponse data', async () => {
    mockPost.mockResolvedValueOnce({ data: googleResponse })

    const result = await postAuthGoogle('google-id-token-123')

    expect(result).toEqual(googleResponse)
    expect(result.access_token).toBe(googleResponse.access_token)
    expect(result.is_new_user).toBe(false)
  })

  it('propagates axios errors to the caller', async () => {
    const networkError = new Error('Network Error')
    mockPost.mockRejectedValueOnce(networkError)

    await expect(postAuthGoogle('bad-token')).rejects.toThrow('Network Error')
  })
})

// ---------------------------------------------------------------------------
// postAuthRefresh
// ---------------------------------------------------------------------------
describe('postAuthRefresh', () => {
  beforeEach(() => {
    mockPost.mockReset()
  })

  it('calls POST /auth/refresh with the refresh_token', async () => {
    mockPost.mockResolvedValueOnce({ data: refreshResponse })

    await postAuthRefresh('my-refresh-token')

    expect(mockPost).toHaveBeenCalledWith('/auth/refresh', {
      refresh_token: 'my-refresh-token',
    })
  })

  it('returns the RefreshResponse data with new tokens', async () => {
    mockPost.mockResolvedValueOnce({ data: refreshResponse })

    const result = await postAuthRefresh('my-refresh-token')

    expect(result.access_token).toBe('new-access-token')
    expect(result.refresh_token).toBe('rotated-refresh-token')
  })

  it('propagates 401 errors (expired refresh token)', async () => {
    const authError = Object.assign(new Error('Unauthorized'), { response: { status: 401 } })
    mockPost.mockRejectedValueOnce(authError)

    await expect(postAuthRefresh('expired-token')).rejects.toThrow('Unauthorized')
  })
})

// ---------------------------------------------------------------------------
// postAuthLogout
// ---------------------------------------------------------------------------
describe('postAuthLogout', () => {
  beforeEach(() => {
    mockPost.mockReset()
  })

  it('calls POST /auth/logout with the refresh_token', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined, status: 204 })

    await postAuthLogout('my-refresh-token')

    expect(mockPost).toHaveBeenCalledWith('/auth/logout', {
      refresh_token: 'my-refresh-token',
    })
  })

  it('resolves without returning data (void)', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined, status: 204 })

    const result = await postAuthLogout('my-refresh-token')

    expect(result).toBeUndefined()
  })

  it('propagates server errors to the caller', async () => {
    mockPost.mockRejectedValueOnce(new Error('Server Error'))

    await expect(postAuthLogout('some-token')).rejects.toThrow('Server Error')
  })
})

// ---------------------------------------------------------------------------
// postOnboardingSeed
// ---------------------------------------------------------------------------
describe('postOnboardingSeed', () => {
  beforeEach(() => {
    mockApiClientPost.mockReset()
  })

  it('calls POST /onboarding/seed via apiClient', async () => {
    mockApiClientPost.mockResolvedValueOnce({ data: seedResponse })

    await postOnboardingSeed()

    expect(mockApiClientPost).toHaveBeenCalledWith('/onboarding/seed')
  })

  it('returns the OnboardingSeedResponse', async () => {
    mockApiClientPost.mockResolvedValueOnce({ data: seedResponse })

    const result = await postOnboardingSeed()

    expect(result.accounts_created).toBe(2)
    expect(result.categories_created).toBe(10)
    expect(result.dashboard_created).toBe(true)
  })

  it('propagates 409 conflict when seed already ran', async () => {
    const conflictError = Object.assign(new Error('Conflict'), { response: { status: 409 } })
    mockApiClientPost.mockRejectedValueOnce(conflictError)

    await expect(postOnboardingSeed()).rejects.toThrow('Conflict')
  })
})
