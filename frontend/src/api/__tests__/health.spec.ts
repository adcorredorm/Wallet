/**
 * health.spec.ts
 *
 * Tests for checkBackendHealth() in src/api/health.ts.
 * Mocks axios.get directly — no baseURL, no interceptors.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }))

vi.mock('axios', () => ({
  default: { get: mockGet },
}))

import { checkBackendHealth } from '../health'

describe('checkBackendHealth', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('returns true when /health responds 200', async () => {
    mockGet.mockResolvedValueOnce({ status: 200 })
    expect(await checkBackendHealth()).toBe(true)
    expect(mockGet).toHaveBeenCalledWith('/health', { timeout: 5000 })
  })

  it('returns false when /health responds 5xx', async () => {
    mockGet.mockRejectedValueOnce({ response: { status: 503 } })
    expect(await checkBackendHealth()).toBe(false)
  })

  it('returns false on network error and never rejects', async () => {
    mockGet.mockRejectedValueOnce(new Error('Network Error'))
    expect(await checkBackendHealth()).toBe(false)
  })

  it('returns false on timeout', async () => {
    mockGet.mockRejectedValueOnce({ code: 'ECONNABORTED', message: 'timeout' })
    expect(await checkBackendHealth()).toBe(false)
  })
})
