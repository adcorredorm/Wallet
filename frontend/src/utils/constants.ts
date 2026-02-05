/**
 * Application Constants
 */

// Account types
export const ACCOUNT_TYPES = [
  { value: 'debito', label: 'Débito' },
  { value: 'credito', label: 'Crédito' },
  { value: 'efectivo', label: 'Efectivo' }
] as const

// Category types
export const CATEGORY_TYPES = [
  { value: 'ingreso', label: 'Ingreso' },
  { value: 'gasto', label: 'Gasto' },
  { value: 'ambos', label: 'Ambos' }
] as const

// Transaction types
export const TRANSACTION_TYPES = [
  { value: 'ingreso', label: 'Ingreso' },
  { value: 'gasto', label: 'Gasto' }
] as const

// Common currencies
export const CURRENCIES = [
  { value: 'EUR', label: 'EUR - Euro', symbol: '€' },
  { value: 'USD', label: 'USD - Dólar', symbol: '$' },
  { value: 'GBP', label: 'GBP - Libra', symbol: '£' },
  { value: 'COP', label: 'COP - Peso Colombiano', symbol: '$' }
] as const

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
