# Design Spec: Net Worth Loading Refactor

**Date:** 2026-03-16
**Ticket:** https://www.notion.so/32579901d1b881d485f1c909da9aaacc
**Status:** Design approved — pending implementation

---

## Overview

`NetWorthCard` and `NetWorthChart` on the home screen have visible loading problems on first app open and new user login. Six root causes were identified through full data-flow analysis. This spec defines the fixes.

---

## Scope

**In scope:**
- Simplifying `fetchAccounts()` to read from Dexie only (balance bug fix)
- Removing the `balance` field from backend account endpoints
- Seeding exchange rates into Dexie on first launch
- Fixing Guard 2 in `useNetWorthHistory` for new users with no transactions
- Debouncing the `watchEffect` in `useNetWorthHistory` during sync
- Disabling the "Todo" preset button until `resolveOldestDate()` resolves

**Out of scope:**
- Removing `fetchAllWithRevalidation` from all stores (tracked separately: https://www.notion.so/32579901d1b881538397d2c7436c630e)
- Any changes to the SyncManager
- Any changes to `useWidgetData` or analytics widgets

---

## Root Causes & Changes

### Change 1 — Simplify `fetchAccounts()` to read Dexie only

**Problem:** `fetchAccounts()` in `accounts.ts` calls the backend via `fetchAllWithRevalidation`. The backend response includes a `balance` field that momentarily overwrites the correct local balance in Dexie. The `onFreshData` callback immediately repairs it, but the race condition is a recurring source of bugs.

The SyncManager already keeps Dexie up to date via `fullReadSync` + `incrementalSync` with cursors. The backend call is redundant.

**Fix:** Replace the body of `fetchAccounts()` with a direct Dexie read, delegating to `refreshFromDB()`. The `activeOnly` parameter is dropped — it was only used to filter the backend call. Views already filter via the `activeAccounts` computed.

```typescript
async function fetchAccounts() {
  loading.value = true
  try {
    await refreshFromDB()
  } catch (err: any) {
    error.value = err.message || 'Error al cargar cuentas'
    throw err
  } finally {
    loading.value = false
  }
}
```

**Callers affected:** `App.vue`, `DashboardView`, `AccountsListView` — all pass `activeOnly=true` which was a no-op on the Dexie side anyway.

---

### Change 2 — Remove `balance` field from backend account endpoints

**Problem:** The backend computes and returns `balance` in `GET /accounts` and `GET /accounts/{id}`. The frontend never uses it — balance is always computed locally from transactions. The field is technical debt and the source of the bug described in Change 1.

**Backend fix:**
- Remove `balance` from `AccountWithBalanceResponse` schema in `app/schemas/account.py`
- Remove balance computation from `AccountService` list/detail methods in `app/services/account.py`
- Remove the dedicated `GET /accounts/{account_id}/balance` endpoint — confirmed present at `app/api/accounts.py:339`
- Update backend tests that assert the `balance` field

**Frontend fix:**
- Remove dead code: `api/accounts.ts:getBalance()`, `api/dashboard.ts:getAccountBalances()`, `api/dashboard.ts:getSummary()`, `types/api.ts:DashboardData`
- `types/account.ts:Account.balance?: number` — keep as optional. `undefined` is handled by `?? 0` in the store
- No changes needed in stores or SyncManager — `account.balance` arriving as `undefined` from Dexie is already covered by `balances.value.get(id)?.balance ?? account.balance ?? 0`

---

### Change 3 — Seed exchange rates into Dexie on first launch

**Problem:** On cold start with no cached rates, `rates.value = []`. This triggers Guard 1 in `useNetWorthHistory` (`ratesCount === 0 → early return → loading = true forever`) and causes `NetWorthCard` to show "Total sin convertir" briefly before rates arrive from the backend.

**Fix:** Add `BASE_RATES` constant in `src/stores/exchangeRates.ts` with the 9 supported currencies. In `fetchRates()`, if `db.exchangeRates.toArray()` returns an empty array, seed the table with `BASE_RATES` via `bulkPut` before assigning `rates.value`.

```typescript
const BASE_RATES: LocalExchangeRate[] = [
  { currency_code: 'USD', rate_to_usd: 1,              fetched_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'COP', rate_to_usd: 3691.6733650,   fetched_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'EUR', rate_to_usd: 0.8746440,      fetched_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'BRL', rate_to_usd: 5.2654710,      fetched_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'JPY', rate_to_usd: 159.5572970,    fetched_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'ARS', rate_to_usd: 1452.2500000,   fetched_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'GBP', rate_to_usd: 0.7553490,      fetched_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'BTC', rate_to_usd: 0.0000135619,   fetched_at: '2026-03-16T00:00:00Z' },
  { currency_code: 'ETH', rate_to_usd: 0.0004412634,   fetched_at: '2026-03-16T00:00:00Z' },
]
```

```typescript
async function fetchRates(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    let localData = await db.exchangeRates.toArray()
    if (localData.length === 0) {
      await db.exchangeRates.bulkPut(BASE_RATES)
      localData = BASE_RATES
    }
    rates.value = localData
  } catch (err: any) {
    console.warn('[exchangeRates] IndexedDB read failed:', err)
    rates.value = BASE_RATES  // in-memory fallback if Dexie fails entirely
  } finally {
    loading.value = false
  }
  // background revalidation continues unchanged...
}
```

**Note on error escalation:** The background revalidation checks `if (rates.value.length === 0)` to decide whether to set `error.value`. After this change, `rates.value` is never empty (always has BASE_RATES at minimum), so background revalidation failures will always be swallowed silently. This is the desired behavior — stale base rates are better than an error state.

```typescript
```

**Consequences:**
- Guard 1 in `useNetWorthHistory` (`if (isRatesLoading || ratesCount === 0)`) can be removed — `rates.value` is never empty after this change
- `NetWorthCard` never shows "Total sin convertir" on cold start
- Rates persist in Dexie across reloads even without network

**Maintenance note:** `BASE_RATES` must be updated on every minor version release. See `CLAUDE.md` for the reminder protocol.

---

### Change 4 — Fix Guard 2 for new user with no transactions

**Problem:** Guard 2 in `useNetWorthHistory`:

```typescript
if (!initialSyncComplete && isSyncing && txCount === 0 && tfCount === 0) {
  loading.value = true
  return
}
```

If the initial sync fails silently or takes a very long time, `isSyncing` stays `true` indefinitely, keeping the chart in skeleton state forever with no way out.

**Important:** `!initialSyncComplete` must be kept. Without it, any subsequent incremental background sync would re-trigger the skeleton for a user who legitimately has no transactions. The flag ensures this guard only fires during the very first sync.

**Fix:** Add a reactive ref `syncTimedOut` that a `setTimeout` flips to `true` after 15 seconds. Because `syncTimedOut` is a `ref`, flipping it re-triggers the `watchEffect` automatically even if no other dependency changed.

```typescript
const SYNC_SKELETON_TIMEOUT_MS = 15_000
const syncTimedOut = ref(false)

// Set the timeout once on composable creation (outside watchEffect)
setTimeout(() => { syncTimedOut.value = true }, SYNC_SKELETON_TIMEOUT_MS)

// Inside watchEffect — read syncTimedOut so Vue tracks it:
const timedOut = syncTimedOut.value

if (!initialSyncComplete && isSyncing && txCount === 0 && tfCount === 0 && !timedOut) {
  loading.value = true
  return
}
```

When `isSyncing` transitions to `false` (sync complete) OR when `syncTimedOut` flips after 15 seconds, the `watchEffect` re-runs, the guard stops firing, and the computation proceeds to show either the chart or the empty state.

---

### Change 5 — Debounce `watchEffect` in `useNetWorthHistory`

**Problem:** During sync, `transactionsStore.transactions.length` changes with every batch the SyncManager writes to Dexie. Each change re-triggers the `watchEffect`, which does three full IndexedDB reads plus the full walking-pass computation. With a large transaction history this is expensive and produces unnecessary intermediate renders.

**Fix:** Wrap the computation body in `useDebounceFn` from `@vueuse/core` (already in the project) with a 300ms delay. Vue still tracks all reactive dependencies normally; only the actual computation is debounced.

The `watchEffect` wrapper must explicitly read **every** reactive dependency so Vue tracks them. The guards also live in the wrapper (not in `runComputation`) since they depend on tracked values. `loading.value = true` is set unconditionally in the wrapper after the guards pass, before handing off to `runComputation`. `runComputation` sets `loading.value = false` in its `finally` block.

```typescript
import { useDebounceFn } from '@vueuse/core'

const runComputation = useDebounceFn(async (
  rangeDays: number,
  gran: Granularity,
  primaryCurrency: string
) => {
  // DB reads + walking pass + assign _dataPoints
  // finally: loading.value = false
}, 300)

watchEffect(() => {
  // Read ALL reactive deps so Vue tracks them:
  const rangeDays = _rangeDays.value
  const gran = granularity.value
  const primaryCurrency = settingsStore.primaryCurrency
  const isRatesLoading = exchangeRatesStore.loading     // tracked for reactivity only — Guard 1 is REMOVED per Change 3
  const ratesCount = exchangeRatesStore.rates.length    // tracked for reactivity only — Guard 1 is REMOVED per Change 3
  // NOTE: Guard 1 (if isRatesLoading || ratesCount === 0) is intentionally absent.
  // BASE_RATES seeding (Change 3) guarantees rates.value is never empty.
  const isSyncing = syncStore.isSyncing
  const initialSyncComplete = syncStore.initialSyncComplete
  const txCount = transactionsStore.transactions.length
  const tfCount = transfersStore.transfers.length
  const timedOut = syncTimedOut.value

  // Guard 2: skeleton during initial sync with no local data
  if (!initialSyncComplete && isSyncing && txCount === 0 && tfCount === 0 && !timedOut) {
    loading.value = true
    return
  }

  // Signal loading before handing off to debounced computation
  loading.value = true
  void runComputation(rangeDays, gran, primaryCurrency)
})
```

**Trade-off:** If batches arrive more than 300ms apart, the chart updates once per batch instead of once at the end. This is acceptable — progressive updates are not worse UX than a single jump.

---

### Change 6 — Disable "Todo" preset until `resolveOldestDate()` resolves

**Problem:** `todoDays` initializes to `1825` (5-year fallback). If the user taps "Todo" before `resolveOldestDate()` completes, the composable computes ~1700 empty boundary points for a user who only has 3 months of history.

**Fix:** Initialize `todoDays` as `ref<number | null>(null)`. Disable the "Todo" button with a micro-spinner while `todoDays.value === null`. Once `resolveOldestDate()` resolves, the button enables with the correct value.

```typescript
const todoDays = ref<number | null>(null)
```

```html
<button
  v-for="preset in PRESETS"
  :disabled="preset.label === 'Todo' && todoDays === null"
  @click="selectPreset(preset)"
>
  <span v-if="preset.label === 'Todo' && todoDays === null" class="animate-spin">⟳</span>
  <span v-else>{{ preset.label }}</span>
</button>
```

`resolveOldestDate()` must be updated to set a fallback when there are no records (new user), instead of returning without assigning:

```typescript
async function resolveOldestDate(): Promise<void> {
  const [oldestTx, oldestTr] = await Promise.all([...])
  const dates: string[] = []
  if (oldestTx?.date) dates.push(oldestTx.date)
  if (oldestTr?.date) dates.push(oldestTr.date)

  if (dates.length === 0) {
    todoDays.value = 30  // new user: default to 30 days, enables the button
    return
  }
  // ...existing logic
}
```

`rangeDays` computed must handle `null` safely:

```typescript
const rangeDays = computed<number>(() => {
  const preset = PRESETS.find(p => p.label === selectedLabel.value)
  if (!preset) return 30
  if (preset.staticDays !== null) return preset.staticDays
  if (preset.label === 'YTD') return ytdDays.value
  if (preset.label === 'Todo') return todoDays.value ?? 30  // null = button disabled, this value won't be used
  return 30
})
```

---

## Affected Files

**Frontend:**
- `src/stores/accounts.ts` — Change 1
- `src/stores/exchangeRates.ts` — Change 3
- `src/composables/useNetWorthHistory.ts` — Changes 4, 5
- `src/components/dashboard/NetWorthChart.vue` — Change 6
- `src/api/accounts.ts` — Change 2 (remove dead code)
- `src/api/dashboard.ts` — Change 2 (remove dead code)
- `src/types/api.ts` — Change 2 (remove dead code)

**Backend:**
- `app/schemas/account.py` — Change 2
- `app/services/account.py` — Change 2
- `app/routes/accounts.py` — Change 2 (remove balance endpoint if exists)
- Backend tests — Change 2

---

## Acceptance Criteria

- [ ] Cold start sin caché de tasas: `NetWorthCard` muestra el patrimonio correctamente, sin flash de "Total sin convertir"
- [ ] Cold start sin caché de tasas: `NetWorthChart` no muestra skeleton esperando tasas
- [ ] Usuario nuevo sin transacciones: el chart muestra empty state tras el sync, no skeleton indefinido
- [ ] Durante sync activo con historial largo: el chart no recomputa más de una vez cada 300ms
- [ ] Preset "Todo" está deshabilitado al montar hasta que `resolveOldestDate()` resuelve
- [ ] `GET /accounts` no retorna el campo `balance`
- [ ] `fetchAccounts()` no hace llamadas al backend
- [ ] `docker compose exec backend pytest` — 305/305 passing (removing balance endpoint will reduce or adjust this count if tests for that endpoint are deleted)
- [ ] `cd frontend && npx vitest run` — 267/267 passing (baseline as of 2026-03-16 after previous fix; 261 pre-existing + 6 fixed in prior session)
