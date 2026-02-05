/**
 * Transfers API Client
 * Handles all HTTP requests related to account transfers
 */

import apiClient from './index'
import type {
  Transfer,
  CreateTransferDto,
  UpdateTransferDto,
  TransferFilters
} from '@/types'

export const transfersApi = {
  /**
   * Get all transfers with optional filters
   * @param filters - Query filters (account, date range, etc)
   */
  getAll(filters?: TransferFilters): Promise<Transfer[]> {
    return apiClient.get('/transfers', { params: filters })
  },

  /**
   * Get a single transfer by ID
   * @param id - Transfer UUID
   */
  getById(id: string): Promise<Transfer> {
    return apiClient.get(`/transfers/${id}`)
  },

  /**
   * Get transfers for a specific account (source or destination)
   * @param accountId - Account UUID
   * @param filters - Additional filters
   */
  getByAccount(accountId: string, filters?: TransferFilters): Promise<Transfer[]> {
    return apiClient.get(`/accounts/${accountId}/transfers`, { params: filters })
  },

  /**
   * Create a new transfer
   * @param data - Transfer creation data
   */
  create(data: CreateTransferDto): Promise<Transfer> {
    return apiClient.post('/transfers', data)
  },

  /**
   * Update an existing transfer
   * @param id - Transfer UUID
   * @param data - Transfer update data
   */
  update(id: string, data: UpdateTransferDto): Promise<Transfer> {
    return apiClient.put(`/transfers/${id}`, data)
  },

  /**
   * Delete a transfer
   * @param id - Transfer UUID
   */
  delete(id: string): Promise<void> {
    return apiClient.delete(`/transfers/${id}`)
  }
}
