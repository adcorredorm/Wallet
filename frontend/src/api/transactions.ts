/**
 * Transactions API Client
 * Handles all HTTP requests related to income/expense transactions
 */

import apiClient from './index'
import type {
  Transaction,
  CreateTransactionDto,
  UpdateTransactionDto,
  TransactionFilters,
  PaginatedResponse
} from '@/types'

export const transactionsApi = {
  /**
   * Get all transactions with optional filters
   * @param filters - Query filters (account, category, date range, etc)
   */
  getAll(filters?: TransactionFilters): Promise<Transaction[]> {
    return apiClient.get('/transactions', { params: filters })
  },

  /**
   * Get paginated transactions
   * @param filters - Query filters with pagination
   */
  getPaginated(filters?: TransactionFilters): Promise<PaginatedResponse<Transaction>> {
    return apiClient.get('/transactions/paginated', { params: filters })
  },

  /**
   * Get a single transaction by ID
   * @param id - Transaction UUID
   */
  getById(id: string): Promise<Transaction> {
    return apiClient.get(`/transactions/${id}`)
  },

  /**
   * Get transactions for a specific account
   * @param accountId - Account UUID
   * @param filters - Additional filters
   */
  getByAccount(accountId: string, filters?: TransactionFilters): Promise<Transaction[]> {
    const params = { ...filters, account_id: accountId }
    return apiClient.get('/transactions', { params })
  },

  /**
   * Create a new transaction
   * @param data - Transaction creation data
   */
  create(data: CreateTransactionDto): Promise<Transaction> {
    return apiClient.post('/transactions', data)
  },

  /**
   * Update an existing transaction
   * @param id - Transaction UUID
   * @param data - Transaction update data
   */
  update(id: string, data: UpdateTransactionDto): Promise<Transaction> {
    return apiClient.put(`/transactions/${id}`, data)
  },

  /**
   * Delete a transaction
   * @param id - Transaction UUID
   */
  delete(id: string): Promise<void> {
    return apiClient.delete(`/transactions/${id}`)
  }
}
