/**
 * accounts.spec.ts
 *
 * Unit tests for the useAccountsStore Pinia store.
 *
 * Why mock @/offline instead of @/offline/db directly?
 * accounts.ts imports from the barrel '@/offline' (not from '@/offline/db'
 * directly). Mocking the barrel is therefore sufficient and keeps the mock
 * declaration simple. If we only mocked '@/offline/db', the barrel would still
 * re-export the real Dexie singleton and the store would attempt real IndexedDB
 * operations, which do not exist in jsdom.
 *
 * Why mock @/api/accounts?
 * Several store actions call accountsApi.getAll() / getById() inside
 * fetchAllWithRevalidation / fetchByIdWithRevalidation. We want these tests to
 * be hermetic — no network calls — and the mock lets us control the return
 * value per test when needed.
 *
 * Why createTestingPinia({ stubActions: false })?
 * stubActions: false means the store's own action code runs without
 * replacement. This lets us verify that adjustBalance, normalizeBalance,
 * recomputeBalancesFromTransactions, etc. behave correctly. We still get the
 * Pinia testing harness for isolation (a fresh store per setActivePinia call).
 *
 * db mock shape:
 * Each Dexie Table method we rely on (toArray, update) is replaced with a
 * vi.fn() that returns a resolved Promise. Individual tests that exercise
 * recomputeBalancesFromTransactions override these mocks via mockResolvedValue
 * to inject test fixture data without touching real IndexedDB.
 *
 * adjustBalance does a fire-and-forget db.accounts.update() call (inside a
 * .catch()), so its mock only needs to return a resolved Promise to prevent
 * unhandled rejection noise. We use mockResolvedValue(undefined) for that.
 */

import { setActivePinia } from 'pinia'
import { createTestingPinia } from '@pinia/testing'
import { useAccountsStore } from './accounts'
import type { LocalAccount } from '@/offline'
import { AccountType } from '@/types/account'

// ---------------------------------------------------------------------------
// Module-level mocks — must be declared before any imports that trigger the
// mocked modules. Vitest hoists vi.mock() calls to the top of the file, so
// ordering relative to import statements is not critical, but declaring them
// near the top keeps the file easy to read.
// ---------------------------------------------------------------------------

/**
 * Mock the @/offline barrel.
 *
 * We need to mock:
 * - db.accounts.toArray   — used by refreshFromDB and implicitly by actions
 * - db.accounts.update    — used by adjustBalance (fire-and-forget) and
 *                           recomputeBalancesFromTransactions
 * - db.transactions.toArray — used by recomputeBalancesFromTransactions
 * - db.transfers.toArray  — used by recomputeBalancesFromTransactions
 * - fetchAllWithRevalidation — used by fetchAccounts
 * - fetchByIdWithRevalidation — used by fetchAccountById
 * - mutationQueue.enqueue / findPendingCreate — used by write actions
 * - generateTempId        — used by createAccount
 */
vi.mock('@/offline', () => {
  const dbAccountsUpdate = vi.fn().mockResolvedValue(undefined)
  const dbAccountsToArray = vi.fn().mockResolvedValue([])
  const dbAccountsAdd = vi.fn().mockResolvedValue(undefined)
  const dbAccountsDelete = vi.fn().mockResolvedValue(undefined)

  const dbTransactionsToArray = vi.fn().mockResolvedValue([])
  const dbTransfersToArray = vi.fn().mockResolvedValue([])

  return {
    db: {
      accounts: {
        toArray: dbAccountsToArray,
        update: dbAccountsUpdate,
        add: dbAccountsAdd,
        delete: dbAccountsDelete,
      },
      transactions: {
        toArray: dbTransactionsToArray,
      },
      transfers: {
        toArray: dbTransfersToArray,
      },
    },
    fetchAllWithRevalidation: vi.fn().mockResolvedValue([]),
    fetchByIdWithRevalidation: vi.fn().mockResolvedValue(undefined),
    generateTempId: vi.fn().mockReturnValue('temp-test-id'),
    isTempId: vi.fn((id: string) => id.startsWith('temp-')),
    mutationQueue: {
      enqueue: vi.fn().mockResolvedValue(1),
      findPendingCreate: vi.fn().mockResolvedValue(undefined),
      updatePayload: vi.fn().mockResolvedValue(undefined),
      remove: vi.fn().mockResolvedValue(undefined),
      count: vi.fn().mockResolvedValue(0),
    },
    // sync-manager singleton — not used by accounts store but exported by barrel
    syncManager: {},
    MutationQueue: vi.fn(),
    SyncManager: vi.fn(),
  }
})

vi.mock('@/api/accounts', () => ({
  accountsApi: {
    getAll: vi.fn().mockResolvedValue([]),
    getById: vi.fn().mockResolvedValue(null),
    create: vi.fn().mockResolvedValue(null),
    update: vi.fn().mockResolvedValue(null),
    delete: vi.fn().mockResolvedValue(undefined),
  },
}))

// ---------------------------------------------------------------------------
// Shared fixture factory
// ---------------------------------------------------------------------------
function makeAccount(overrides: Partial<LocalAccount> = {}): LocalAccount {
  return {
    id: 'acc-1',
    nombre: 'Cuenta Principal',
    tipo: AccountType.DEBITO,
    divisa: 'EUR',
    tags: [],
    activa: true,
    balance: 100,
    created_at: '2024-01-01T00:00:00.000Z',
    updated_at: '2024-01-01T00:00:00.000Z',
    _sync_status: 'synced',
    _local_updated_at: '2024-01-01T00:00:00.000Z',
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Setup helper
// ---------------------------------------------------------------------------
function setup() {
  setActivePinia(
    createTestingPinia({ stubActions: false })
  )
  return useAccountsStore()
}

// ---------------------------------------------------------------------------
// activeAccounts — computed
// ---------------------------------------------------------------------------
describe('useAccountsStore — activeAccounts', () => {
  it('returns only accounts where activa is true', () => {
    const store = setup()
    store.accounts = [
      makeAccount({ id: 'a1', activa: true }),
      makeAccount({ id: 'a2', activa: false }),
      makeAccount({ id: 'a3', activa: true }),
    ]
    expect(store.activeAccounts).toHaveLength(2)
    expect(store.activeAccounts.map(a => a.id)).toEqual(['a1', 'a3'])
  })

  it('returns an empty array when all accounts are inactive', () => {
    const store = setup()
    store.accounts = [makeAccount({ activa: false })]
    expect(store.activeAccounts).toHaveLength(0)
  })

  it('returns all accounts when all are active', () => {
    const store = setup()
    store.accounts = [makeAccount({ id: 'a1' }), makeAccount({ id: 'a2' })]
    expect(store.activeAccounts).toHaveLength(2)
  })
})

// ---------------------------------------------------------------------------
// accountsWithBalances — computed
// ---------------------------------------------------------------------------
describe('useAccountsStore — accountsWithBalances', () => {
  it('prefers balances.value over account.balance when available', () => {
    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', balance: 50 })]
    // Seed balances map with a different value — this should win
    store.balances.set('acc-1', { account_id: 'acc-1', balance: 200, currency: 'EUR' })

    const result = store.accountsWithBalances
    expect(result[0].balance).toBe(200)
  })

  it('falls back to account.balance when balances map has no entry', () => {
    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', balance: 75 })]
    // balances map is empty by default

    const result = store.accountsWithBalances
    expect(result[0].balance).toBe(75)
  })

  it('returns 0 when neither map nor account.balance is set', () => {
    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', balance: undefined })]

    const result = store.accountsWithBalances
    expect(result[0].balance).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// adjustBalance
// ---------------------------------------------------------------------------
describe('useAccountsStore — adjustBalance', () => {
  it('adds a positive delta to the existing balance', () => {
    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', balance: 100 })]
    store.adjustBalance('acc-1', 50)
    expect(store.accountsWithBalances[0].balance).toBe(150)
  })

  it('subtracts a negative delta from the existing balance', () => {
    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', balance: 100 })]
    store.adjustBalance('acc-1', -30)
    expect(store.accountsWithBalances[0].balance).toBe(70)
  })

  it('starts from the balances map value when available', () => {
    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', balance: 100 })]
    // The map has the authoritative balance of 200
    store.balances.set('acc-1', { account_id: 'acc-1', balance: 200, currency: 'EUR' })
    store.adjustBalance('acc-1', 10)
    expect(store.balances.get('acc-1')!.balance).toBe(210)
  })

  it('creates a balances map entry when none existed before', () => {
    const store = setup()
    // accounts has no matching id — balance unknown
    store.accounts = []
    store.adjustBalance('acc-new', 25)
    expect(store.balances.get('acc-new')!.balance).toBe(25)
  })

  it('updates accounts.value[idx].balance to the new balance', () => {
    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', balance: 0 })]
    store.adjustBalance('acc-1', 99)
    expect(store.accounts[0].balance).toBe(99)
  })
})

// ---------------------------------------------------------------------------
// normalizeBalance (called internally — tested via side-effects)
// ---------------------------------------------------------------------------
describe('useAccountsStore — normalizeBalance (via refreshFromDB)', () => {
  it('converts a string balance to a number', async () => {
    const { db } = await import('@/offline')
    // Simulate IndexedDB returning a balance stored as a string (API quirk)
    ;(db.accounts.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      makeAccount({ id: 'acc-1', balance: '42.5' as unknown as number }),
    ])
    const store = setup()
    await store.refreshFromDB()
    expect(store.accounts[0].balance).toBe(42.5)
    expect(typeof store.accounts[0].balance).toBe('number')
  })

  it('defaults a missing balance field to 0', async () => {
    const { db } = await import('@/offline')
    ;(db.accounts.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      makeAccount({ id: 'acc-1', balance: undefined }),
    ])
    const store = setup()
    await store.refreshFromDB()
    expect(store.accounts[0].balance).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// recomputeBalancesFromTransactions
// ---------------------------------------------------------------------------
describe('useAccountsStore — recomputeBalancesFromTransactions', () => {
  it('adds ingreso transactions to the account balance', async () => {
    const { db } = await import('@/offline')
    ;(db.transactions.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      { cuenta_id: 'acc-1', tipo: 'ingreso', monto: '100' },
      { cuenta_id: 'acc-1', tipo: 'ingreso', monto: '50' },
    ])
    ;(db.transfers.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([])

    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', divisa: 'EUR', balance: 0 })]
    await store.recomputeBalancesFromTransactions()

    expect(store.balances.get('acc-1')!.balance).toBe(150)
  })

  it('subtracts gasto transactions from the account balance', async () => {
    const { db } = await import('@/offline')
    ;(db.transactions.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      { cuenta_id: 'acc-1', tipo: 'gasto', monto: '40' },
    ])
    ;(db.transfers.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([])

    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', divisa: 'EUR', balance: 0 })]
    await store.recomputeBalancesFromTransactions()

    expect(store.balances.get('acc-1')!.balance).toBe(-40)
  })

  it('applies transfer debits and credits to origin and destination accounts', async () => {
    const { db } = await import('@/offline')
    ;(db.transactions.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([])
    ;(db.transfers.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      { cuenta_origen_id: 'acc-origin', cuenta_destino_id: 'acc-dest', monto: '75' },
    ])

    const store = setup()
    store.accounts = [
      makeAccount({ id: 'acc-origin', divisa: 'EUR', balance: 0 }),
      makeAccount({ id: 'acc-dest', divisa: 'EUR', balance: 0 }),
    ]
    await store.recomputeBalancesFromTransactions()

    expect(store.balances.get('acc-origin')!.balance).toBe(-75)
    expect(store.balances.get('acc-dest')!.balance).toBe(75)
  })

  it('updates accounts.value[idx].balance with the recomputed value', async () => {
    const { db } = await import('@/offline')
    ;(db.transactions.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      { cuenta_id: 'acc-1', tipo: 'ingreso', monto: '200' },
    ])
    ;(db.transfers.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([])

    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', divisa: 'EUR', balance: 0 })]
    await store.recomputeBalancesFromTransactions()

    expect(store.accounts[0].balance).toBe(200)
  })

  it('assigns the account divisa as the currency in the balances map', async () => {
    const { db } = await import('@/offline')
    ;(db.transactions.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      { cuenta_id: 'acc-1', tipo: 'ingreso', monto: '10' },
    ])
    ;(db.transfers.toArray as ReturnType<typeof vi.fn>).mockResolvedValueOnce([])

    const store = setup()
    store.accounts = [makeAccount({ id: 'acc-1', divisa: 'GBP', balance: 0 })]
    await store.recomputeBalancesFromTransactions()

    expect(store.balances.get('acc-1')!.currency).toBe('GBP')
  })
})
