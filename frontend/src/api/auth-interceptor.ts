import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth'

let isRefreshing = false
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = []

function processQueue(error: any, token: string | null = null) {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token as string)
    }
  })
  failedQueue = []
}

export async function handle401Error(
  error: AxiosError,
  client: AxiosInstance,
  fallbackErrorFormatter: (error: AxiosError) => Promise<any> = (e) => Promise.reject(e)
) {
  const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

  if (error.response?.status === 401 && originalRequest && !originalRequest._retry && originalRequest.url !== '/auth/refresh') {
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      })
        .then(token => {
          originalRequest.headers['Authorization'] = `Bearer ${token}`
          return client(originalRequest)
        })
        .catch(err => fallbackErrorFormatter(err || error))
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      const authStore = useAuthStore()
      const success = await authStore.refresh()

      if (success && authStore.accessToken) {
        processQueue(null, authStore.accessToken)
        originalRequest.headers['Authorization'] = `Bearer ${authStore.accessToken}`
        return client(originalRequest)
      } else {
        processQueue(error, null)
        return fallbackErrorFormatter(error)
      }
    } catch (err) {
      processQueue(err, null)
      return fallbackErrorFormatter(error)
    } finally {
      isRefreshing = false
    }
  }

  return fallbackErrorFormatter(error)
}
