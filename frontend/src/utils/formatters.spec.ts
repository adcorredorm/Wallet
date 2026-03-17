/**
 * formatters.spec.ts
 *
 * Unit tests for every exported function in src/utils/formatters.ts.
 *
 * Clock management:
 * formatDateRelative() compares the input date against new Date() at call
 * time to decide "Hoy" / "Ayer" / formatted date. To make those tests
 * deterministic we freeze the system clock to a known UTC instant
 * (2024-06-15T12:00:00.000Z) using vi.useFakeTimers() + vi.setSystemTime().
 * The rest of the file does NOT use fake timers — only the describe block that
 * needs them restores real timers in afterEach.
 *
 * Locale note:
 * formatCurrency uses the 'en-US' locale internally.
 * formatNumber uses the 'es-ES' locale (period as thousand separator, comma
 * as decimal separator).
 * Tests assert the expected locale-specific output strings produced by jsdom's
 * Intl implementation (which inherits from V8 via Node.js).
 */

import {
  formatCurrency,
  formatNumber,
  parseFormattedNumber,
  formatDate,
  formatDateRelative,
  formatDateForInput,
  getMonthName,
  truncate,
  getInitials,
  formatAccountType,
  formatCategoryType,
} from './formatters'

// ---------------------------------------------------------------------------
// formatCurrency
// ---------------------------------------------------------------------------
describe('formatCurrency', () => {
  it('formats USD by default with two decimal places', () => {
    expect(formatCurrency(1234.5)).toBe('$1,234.50')
  })

  it('formats EUR correctly', () => {
    expect(formatCurrency(9.99, 'EUR')).toBe('€9.99')
  })

  it('formats a zero amount', () => {
    expect(formatCurrency(0, 'USD')).toBe('$0.00')
  })

  it('formats a negative amount', () => {
    expect(formatCurrency(-50, 'USD')).toBe('-$50.00')
  })

  it('uses compact notation for amounts >= 1000 when compact=true', () => {
    const result = formatCurrency(1500, 'USD', true)
    // Compact notation produces "1.5K" style — exact string depends on Intl
    expect(result).toMatch(/1[.,]?5K/)
  })

  it('does NOT use compact notation for amounts < 1000 even when compact=true', () => {
    const result = formatCurrency(999, 'USD', true)
    expect(result).toBe('$999.00')
  })

  it('falls back to USD when an invalid currency code is provided', () => {
    // Empty string triggers the fallback inside the function
    const result = formatCurrency(10, '')
    expect(result).toBe('$10.00')
  })
})

// ---------------------------------------------------------------------------
// formatNumber
// ---------------------------------------------------------------------------
describe('formatNumber', () => {
  it('formats with 2 decimal places by default using es-ES locale', () => {
    // es-ES: period = thousand sep, comma = decimal sep
    expect(formatNumber(1234.56)).toBe('1234,56')
  })

  it('formats with a custom decimal count', () => {
    expect(formatNumber(3.14159, 3)).toBe('3,142')
  })

  it('formats zero correctly', () => {
    expect(formatNumber(0)).toBe('0,00')
  })

  it('formats a whole number with the specified decimals', () => {
    expect(formatNumber(100, 0)).toBe('100')
  })
})

// ---------------------------------------------------------------------------
// parseFormattedNumber
// ---------------------------------------------------------------------------
describe('parseFormattedNumber', () => {
  it('parses a Spanish-formatted number with thousand separators', () => {
    expect(parseFormattedNumber('1.234,56')).toBe(1234.56)
  })

  it('parses a number without thousand separators', () => {
    expect(parseFormattedNumber('9,99')).toBe(9.99)
  })

  it('parses a plain integer string', () => {
    expect(parseFormattedNumber('42')).toBe(42)
  })

  it('returns 0 for an invalid string', () => {
    expect(parseFormattedNumber('not-a-number')).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// formatDate
// ---------------------------------------------------------------------------
describe('formatDate', () => {
  it('formats an ISO date string with the default dd/MM/yyyy format', () => {
    expect(formatDate('2024-03-15')).toBe('15/03/2024')
  })

  it('formats with a custom format string', () => {
    expect(formatDate('2024-03-15', 'yyyy/MM/dd')).toBe('2024/03/15')
  })

  it('returns the original string for an invalid date', () => {
    expect(formatDate('not-a-date')).toBe('not-a-date')
  })
})

// ---------------------------------------------------------------------------
// formatDateRelative — requires a frozen clock
// ---------------------------------------------------------------------------
describe('formatDateRelative', () => {
  // Freeze time to 2024-06-15T12:00:00.000Z so "today" is 2024-06-15
  // and "yesterday" is 2024-06-14.
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-06-15T12:00:00.000Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns "Hoy" for today\'s date', () => {
    expect(formatDateRelative('2024-06-15')).toBe('Hoy')
  })

  it('returns "Ayer" for yesterday\'s date', () => {
    expect(formatDateRelative('2024-06-14')).toBe('Ayer')
  })

  it('returns a formatted date for any other date', () => {
    // date-fns format 'dd MMM yyyy' with es locale produces "10 jun 2024"
    const result = formatDateRelative('2024-06-10')
    expect(result).toMatch(/10/)
    expect(result).not.toBe('Hoy')
    expect(result).not.toBe('Ayer')
  })

  it('returns the raw string for an invalid date', () => {
    expect(formatDateRelative('bad-date')).toBe('bad-date')
  })
})

// ---------------------------------------------------------------------------
// formatDateForInput
// ---------------------------------------------------------------------------
describe('formatDateForInput', () => {
  it('converts an ISO string to yyyy-MM-dd', () => {
    expect(formatDateForInput('2024-03-15T10:30:00.000Z')).toBe('2024-03-15')
  })

  it('accepts a Date object', () => {
    expect(formatDateForInput(new Date(2024, 11, 1))).toBe('2024-12-01')
  })

  it('returns an empty string for an invalid date string', () => {
    expect(formatDateForInput('not-a-date')).toBe('')
  })
})

// ---------------------------------------------------------------------------
// getMonthName
// ---------------------------------------------------------------------------
describe('getMonthName', () => {
  it('returns the Spanish month name for January (month 1)', () => {
    expect(getMonthName(1)).toBe('enero')
  })

  it('returns the Spanish month name for June (month 6)', () => {
    expect(getMonthName(6)).toBe('junio')
  })

  it('returns the Spanish month name for December (month 12)', () => {
    expect(getMonthName(12)).toBe('diciembre')
  })
})

// ---------------------------------------------------------------------------
// truncate
// ---------------------------------------------------------------------------
describe('truncate', () => {
  it('returns the original text when it is within the limit', () => {
    expect(truncate('hello', 10)).toBe('hello')
  })

  it('returns the original text when it equals the limit exactly', () => {
    expect(truncate('hello', 5)).toBe('hello')
  })

  it('truncates and appends "..." when the text exceeds the limit', () => {
    expect(truncate('Hello, World!', 8)).toBe('Hello...')
  })

  it('uses 30 as the default maxLength', () => {
    const long = 'a'.repeat(31)
    const result = truncate(long)
    expect(result).toHaveLength(30)
    expect(result.endsWith('...')).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// getInitials
// ---------------------------------------------------------------------------
describe('getInitials', () => {
  it('returns initials from a two-word name', () => {
    expect(getInitials('Angel Corredor')).toBe('AC')
  })

  it('returns a single initial for a one-word name', () => {
    expect(getInitials('Angel')).toBe('A')
  })

  it('returns at most 2 characters for names with more than 2 words', () => {
    expect(getInitials('Juan Carlos Garcia')).toBe('JC')
  })

  it('uppercases the initials', () => {
    expect(getInitials('angel corredor')).toBe('AC')
  })
})

// ---------------------------------------------------------------------------
// formatAccountType
// ---------------------------------------------------------------------------
describe('formatAccountType', () => {
  it('maps "debit" to "Débito"', () => {
    expect(formatAccountType('debit')).toBe('Débito')
  })

  it('maps "credit" to "Crédito"', () => {
    expect(formatAccountType('credit')).toBe('Crédito')
  })

  it('maps "cash" to "Efectivo"', () => {
    expect(formatAccountType('cash')).toBe('Efectivo')
  })

  it('returns the raw value for an unknown type', () => {
    expect(formatAccountType('savings')).toBe('savings')
  })
})

// ---------------------------------------------------------------------------
// formatCategoryType
// ---------------------------------------------------------------------------
describe('formatCategoryType', () => {
  it('maps "income" to "Ingreso"', () => {
    expect(formatCategoryType('income')).toBe('Ingreso')
  })

  it('maps "expense" to "Gasto"', () => {
    expect(formatCategoryType('expense')).toBe('Gasto')
  })

  it('maps "both" to "Mixto"', () => {
    expect(formatCategoryType('both')).toBe('Mixto')
  })

  it('returns the raw value for an unknown type', () => {
    expect(formatCategoryType('unknown')).toBe('unknown')
  })
})
