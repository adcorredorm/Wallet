/**
 * Dedicated Axios instance for SyncManager incremental sync requests.
 *
 * Why a separate client?
 * The default apiClient response interceptor unwraps { success: true, data: ... }
 * and discards the raw AxiosResponse — including headers. The SyncManager needs
 * access to the X-Sync-Cursor response header, which requires the full response.
 *
 * validateStatus allows 304 without throwing (default Axios treats 304 as error).
 */
import axios from 'axios'
import { API_BASE_URL } from './index'

export const syncClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  validateStatus: (status) => (status >= 200 && status < 300) || status === 304,
})

// Request interceptor — inject Authorization: Bearer <accessToken> from authStore.
//
// Why duplicate the interceptor instead of sharing it?
// syncClient is a completely independent Axios instance. Interceptors are
// per-instance — registering one on apiClient does NOT affect syncClient.
// The SyncManager uses syncClient exclusively for incremental sync requests
// (needs raw AxiosResponse + X-Sync-Cursor header). Both clients must carry
// the Authorization header for the backend to authenticate the requests.
//
// Why ESM static import but lazy function call?
// Same reason as in index.ts: we import useAuthStore at module level (just
// a function reference), but call useAuthStore() INSIDE the interceptor
// callback so Pinia is guaranteed to be initialized at that point.
import { useAuthStore } from '@/stores/auth'

syncClient.interceptors.request.use(
  (config) => {
    // Lazy call: invoked at request time, not at module load time.
    const authStore = useAuthStore()
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
