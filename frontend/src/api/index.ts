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
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1'

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,  // 10 seconds timeout for mobile networks
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// Request interceptor - Add auth token if needed in future
apiClient.interceptors.request.use(
  (config) => {
    // Future: Add authentication token here
    // const token = localStorage.getItem('auth_token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
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
