/**
 * Application Constants
 */

// Account types
export const ACCOUNT_TYPES = [
  { value: 'debit', label: 'Débito' },
  { value: 'credit', label: 'Crédito' },
  { value: 'cash', label: 'Efectivo' }
] as const

// Category types
export const CATEGORY_TYPES = [
  { value: 'income', label: 'Ingreso' },
  { value: 'expense', label: 'Gasto' },
  { value: 'both', label: 'Mixto' }
] as const

// Transaction types
export const TRANSACTION_TYPES = [
  { value: 'income', label: 'Ingreso' },
  { value: 'expense', label: 'Gasto' }
] as const

// Full currency data — use this wherever the symbol or full name is needed
export const SUPPORTED_CURRENCIES = [
  { code: 'COP', name: 'Peso Colombiano',  symbol: '$'  },
  { code: 'USD', name: 'Dólar Americano',  symbol: '$'  },
  { code: 'EUR', name: 'Euro',             symbol: '€'  },
  { code: 'BRL', name: 'Real Brasileño',   symbol: 'R$' },
  { code: 'JPY', name: 'Yen Japonés',      symbol: '¥'  },
  { code: 'ARS', name: 'Peso Argentino',   symbol: '$'  },
  { code: 'GBP', name: 'Libra Esterlina',  symbol: '£'  },
  { code: 'BTC', name: 'Bitcoin',          symbol: '₿'  },
  { code: 'ETH', name: 'Ethereum',         symbol: 'Ξ'  },
] as const

// BaseSelect-compatible list — value/label shape consumed by AccountForm and any other dropdown
export const CURRENCIES = SUPPORTED_CURRENCIES.map(c => ({
  value: c.code,
  label: `${c.code} - ${c.name}`,
}))

// Common category icons (using emoji for simplicity)
export const CATEGORY_ICONS = [
  '💰', '🏠', '🍔', '🚗', '🎬', '🛒',
  '💊', '✈️', '📚', '👕', '⚡', '📱',
  '☕', '🎮', '💳', '🏦', '🎁', '🔧'
] as const

// Category colors
export const CATEGORY_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
  '#6366f1', // indigo
] as const

// Date range presets
export const DATE_RANGES = [
  { label: 'Hoy', value: 'today' },
  { label: 'Esta semana', value: 'this_week' },
  { label: 'Este mes', value: 'this_month' },
  { label: 'Últimos 30 días', value: 'last_30_days' },
  { label: 'Últimos 90 días', value: 'last_90_days' },
  { label: 'Este año', value: 'this_year' },
  { label: 'Personalizado', value: 'custom' }
] as const

// Pagination
export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const

// Toast durations (milliseconds)
export const TOAST_DURATION = {
  SHORT: 2000,
  NORMAL: 3000,
  LONG: 5000
} as const

// Breakpoints (matches Tailwind config)
export const BREAKPOINTS = {
  mobile: 320,
  tablet: 768,
  desktop: 1024,
  largeDesktop: 1280
} as const
