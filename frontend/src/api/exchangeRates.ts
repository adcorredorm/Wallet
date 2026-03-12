/**
 * Exchange Rates API Client
 *
 * Why a dedicated module instead of inlining the call in the store?
 * Keeping HTTP concerns here and reactive state in the store follows the same
 * separation used by every other API module in this codebase. It also makes
 * the store unit-testable without a real HTTP layer — you mock this module.
 *
 * Why does the return type match LocalExchangeRate[]?
 * The server shape and the local IndexedDB shape are identical for exchange
 * rates (no _sync_* fields). The API response carries the same fields that
 * Dexie stores, so no mapping step is needed in the store.
 */

import apiClient from './index'
import type { LocalExchangeRate } from '@/offline'

export interface ExchangeRatesResponse {
  rates: LocalExchangeRate[]
  last_updated: string | null
}

/**
 * Fetch all exchange rates from the backend.
 *
 * The axios response interceptor in api/index.ts unwraps the standard API
 * envelope { success: true, data: { rates: [...], last_updated: "..." } }
 * so this function receives the inner data object directly.
 */
export async function fetchExchangeRates(): Promise<ExchangeRatesResponse> {
  return apiClient.get('/exchange-rates')
}
