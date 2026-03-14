/**
 * Accounts API Client
 * Handles all HTTP requests related to financial accounts
 */

import apiClient from './index'
import type { Account, CreateAccountDto, UpdateAccountDto, AccountBalance, ApiResponse } from '@/types'

export const accountsApi = {
  /**
   * Get all accounts
   * @param active - Filter by active status (optional)
   */
  getAll(active?: boolean): Promise<Account[]> {
    // Backend expects 'include_archived' parameter (inverse of 'active')
    const params = active !== undefined ? { include_archived: !active } : {}
    return apiClient.get('/accounts', { params })
  },

  /**
   * Get a single account by ID
   * @param id - Account UUID
   */
  getById(id: string): Promise<Account> {
    return apiClient.get(`/accounts/${id}`)
  },

  /**
   * Get account balance (calculated from transactions)
   * @param id - Account UUID
   */
  getBalance(id: string): Promise<AccountBalance> {
    return apiClient.get(`/accounts/${id}/balance`)
  },

  /**
   * Create a new account
   * @param data - Account creation data
   */
  create(data: CreateAccountDto): Promise<Account> {
    return apiClient.post('/accounts', data)
  },

  /**
   * Update an existing account
   * @param id - Account UUID
   * @param data - Account update data
   */
  update(id: string, data: UpdateAccountDto): Promise<Account> {
    return apiClient.put(`/accounts/${id}`, data)
  },

  /**
   * Delete an account (soft delete - sets active to false)
   * @param id - Account UUID
   */
  delete(id: string): Promise<void> {
    return apiClient.delete(`/accounts/${id}`)
  },

  /**
   * Permanently delete an account (hard delete - removes from database)
   * @param id - Account UUID
   */
  hardDelete(id: string): Promise<void> {
    return apiClient.delete(`/accounts/${id}/permanent`)
  }
}
