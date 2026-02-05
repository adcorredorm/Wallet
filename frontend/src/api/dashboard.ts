/**
 * Dashboard API Client
 * Handles requests for aggregated dashboard data
 */

import apiClient from './index'
import type { DashboardData, AccountBalance } from '@/types'

export const dashboardApi = {
  /**
   * Get complete dashboard data
   * Includes net worth, account balances, recent activity
   */
  getSummary(): Promise<DashboardData> {
    return apiClient.get('/dashboard')
  },

  /**
   * Get net worth (total patrimonio neto across all accounts)
   * This is calculated by summing all account balances
   */
  getNetWorth(): Promise<{ patrimonio_neto: number }> {
    return apiClient.get('/dashboard/net-worth')
  },

  /**
   * Get all account balances
   * Returns array of accounts with their calculated balances
   */
  getAccountBalances(): Promise<AccountBalance[]> {
    return apiClient.get('/dashboard/balances')
  },

  /**
   * Get monthly summary
   * @param year - Year (default: current year)
   * @param month - Month 1-12 (default: current month)
   */
  getMonthlySummary(year?: number, month?: number): Promise<{
    ingresos: number
    gastos: number
    balance: number
  }> {
    const params: any = {}
    if (year) params.year = year
    if (month) params.month = month
    return apiClient.get('/dashboard/monthly-summary', { params })
  }
}
