/**
 * auth.spec.ts
 *
 * Tests for useAuthStore — the central auth store.
 *
 * Strategy:
 * - Mock @/api/auth (no real HTTP calls)
 * - Mock @/offline/auth-db (no real IndexedDB — we test authStore logic,
 *   not AuthDB internals which have their own spec)
 * - Use createPinia() with stubActions: false so real store actions run
 *
 * What we test:
 * 1. loginWithGoogle — sets accessToken + user in memory, calls setRefreshToken + setLastUserId
 * 2. refresh — success path: updates tokens; failure path: clears state
 * 3. logout — always clears state regardless of server response; calls deleteRefreshToken
 * 4. initializeFromStorage / refresh — returns false when no refresh_token stored
 * 5. isAuthenticated computed — reflects accessToken + user state
 * 6. JWT decoding — user object is extracted from the JWT payload
 * 7. Security invariants — accessToken is NEVER put into AuthDB
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// ---------------------------------------------------------------------------
// vi.hoisted() — creates spy references before vi.mock factories are hoisted.
// This avoids the "Cannot access before initialization" error when factories
// reference variables declared with const/let.
// ---------------------------------------------------------------------------
const {
  mockPostAuthGoogle,
  mockPostAuthRefresh,
  mockPostAuthLogout,
  mockGetRefreshToken,
  mockSetRefreshToken,
  mockDeleteRefreshToken,
  mockGetLastUserId,
  mockSetLastUserId,
  mockDeleteLastUserId,
  mockDbDelete,
  mockDbOpen,
} = vi.hoisted(() => ({
  mockPostAuthGoogle: vi.fn(),
  mockPostAuthRefresh: vi.fn(),
  mockPostAuthLogout: vi.fn(),
  mockGetRefreshToken: vi.fn(),
  mockSetRefreshToken: vi.fn(),
  mockDeleteRefreshToken: vi.fn(),
  mockGetLastUserId: vi.fn(),
  mockSetLastUserId: vi.fn(),
  mockDeleteLastUserId: vi.fn(),
  mockDbDelete: vi.fn(),
  mockDbOpen: vi.fn(),
}))

vi.mock('@/api/auth', () => ({
  postAuthGoogle: mockPostAuthGoogle,
  postAuthRefresh: mockPostAuthRefresh,
  postAuthLogout: mockPostAuthLogout,
}))

vi.mock('@/offline/auth-db', () => ({
  getRefreshToken: mockGetRefreshToken,
  setRefreshToken: mockSetRefreshToken,
  deleteRefreshToken: mockDeleteRefreshToken,
  getLastUserId: mockGetLastUserId,
  setLastUserId: mockSetLastUserId,
  deleteLastUserId: mockDeleteLastUserId,
  clearAuthDb: vi.fn(),
}))

vi.mock('@/offline/db', () => ({
  db: {
    delete: mockDbDelete,
    open: mockDbOpen,
  },
}))

// Import AFTER mocks
import { useAuthStore } from '../auth'

// ---------------------------------------------------------------------------
// JWT fixture helpers
//
// Build a minimal valid-looking JWT with the given payload.
// We don't sign it — the store never verifies the signature.
//
// Why TextEncoder + Uint8Array + fromCharCode for base64url encoding?
// btoa() in browsers/Node only handles Latin-1 (bytes 0-255). For UTF-8
// strings like 'Ángel', the character 'Á' (U+00C1) encodes to two bytes
// in UTF-8 (0xC3 0x81). btoa() would truncate or corrupt multi-byte chars.
// The correct approach is: JSON.stringify → TextEncoder (UTF-8 bytes) →
// convert to binary string → btoa(). This matches what real JWT servers
// produce when encoding non-ASCII names.
// ---------------------------------------------------------------------------
function buildJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))

  // Encode payload as UTF-8 bytes, then base64url
  const jsonStr = JSON.stringify(payload)
  const bytes = new TextEncoder().encode(jsonStr)
  const binaryStr = Array.from(bytes).map(b => String.fromCharCode(b)).join('')
  const payloadB64 = btoa(binaryStr)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')

  return `${header}.${payloadB64}.fake-signature`
}

const testJwt = buildJwt({
  sub: 'user-abc-123',
  email: 'angel@example.com',
  name: 'Angel Test',
  iat: 1700000000,
  exp: 1700086400,
})

const googleApiResponse = {
  access_token: testJwt,
  refresh_token: 'opaque-refresh-token',
  user: { id: 'user-abc-123', email: 'angel@example.com', name: 'Angel Test' },
  is_new_user: false,
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------
beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()

  // Default: no refresh token stored
  mockGetRefreshToken.mockResolvedValue(undefined)
  mockSetRefreshToken.mockResolvedValue(undefined)
  mockDeleteRefreshToken.mockResolvedValue(undefined)
  mockGetLastUserId.mockResolvedValue(undefined)
  mockSetLastUserId.mockResolvedValue(undefined)
  mockDeleteLastUserId.mockResolvedValue(undefined)

  // Default: WalletDB operations succeed silently
  mockDbDelete.mockResolvedValue(undefined)
  mockDbOpen.mockResolvedValue(undefined)
})

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------
describe('initial state', () => {
  it('starts unauthenticated with null accessToken and user', () => {
    const store = useAuthStore()
    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// loginWithGoogle
// ---------------------------------------------------------------------------
describe('loginWithGoogle', () => {
  it('sets accessToken in memory after successful login', async () => {
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)

    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    expect(store.accessToken).toBe(testJwt)
  })

  it('extracts user object from JWT payload', async () => {
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)

    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    expect(store.user).toEqual({
      id: 'user-abc-123',
      email: 'angel@example.com',
      name: 'Angel Test',
    })
  })

  it('stores refresh_token in AuthDB via setRefreshToken', async () => {
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)

    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    expect(mockSetRefreshToken).toHaveBeenCalledOnce()
    expect(mockSetRefreshToken).toHaveBeenCalledWith('opaque-refresh-token')
  })

  it('does NOT call setLastUserId — that is deferred to handlePostLogin', async () => {
    // last_user_id is set by usePostLoginFlow.handlePostLogin AFTER login,
    // not by loginWithGoogle itself. This prevents the user-switch detection
    // from seeing the new ID before it can compare with the old one.
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)

    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    expect(mockSetLastUserId).not.toHaveBeenCalled()
  })

  it('sets isAuthenticated to true', async () => {
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)

    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    expect(store.isAuthenticated).toBe(true)
  })

  it('returns the full API response including is_new_user', async () => {
    const newUserResponse = { ...googleApiResponse, is_new_user: true }
    mockPostAuthGoogle.mockResolvedValueOnce(newUserResponse)

    const store = useAuthStore()
    const result = await store.loginWithGoogle('google-id-token')

    expect(result.is_new_user).toBe(true)
  })

  it('propagates API errors to the caller', async () => {
    mockPostAuthGoogle.mockRejectedValueOnce(new Error('Invalid id_token'))

    const store = useAuthStore()
    await expect(store.loginWithGoogle('bad-token')).rejects.toThrow('Invalid id_token')
  })

  it('does NOT store accessToken in AuthDB (security invariant)', async () => {
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)

    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    // setRefreshToken must never be called with the access_token value
    for (const call of mockSetRefreshToken.mock.calls) {
      expect(call[0]).not.toBe(testJwt)
    }
  })
})

// ---------------------------------------------------------------------------
// refresh
// ---------------------------------------------------------------------------
describe('refresh', () => {
  it('returns false when no refresh_token is in AuthDB', async () => {
    mockGetRefreshToken.mockResolvedValueOnce(undefined)

    const store = useAuthStore()
    const result = await store.refresh()

    expect(result).toBe(false)
    expect(store.isAuthenticated).toBe(false)
  })

  it('updates accessToken in memory on successful refresh', async () => {
    const newJwt = buildJwt({ sub: 'user-abc-123', email: 'angel@example.com', name: 'Angel Test' })
    mockGetRefreshToken.mockResolvedValueOnce('stored-refresh-token')
    mockPostAuthRefresh.mockResolvedValueOnce({
      access_token: newJwt,
      refresh_token: 'new-rotated-refresh-token',
    })
    mockSetRefreshToken.mockResolvedValue(undefined)

    const store = useAuthStore()
    const result = await store.refresh()

    expect(result).toBe(true)
    expect(store.accessToken).toBe(newJwt)
    expect(store.user?.email).toBe('angel@example.com')
  })

  it('rotates refresh_token in AuthDB after successful refresh', async () => {
    const newJwt = buildJwt({ sub: 'user-abc-123', email: 'angel@example.com', name: 'Angel Test' })
    mockGetRefreshToken.mockResolvedValueOnce('stored-refresh-token')
    mockPostAuthRefresh.mockResolvedValueOnce({
      access_token: newJwt,
      refresh_token: 'new-rotated-refresh-token',
    })

    const store = useAuthStore()
    await store.refresh()

    expect(mockSetRefreshToken).toHaveBeenCalledWith('new-rotated-refresh-token')
  })

  it('returns false and clears state when refresh_token is expired (401)', async () => {
    mockGetRefreshToken.mockResolvedValueOnce('expired-token')
    mockPostAuthRefresh.mockRejectedValueOnce(
      Object.assign(new Error('Unauthorized'), { response: { status: 401 } })
    )

    const store = useAuthStore()
    const result = await store.refresh()

    expect(result).toBe(false)
    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
  })

  it('deletes refresh_token from AuthDB when server rejects with 401', async () => {
    mockGetRefreshToken.mockResolvedValueOnce('expired-token')
    mockPostAuthRefresh.mockRejectedValueOnce(
      Object.assign(new Error('Unauthorized'), { response: { status: 401 } })
    )

    const store = useAuthStore()
    await store.refresh()

    expect(mockDeleteRefreshToken).toHaveBeenCalledOnce()
  })

  it('keeps refresh_token when refresh fails with a network error (no server response)', async () => {
    // Simulates wifi dropout, timeout, DNS failure — no response from server.
    // The refresh token is still valid; we should not delete it.
    mockGetRefreshToken.mockResolvedValueOnce('valid-refresh-token')
    mockPostAuthRefresh.mockRejectedValueOnce(
      Object.assign(new Error('Network Error'), { response: undefined })
    )

    const store = useAuthStore()
    const result = await store.refresh()

    expect(result).toBe(false)
    expect(store.accessToken).toBeNull()   // state cleared (no valid session in memory)
    expect(store.user).toBeNull()
    expect(mockDeleteRefreshToken).not.toHaveBeenCalled()  // token preserved for retry
  })

  it('keeps refresh_token when refresh fails with a 500 server error', async () => {
    // 5xx = transient server problem, token is still valid.
    mockGetRefreshToken.mockResolvedValueOnce('valid-refresh-token')
    mockPostAuthRefresh.mockRejectedValueOnce(
      Object.assign(new Error('Internal Server Error'), { response: { status: 500 } })
    )

    const store = useAuthStore()
    const result = await store.refresh()

    expect(result).toBe(false)
    expect(mockDeleteRefreshToken).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// logout
// ---------------------------------------------------------------------------
describe('logout', () => {
  it('clears accessToken and user from memory', async () => {
    // First log in
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)
    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')
    expect(store.isAuthenticated).toBe(true)

    // Then log out
    mockGetRefreshToken.mockResolvedValueOnce('opaque-refresh-token')
    mockPostAuthLogout.mockResolvedValueOnce(undefined)
    await store.logout()

    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('deletes refresh_token from AuthDB', async () => {
    mockGetRefreshToken.mockResolvedValueOnce('opaque-refresh-token')
    mockPostAuthLogout.mockResolvedValueOnce(undefined)

    const store = useAuthStore()
    await store.logout()

    expect(mockDeleteRefreshToken).toHaveBeenCalledOnce()
  })

  it('still clears local state even when server returns an error', async () => {
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)
    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    // Server fails but logout should still clear local state
    mockGetRefreshToken.mockResolvedValueOnce('opaque-refresh-token')
    mockPostAuthLogout.mockRejectedValueOnce(new Error('500 Internal Server Error'))
    await store.logout()

    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
    expect(mockDeleteRefreshToken).toHaveBeenCalledOnce()
  })

  it('works even when no refresh_token exists (guest logout)', async () => {
    mockGetRefreshToken.mockResolvedValueOnce(undefined)

    const store = useAuthStore()
    await expect(store.logout()).resolves.not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// clearLocalAuthState
// ---------------------------------------------------------------------------
describe('clearLocalAuthState', () => {
  it('clears accessToken and user without hitting the server', async () => {
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)
    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')
    expect(store.isAuthenticated).toBe(true)

    store.clearLocalAuthState()

    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
    expect(mockPostAuthLogout).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// logout with clearLocalData
// ---------------------------------------------------------------------------
describe('logout — clearLocalData parameter', () => {
  it('logout(true) deletes and re-opens WalletDB', async () => {
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)
    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    mockGetRefreshToken.mockResolvedValueOnce('opaque-refresh-token')
    mockPostAuthLogout.mockResolvedValueOnce(undefined)
    await store.logout(true)

    expect(mockDbDelete).toHaveBeenCalledOnce()
    expect(mockDbOpen).toHaveBeenCalledOnce()
  })

  it('logout(false) does NOT touch WalletDB', async () => {
    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)
    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    mockGetRefreshToken.mockResolvedValueOnce('opaque-refresh-token')
    mockPostAuthLogout.mockResolvedValueOnce(undefined)
    await store.logout(false)

    expect(mockDbDelete).not.toHaveBeenCalled()
    expect(mockDbOpen).not.toHaveBeenCalled()
  })

  it('logout() without argument does NOT touch WalletDB (default false)', async () => {
    mockGetRefreshToken.mockResolvedValueOnce('opaque-refresh-token')
    mockPostAuthLogout.mockResolvedValueOnce(undefined)

    const store = useAuthStore()
    await store.logout()

    expect(mockDbDelete).not.toHaveBeenCalled()
    expect(mockDbOpen).not.toHaveBeenCalled()
  })

  it('logout(true) still clears auth state even if WalletDB.delete() throws', async () => {
    mockGetRefreshToken.mockResolvedValueOnce('opaque-refresh-token')
    mockPostAuthLogout.mockResolvedValueOnce(undefined)
    mockDbDelete.mockRejectedValueOnce(new Error('IndexedDB error'))

    mockPostAuthGoogle.mockResolvedValueOnce(googleApiResponse)
    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    await expect(store.logout(true)).resolves.not.toThrow()
    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// initializeFromStorage
// ---------------------------------------------------------------------------
describe('initializeFromStorage', () => {
  it('with no stored token: stays as guest without calling refresh API', async () => {
    mockGetRefreshToken.mockResolvedValueOnce(undefined)

    const store = useAuthStore()
    await store.initializeFromStorage()

    expect(mockPostAuthRefresh).not.toHaveBeenCalled()
    expect(store.isAuthenticated).toBe(false)
  })

  it('with a stored token: calls refresh() and updates auth state on success', async () => {
    const newJwt = buildJwt({ sub: 'user-abc-123', email: 'angel@example.com', name: 'Angel Test' })
    // initializeFromStorage() calls getRefreshToken() once to check existence,
    // then refresh() calls getRefreshToken() again to get the token value.
    // Both calls must return the token.
    mockGetRefreshToken.mockResolvedValue('stored-refresh-token')
    mockPostAuthRefresh.mockResolvedValueOnce({
      access_token: newJwt,
      refresh_token: 'new-rotated-refresh-token',
    })
    mockSetRefreshToken.mockResolvedValue(undefined)

    const store = useAuthStore()
    await store.initializeFromStorage()

    expect(mockPostAuthRefresh).toHaveBeenCalledOnce()
    expect(store.isAuthenticated).toBe(true)
    expect(store.user?.email).toBe('angel@example.com')
  })

  it('with an expired token: stays as guest after refresh failure (no throw)', async () => {
    mockGetRefreshToken.mockResolvedValueOnce('expired-refresh-token')
    mockPostAuthRefresh.mockRejectedValueOnce(
      Object.assign(new Error('Unauthorized'), { response: { status: 401 } })
    )

    const store = useAuthStore()
    await expect(store.initializeFromStorage()).resolves.not.toThrow()
    expect(store.isAuthenticated).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// JWT decoding edge cases
// ---------------------------------------------------------------------------
describe('JWT decoding', () => {
  it('handles JWT payload with UTF-8 characters in name (accents)', async () => {
    const jwtWithAccents = buildJwt({
      sub: 'user-es-1',
      email: 'angel@example.com',
      name: 'Ángel Corredor',
    })
    mockPostAuthGoogle.mockResolvedValueOnce({
      ...googleApiResponse,
      access_token: jwtWithAccents,
    })

    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    expect(store.user?.name).toBe('Ángel Corredor')
  })

  it('sets user to null if JWT payload is missing required fields', async () => {
    const incompleteJwt = buildJwt({ sub: 'user-1' }) // missing email and name
    mockPostAuthGoogle.mockResolvedValueOnce({
      ...googleApiResponse,
      access_token: incompleteJwt,
    })

    const store = useAuthStore()
    await store.loginWithGoogle('google-id-token')

    // User should be null because name and email are missing
    expect(store.user).toBeNull()
  })
})
