/**
 * validators.spec.ts
 *
 * Unit tests for every exported function in src/utils/validators.ts.
 *
 * Why no imports for describe/it/expect?
 * vitest.config.ts sets globals: true, so Vitest injects the global test
 * helpers automatically — matching how the project is configured.
 *
 * Testing strategy:
 * - Each function gets its own describe block named after the export.
 * - Every block has at least one "returns true" and one "returns error string"
 *   case so we cover both branches of the boolean | string return type.
 * - Closure-returning factories (minLength, maxLength, maxDecimals) are called
 *   once in beforeEach (or inline) to produce a reusable validator, then the
 *   returned validator is exercised on boundary and non-boundary inputs.
 * - Date-dependent tests (notFutureDate) use a fixed past date string and a
 *   future date string rather than vi.useFakeTimers so the test is time-stable
 *   without clock manipulation (the logic only compares to "today at 23:59:59",
 *   so a year-1900 past date and year-9999 future date are always safe).
 */

import {
  required,
  minLength,
  maxLength,
  positiveNumber,
  nonNegative,
  maxDecimals,
  email,
  currencyCode,
  hexColor,
  notFutureDate,
  dateRange,
  validate,
} from './validators'

// ---------------------------------------------------------------------------
// required
// ---------------------------------------------------------------------------
describe('required', () => {
  it('returns true for a non-empty string', () => {
    expect(required('hello')).toBe(true)
  })

  it('returns true for a string with only content (no trim false-positive)', () => {
    expect(required('  a  ')).toBe(true)
  })

  it('returns error string for an empty string', () => {
    expect(required('')).toBe('Este campo es obligatorio')
  })

  it('returns error string for a whitespace-only string', () => {
    expect(required('   ')).toBe('Este campo es obligatorio')
  })

  it('returns true for a non-empty array', () => {
    expect(required([1, 2, 3])).toBe(true)
  })

  it('returns error string for an empty array', () => {
    expect(required([])).toBe('Este campo es obligatorio')
  })

  it('returns true for a truthy non-string, non-array value', () => {
    expect(required(42)).toBe(true)
  })

  it('returns error string for null', () => {
    expect(required(null)).toBe('Este campo es obligatorio')
  })

  it('returns error string for undefined', () => {
    expect(required(undefined)).toBe('Este campo es obligatorio')
  })

  it('returns error string for 0', () => {
    // 0 is falsy — required treats it as "empty"
    expect(required(0)).toBe('Este campo es obligatorio')
  })
})

// ---------------------------------------------------------------------------
// minLength (factory)
// ---------------------------------------------------------------------------
describe('minLength', () => {
  const atLeast5 = minLength(5)

  it('returns true when string length equals the minimum', () => {
    expect(atLeast5('abcde')).toBe(true)
  })

  it('returns true when string length exceeds the minimum', () => {
    expect(atLeast5('abcdef')).toBe(true)
  })

  it('returns error string when string is shorter than minimum', () => {
    expect(atLeast5('abc')).toBe('Mínimo 5 caracteres')
  })

  it('interpolates the min value into the error string', () => {
    const atLeast10 = minLength(10)
    expect(atLeast10('short')).toBe('Mínimo 10 caracteres')
  })
})

// ---------------------------------------------------------------------------
// maxLength (factory)
// ---------------------------------------------------------------------------
describe('maxLength', () => {
  const atMost8 = maxLength(8)

  it('returns true when string length equals the maximum', () => {
    expect(atMost8('12345678')).toBe(true)
  })

  it('returns true when string length is below the maximum', () => {
    expect(atMost8('hello')).toBe(true)
  })

  it('returns error string when string exceeds the maximum', () => {
    expect(atMost8('123456789')).toBe('Máximo 8 caracteres')
  })

  it('interpolates the max value into the error string', () => {
    const atMost3 = maxLength(3)
    expect(atMost3('toolong')).toBe('Máximo 3 caracteres')
  })
})

// ---------------------------------------------------------------------------
// positiveNumber
// ---------------------------------------------------------------------------
describe('positiveNumber', () => {
  it('returns true for a positive number', () => {
    expect(positiveNumber(5)).toBe(true)
  })

  it('returns true for a positive number string', () => {
    expect(positiveNumber('3.14')).toBe(true)
  })

  it('returns error string for zero', () => {
    // Zero is NOT positive
    expect(positiveNumber(0)).toBe('El valor debe ser positivo')
  })

  it('returns error string for a negative number', () => {
    expect(positiveNumber(-1)).toBe('El valor debe ser positivo')
  })

  it('returns error string for a negative string', () => {
    expect(positiveNumber('-0.01')).toBe('El valor debe ser positivo')
  })
})

// ---------------------------------------------------------------------------
// nonNegative
// ---------------------------------------------------------------------------
describe('nonNegative', () => {
  it('returns true for a positive number', () => {
    expect(nonNegative(10)).toBe(true)
  })

  it('returns true for zero', () => {
    // Zero is allowed — "non-negative" means >= 0
    expect(nonNegative(0)).toBe(true)
  })

  it('returns true for a zero string', () => {
    expect(nonNegative('0')).toBe(true)
  })

  it('returns error string for a negative number', () => {
    expect(nonNegative(-5)).toBe('El valor no puede ser negativo')
  })

  it('returns error string for a negative string', () => {
    expect(nonNegative('-100')).toBe('El valor no puede ser negativo')
  })
})

// ---------------------------------------------------------------------------
// maxDecimals (factory)
// ---------------------------------------------------------------------------
describe('maxDecimals', () => {
  const twoDecimals = maxDecimals(2)

  it('returns true for an integer (zero decimals)', () => {
    expect(twoDecimals(100)).toBe(true)
  })

  it('returns true for exactly 2 decimal places', () => {
    expect(twoDecimals(1.23)).toBe(true)
  })

  it('returns true for exactly 2 decimal places as a string', () => {
    expect(twoDecimals('9.99')).toBe(true)
  })

  it('returns error string for 3 decimal places', () => {
    expect(twoDecimals(1.234)).toBe('Máximo 2 decimales')
  })

  it('returns error string for a string with excess decimals', () => {
    expect(twoDecimals('1.123')).toBe('Máximo 2 decimales')
  })

  it('interpolates the max value into the error string', () => {
    const zero = maxDecimals(0)
    expect(zero('1.5')).toBe('Máximo 0 decimales')
  })
})

// ---------------------------------------------------------------------------
// email
// ---------------------------------------------------------------------------
describe('email', () => {
  it('returns true for a valid email address', () => {
    expect(email('user@example.com')).toBe(true)
  })

  it('returns true for an email with subdomain', () => {
    expect(email('a@b.co.uk')).toBe(true)
  })

  it('returns error string for missing @', () => {
    expect(email('notanemail')).toBe('Email inválido')
  })

  it('returns error string for missing domain extension', () => {
    expect(email('user@domain')).toBe('Email inválido')
  })

  it('returns error string for empty string', () => {
    expect(email('')).toBe('Email inválido')
  })
})

// ---------------------------------------------------------------------------
// currencyCode
// ---------------------------------------------------------------------------
describe('currencyCode', () => {
  it('returns true for a valid 3-letter uppercase code', () => {
    expect(currencyCode('EUR')).toBe(true)
  })

  it('returns true for a valid 3-letter lowercase code (normalised internally)', () => {
    // The implementation calls .toUpperCase() before testing the regex
    expect(currencyCode('usd')).toBe(true)
  })

  it('returns true for a mixed-case code', () => {
    expect(currencyCode('Gbp')).toBe(true)
  })

  it('returns error string for a 2-letter code', () => {
    expect(currencyCode('EU')).toBe('Código de divisa inválido (ej: EUR, USD)')
  })

  it('returns error string for a 4-letter code', () => {
    expect(currencyCode('EURO')).toBe('Código de divisa inválido (ej: EUR, USD)')
  })

  it('returns error string for a code with digits', () => {
    expect(currencyCode('U5D')).toBe('Código de divisa inválido (ej: EUR, USD)')
  })
})

// ---------------------------------------------------------------------------
// hexColor
// ---------------------------------------------------------------------------
describe('hexColor', () => {
  it('returns true for a valid 6-digit hex color', () => {
    expect(hexColor('#FF5733')).toBe(true)
  })

  it('returns true for a lowercase hex color', () => {
    expect(hexColor('#aabbcc')).toBe(true)
  })

  it('returns error string for missing #', () => {
    expect(hexColor('FF5733')).toBe('Color hexadecimal inválido (ej: #FF5733)')
  })

  it('returns error string for a 3-digit shorthand', () => {
    // The regex requires exactly 6 hex digits — shorthand is not supported
    expect(hexColor('#FFF')).toBe('Color hexadecimal inválido (ej: #FF5733)')
  })

  it('returns error string for non-hex characters', () => {
    expect(hexColor('#ZZZZZZ')).toBe('Color hexadecimal inválido (ej: #FF5733)')
  })
})

// ---------------------------------------------------------------------------
// notFutureDate
// ---------------------------------------------------------------------------
describe('notFutureDate', () => {
  it('returns true for a past date', () => {
    expect(notFutureDate('1990-06-15')).toBe(true)
  })

  it('returns error string for a far-future date', () => {
    expect(notFutureDate('9999-12-31')).toBe('La fecha no puede ser futura')
  })
})

// ---------------------------------------------------------------------------
// dateRange
// ---------------------------------------------------------------------------
describe('dateRange', () => {
  it('returns true when start equals end', () => {
    expect(dateRange('2024-01-01', '2024-01-01')).toBe(true)
  })

  it('returns true when start is before end', () => {
    expect(dateRange('2024-01-01', '2024-12-31')).toBe(true)
  })

  it('returns error string when start is after end', () => {
    expect(dateRange('2024-12-31', '2024-01-01')).toBe(
      'La fecha inicial debe ser menor o igual a la final'
    )
  })

  it('returns true when startDate is empty (no range to validate)', () => {
    expect(dateRange('', '2024-12-31')).toBe(true)
  })

  it('returns true when endDate is empty', () => {
    expect(dateRange('2024-01-01', '')).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// validate (combinator)
// ---------------------------------------------------------------------------
describe('validate', () => {
  it('returns true when all validators pass', () => {
    const result = validate('hello', [required, minLength(3)])
    expect(result).toBe(true)
  })

  it('returns the first error and short-circuits on the first failure', () => {
    // required will fail first for an empty string
    const result = validate('', [required, minLength(3)])
    expect(result).toBe('Este campo es obligatorio')
  })

  it('continues past a passing validator to find the first failing one', () => {
    // required passes (value is non-empty) but minLength(10) fails
    const result = validate('hi', [required, minLength(10)])
    expect(result).toBe('Mínimo 10 caracteres')
  })

  it('returns true for an empty validator list', () => {
    expect(validate('anything', [])).toBe(true)
  })
})
