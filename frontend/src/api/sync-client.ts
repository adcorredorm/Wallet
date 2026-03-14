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
