/**
 * Client-side Validation Utilities
 *
 * Why client-side validation?
 * - Immediate feedback for better UX
 * - Reduces unnecessary API calls
 * - Server still validates (security)
 *
 * Note: These are helpers for forms, NOT security validators
 * All critical validation happens on the backend
 */

/**
 * Check if value is required (not empty)
 */
export function required(value: any): boolean | string {
  if (Array.isArray(value)) {
    return value.length > 0 || 'Este campo es obligatorio'
  }
  if (typeof value === 'string') {
    return value.trim().length > 0 || 'Este campo es obligatorio'
  }
  return !!value || 'Este campo es obligatorio'
}

/**
 * Validate minimum length
 */
export function minLength(min: number) {
  return (value: string): boolean | string => {
    return value.length >= min || `Mínimo ${min} caracteres`
  }
}

/**
 * Validate maximum length
 */
export function maxLength(max: number) {
  return (value: string): boolean | string => {
    return value.length <= max || `Máximo ${max} caracteres`
  }
}

/**
 * Validate positive number
 */
export function positiveNumber(value: number | string): boolean | string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  return (num > 0) || 'El valor debe ser positivo'
}

/**
 * Validate non-negative number
 */
export function nonNegative(value: number | string): boolean | string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  return (num >= 0) || 'El valor no puede ser negativo'
}

/**
 * Validate decimal places
 */
export function maxDecimals(max: number) {
  return (value: number | string): boolean | string => {
    const strValue = value.toString()
    const decimals = strValue.includes('.') ? strValue.split('.')[1].length : 0
    return decimals <= max || `Máximo ${max} decimales`
  }
}

/**
 * Validate email format (basic)
 */
export function email(value: string): boolean | string {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(value) || 'Email inválido'
}

/**
 * Validate currency code (3 letters)
 */
export function currencyCode(value: string): boolean | string {
  const currencyRegex = /^[A-Z]{3}$/
  return currencyRegex.test(value.toUpperCase()) || 'Código de divisa inválido (ej: EUR, USD)'
}

/**
 * Validate hex color
 */
export function hexColor(value: string): boolean | string {
  const hexRegex = /^#[0-9A-Fa-f]{6}$/
  return hexRegex.test(value) || 'Color hexadecimal inválido (ej: #FF5733)'
}

/**
 * Validate date is not in future
 */
export function notFutureDate(value: string): boolean | string {
  const date = new Date(value)
  const today = new Date()
  today.setHours(23, 59, 59, 999) // End of today
  return date <= today || 'La fecha no puede ser futura'
}

/**
 * Validate date range
 */
export function dateRange(startDate: string, endDate: string): boolean | string {
  if (!startDate || !endDate) return true
  const start = new Date(startDate)
  const end = new Date(endDate)
  return start <= end || 'La fecha inicial debe ser menor o igual a la final'
}

/**
 * Combine multiple validators
 * Returns first error message or true if all pass
 */
export function validate(value: any, validators: Array<(val: any) => boolean | string>): boolean | string {
  for (const validator of validators) {
    const result = validator(value)
    if (result !== true) {
      return result
    }
  }
  return true
}
