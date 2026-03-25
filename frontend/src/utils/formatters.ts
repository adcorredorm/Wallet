/**
 * Formatting Utilities
 *
 * Functions for formatting currency, dates, and numbers
 * Optimized for mobile display (shorter formats when needed)
 */

import { format, parseISO } from 'date-fns'
import { es } from 'date-fns/locale'

// Crypto currencies that Intl.NumberFormat does not recognise as ISO 4217 codes.
// Using a Set for O(1) membership checks.
const CRYPTO_CURRENCIES = new Set(['BTC', 'ETH'])

// Display symbols for each supported crypto ticker
const CRYPTO_SYMBOLS: Record<string, string> = {
  BTC: '₿',
  ETH: 'Ξ',
}

/**
 * Format a crypto amount for compact (mobile) display.
 * Uses K/M suffixes for large values; preserves up to `maxDecimals` significant
 * decimal places with no trailing zeros.
 */
function compactCryptoNumber(amount: number, maxDecimals: number): string {
  const abs = Math.abs(amount)
  if (abs >= 1_000_000) {
    return `${parseFloat((amount / 1_000_000).toFixed(maxDecimals))}M`
  }
  if (abs >= 1_000) {
    return `${parseFloat((amount / 1_000).toFixed(maxDecimals))}K`
  }
  return parseFloat(amount.toFixed(maxDecimals)).toString()
}

/**
 * Format currency amount with symbol
 * @param amount - The numeric amount
 * @param currency - ISO currency code (EUR, USD, COP, BTC, ETH, …)
 * @param compact - Use compact format for mobile (1.2K instead of 1,200)
 */
export function formatCurrency(
  amount: number,
  currency: string = 'USD',
  compact: boolean = false
): string {
  // Ensure currency is valid, fallback to USD
  const validCurrency = currency && currency.length === 3 ? currency.toUpperCase() : 'USD'

  // --- Crypto path ---
  // Intl.NumberFormat throws for non-ISO-4217 codes like BTC / ETH.
  // We handle them manually: up to 6 significant decimal places, no trailing zeros.
  if (CRYPTO_CURRENCIES.has(validCurrency)) {
    const symbol = CRYPTO_SYMBOLS[validCurrency] ?? validCurrency
    if (compact && Math.abs(amount) >= 1000) {
      return `${symbol}${compactCryptoNumber(amount, 6)}`
    }
    // parseFloat strips trailing zeros that toFixed(6) would leave
    const formatted = parseFloat(amount.toFixed(6)).toString()
    return `${symbol}${formatted}`
  }

  // --- Fiat path (unchanged behaviour) ---
  const options: Intl.NumberFormatOptions = {
    style: 'currency',
    currency: validCurrency,
  }

  // Don't set fractionDigits when using compact notation
  // Let the formatter decide based on the currency
  if (compact && Math.abs(amount) >= 1000) {
    options.notation = 'compact'
    options.maximumFractionDigits = 1
  } else {
    options.minimumFractionDigits = 2
    options.maximumFractionDigits = 2
  }

  try {
    return new Intl.NumberFormat('en-US', options).format(amount)
  } catch (error) {
    // Fallback to simple formatting if Intl fails
    console.error('Currency formatting error:', error)
    return `$${amount.toFixed(2)}`
  }
}

/**
 * Format number without currency symbol
 * Useful for input fields
 */
export function formatNumber(value: number, decimals: number = 2): string {
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value)
}

/**
 * Parse formatted number string to number
 * Handles Spanish number format (1.234,56)
 */
export function parseFormattedNumber(value: string): number {
  const hasDot = value.includes('.')
  const hasComma = value.includes(',')

  let cleaned: string
  if (hasDot && hasComma) {
    // Spanish format: 1.234,56 — dot=thousands, comma=decimal
    cleaned = value.replace(/\./g, '').replace(',', '.')
  } else if (hasComma && !hasDot) {
    // Spanish decimal only: 0,001
    cleaned = value.replace(',', '.')
  } else if (hasDot && !hasComma) {
    // Either Spanish thousands-only (10.000, 1.000.000) or English decimal (10.5)
    // Heuristic: if there are multiple dots, OR the last segment after a dot has
    // exactly 3 digits, it's a Spanish thousands separator — strip all dots.
    const dotCount = (value.match(/\./g) || []).length
    const afterLastDot = value.split('.').pop() ?? ''
    if (dotCount > 1 || afterLastDot.length === 3) {
      cleaned = value.replace(/\./g, '')
    } else {
      // Single dot with ≠3 digits after → English decimal (10.5, 1.50)
      cleaned = value
    }
  } else {
    // No dots, no commas: plain integer
    cleaned = value
  }
  return parseFloat(cleaned) || 0
}

/**
 * Format date for display
 * @param dateString - ISO date string
 * @param formatStr - date-fns format string
 */
export function formatDate(
  dateString: string,
  formatStr: string = 'dd/MM/yyyy'
): string {
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString
    return format(date, formatStr, { locale: es })
  } catch (error) {
    return dateString
  }
}

/**
 * Format date relative to today
 * Returns "Hoy", "Ayer", or the formatted date
 */
export function formatDateRelative(dateString: string): string {
  try {
    const date = parseISO(dateString)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    if (format(date, 'yyyy-MM-dd') === format(today, 'yyyy-MM-dd')) {
      return 'Hoy'
    } else if (format(date, 'yyyy-MM-dd') === format(yesterday, 'yyyy-MM-dd')) {
      return 'Ayer'
    } else {
      return formatDate(dateString, 'dd MMM yyyy')
    }
  } catch (error) {
    return dateString
  }
}

/**
 * Format date for input fields (YYYY-MM-DD)
 */
export function formatDateForInput(date: Date | string): string {
  try {
    const d = typeof date === 'string' ? parseISO(date) : date
    return format(d, 'yyyy-MM-dd')
  } catch (error) {
    return ''
  }
}

/**
 * Get month name
 */
export function getMonthName(month: number): string {
  const date = new Date(2000, month - 1, 1)
  return format(date, 'MMMM', { locale: es })
}

/**
 * Truncate text with ellipsis
 * Useful for mobile displays with limited space
 */
export function truncate(text: string, maxLength: number = 30): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

/**
 * Get initials from name
 * Useful for avatars
 */
export function getInitials(name: string): string {
  return name
    .split(' ')
    .map(word => word[0])
    .join('')
    .toUpperCase()
    .substring(0, 2)
}

/**
 * Format account type label
 */
export function formatAccountType(type: string): string {
  const labels: Record<string, string> = {
    'debit': 'Débito',
    'credit': 'Crédito',
    'cash': 'Efectivo'
  }
  return labels[type] || type
}

/**
 * Format category type label
 */
export function formatCategoryType(type: string): string {
  const labels: Record<string, string> = {
    'income': 'Ingreso',
    'expense': 'Gasto',
    'both': 'Mixto'
  }
  return labels[type] || type
}
