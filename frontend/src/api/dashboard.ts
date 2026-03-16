/**
 * Dashboard API Client
 * Handles requests for aggregated dashboard data
 */

import apiClient from './index'
export const dashboardApi = {
  /**
   * Get net worth (total patrimonio neto across all accounts)
   * This is calculated by summing all account balances
   */
  getNetWorth(): Promise<{ patrimonio_neto: number }> {
    return apiClient.get('/dashboard/net-worth')
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
