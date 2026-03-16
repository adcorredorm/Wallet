/**
 * API Client Configuration
 *
 * Why Axios?
 * - Interceptors for centralized error handling
 * - Automatic JSON transformation
 * - Request/response middleware support
 * - Better browser compatibility than fetch
 */

import axios, { type AxiosInstance, type AxiosError } from 'axios'
import type { ApiResponse, ApiError } from '@/types'

// Get API base URL from environment variables
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1'

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,  // 10 seconds timeout for mobile networks
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// Request interceptor — inject Authorization: Bearer <accessToken> from authStore.
//
// Why call useAuthStore() INSIDE the callback (lazy access)?
// Pinia requires that a store is only accessed after createPinia() has been
// called and setActivePinia() has been executed. At module evaluation time
// (when this file is first imported), the Pinia instance may not yet be
// mounted — particularly in tests or during the app boot sequence before
// main.ts calls app.use(pinia). Calling useAuthStore() lazily (inside the
// interceptor function) defers the store access to the moment of each request,
// when Pinia is guaranteed to be ready.
//
// Why not set the header at the Axios instance level (in the `headers` config)?
// The access token is dynamic — it changes when the user logs in or the token
// is refreshed. An interceptor is re-evaluated on every request, so it always
// picks up the latest in-memory value without needing to recreate the client.
//
// Why ESM static import but lazy function call?
// In Vite/ESM environments, require() is not available. The solution is to
// import the module statically (which is fine — just resolves the module graph)
// but call useAuthStore() lazily inside the callback. The module-level import
// does NOT call useAuthStore(); it only imports the function reference.
// The actual store access happens at request time via useAuthStore().
import { useAuthStore as _useAuthStore } from '@/stores/auth'

apiClient.interceptors.request.use(
  (config) => {
    // Lazy call: useAuthStore() is invoked here (at request time), not at
    // module initialization time. Pinia is guaranteed to be active by now.
    const authStore = _useAuthStore()
    const token = authStore.accessToken
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - Handle errors globally
apiClient.interceptors.response.use(
  (response) => {
    // Unwrap the API response structure { success: true, data: ... }
    if (response.data && 'data' in response.data) {
      const innerData = response.data.data
      // Handle paginated responses: { items: [...], pagination: {...} }
      if (innerData && typeof innerData === 'object' && 'items' in innerData) {
        return innerData.items
      }
      return innerData
    }
    return response.data
  },
  (error: AxiosError) => {
    // Transform axios error into our ApiError format
    const apiError: ApiError = {
      message: 'Ha ocurrido un error',
      status: error.response?.status || 500,
      errors: {}
    }

    if (error.response) {
      // Server responded with error status
      const data = error.response.data as any
      apiError.message = data.message || error.message
      apiError.errors = data.errors || {}
    } else if (error.request) {
      // Request made but no response received
      apiError.message = 'No se pudo conectar con el servidor'
    } else {
      // Something else happened
      apiError.message = error.message
    }

    return Promise.reject(apiError)
  }
)

export default apiClient
export type { ApiResponse, ApiError }
