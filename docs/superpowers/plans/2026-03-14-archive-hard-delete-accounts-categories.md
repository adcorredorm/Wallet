# Archive and Hard Delete — Accounts & Categories Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate the existing single "delete" action into Archive (soft delete, always available, keeps history) and Hard Delete (permanent, blocked when movements exist) for both accounts and categories, following the app's offline-first IndexedDB pattern.

**Architecture:** Every write goes to IndexedDB first, updates reactive Pinia state optimistically, then enqueues a `PendingMutation`. A new `delete_permanent` operation is added to the mutation union and handled in the SyncManager alongside the existing `delete` (now meaning archive). The Dexie schema is bumped to version 6 to index `categories.active`. All UI changes are additive — existing components are extended, not rewritten.

**Tech Stack:** Vue 3 `<script setup>`, Pinia, Dexie 3 (IndexedDB), TypeScript strict mode, Tailwind CSS, Vue Router 4.

---

## Chunk 1: Type System and Schema Foundation

### Task 1: Extend `PendingMutation.operation` union

**Files:**
- Modify: `frontend/src/offline/types.ts`

This is the blocking first step. Every switch on `mutation.operation` in the codebase is exhaustive via TypeScript — adding the new literal will immediately surface all unhandled locations as compile errors, giving a complete checklist for the rest of the work.

- [ ] **Step 1.1: Add `'delete_permanent'` to the operation union**

In `frontend/src/offline/types.ts`, change line 82:

```typescript
// Before
operation: 'create' | 'update' | 'delete'

// After
operation: 'create' | 'update' | 'delete' | 'delete_permanent'
```

- [ ] **Step 1.2: Run type-check to get the full error list**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS"
```

Expected: Several errors in `sync-manager.ts` (each switch on `mutation.operation` is now non-exhaustive). Record every file and line flagged — those are exactly the locations that must be updated in Task 3. No other files should be flagged at this point; if they are, note them.

- [ ] **Step 1.3: Commit the type extension only**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend
git add src/offline/types.ts
git commit -m "feat(types): add delete_permanent to PendingMutation.operation union"
```

---

### Task 2: Add `active` field to `Category` type and `UpdateCategoryDto`

**Files:**
- Modify: `frontend/src/types/category.ts`

The `Category` interface currently has no `active` field. The `Account` interface already has `active: boolean`. Adding it to `Category` aligns the two domain types and lets the store, API layer, and components all work with a typed `active` flag instead of casting.

- [ ] **Step 2.1: Add `active` to the `Category` interface**

In `frontend/src/types/category.ts`, update the `Category` interface:

```typescript
export interface Category {
  id: string
  name: string
  type: CategoryType
  icon?: string
  color?: string
  parent_category_id?: string
  active: boolean          // NEW — false means archived
  created_at: string
  updated_at: string
}
```

- [ ] **Step 2.2: Add `active` to `UpdateCategoryDto`**

```typescript
export interface UpdateCategoryDto {
  name?: string
  type?: CategoryType
  icon?: string
  color?: string
  parent_category_id?: string
  active?: boolean         // NEW — used for archive/restore
}
```

- [ ] **Step 2.3: Run type-check**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS"
```

Expected: New errors anywhere `Category` is constructed without `active` (e.g., in `categoriesStore.createCategory`). Make note of each location. We will fix them in subsequent tasks. Do not fix them yet — just confirm the expected errors appear.

- [ ] **Step 2.4: Commit**

```bash
git add src/types/category.ts
git commit -m "feat(types): add active field to Category interface and UpdateCategoryDto"
```

---

### Task 3: Bump Dexie schema to version 6

**Files:**
- Modify: `frontend/src/offline/db.ts`

The `categories` table has never been indexed on `active`. Version 6 adds that index and runs an upgrade migration to backfill `active = true` on every existing category row (since all existing categories are active — there have been no archived ones before this feature).

The accounts table already has `active` indexed since version 2; no change needed there.

- [ ] **Step 3.1: Add version 6 schema with categories `active` index**

Append after the `this.version(5).stores(...)` block in `frontend/src/offline/db.ts`:

```typescript
this.version(6)
  .stores({
    // All existing tables carried forward — schema strings must be repeated
    // even when unchanged, otherwise Dexie drops the table.
    accounts: 'id, server_id, type, active, _sync_status',
    transactions: 'id, server_id, account_id, category_id, type, date, _sync_status',
    transfers: 'id, server_id, source_account_id, destination_account_id, date, _sync_status',
    // categories: add active to the index so archivedCategories computed
    // can query db.categories.where('active').equals(0) efficiently.
    categories: 'id, server_id, type, active, parent_category_id, _sync_status',
    pendingMutations: '++id, entity_type, entity_id, operation, queued_at',
    exchangeRates: 'currency_code',
    settings: 'key, _sync_status',
    dashboards: 'id, server_id, is_default, sort_order, _sync_status',
    dashboardWidgets: 'id, server_id, dashboard_id, _sync_status'
  })
  .upgrade(tx => {
    // Backfill active = true on all existing categories.
    // Why true? All categories created before this feature were active —
    // the concept of "archived" did not exist until now. Setting active to
    // true means no existing user data is hidden after the migration.
    return tx.table('categories').toCollection().modify((cat: Record<string, unknown>) => {
      if (cat['active'] === undefined) {
        cat['active'] = true
      }
    })
  })
```

- [ ] **Step 3.2: Run type-check**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS"
```

Expected: No new errors introduced by this change. If the `.modify()` callback shows a type error, cast explicitly: `(cat: Record<string, unknown>)`.

- [ ] **Step 3.3: Commit**

```bash
git add src/offline/db.ts
git commit -m "feat(db): bump schema to v6 — index categories.active, backfill active=true"
```

---

## Chunk 2: API Layer

### Task 4: Add `hardDelete` to `accounts` API client

**Files:**
- Modify: `frontend/src/api/accounts.ts`

The existing `delete(id)` maps to `DELETE /accounts/:id` which the backend treats as a soft-delete (sets `active = false`). The new `hardDelete(id)` maps to `DELETE /accounts/:id/permanent` which is a permanent removal on the backend. The SyncManager will call this endpoint when it processes a `delete_permanent` mutation.

- [ ] **Step 4.1: Add `hardDelete` method**

In `frontend/src/api/accounts.ts`, add after the existing `delete` method:

```typescript
/**
 * Permanently delete an account (hard delete — irreversible).
 * Only valid when the account has zero transactions and transfers.
 * @param id - Account UUID
 */
hardDelete(id: string): Promise<void> {
  return apiClient.delete(`/accounts/${id}/permanent`)
},
```

- [ ] **Step 4.2: Run type-check**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS"
```

Expected: No errors.

- [ ] **Step 4.3: Commit**

```bash
git add src/api/accounts.ts
git commit -m "feat(api): add hardDelete to accountsApi — DELETE /accounts/:id/permanent"
```

---

### Task 5: Update `categories` API client

**Files:**
- Modify: `frontend/src/api/categories.ts`

Three changes are needed:
1. Rename the implicit contract: the existing `delete(id)` now explicitly represents archive (the backend `DELETE /categories/:id` is a soft-delete — it sets `active = false`). Add a JSDoc clarification.
2. Add `hardDelete(id)` → `DELETE /categories/:id/permanent`.
3. The `update()` method already accepts `UpdateCategoryDto` which now includes `active?: boolean` (Task 2) — no signature change required.

- [ ] **Step 5.1: Update JSDoc on `delete` and add `hardDelete`**

Replace the `delete` method and add `hardDelete` in `frontend/src/api/categories.ts`:

```typescript
/**
 * Archive a category (soft delete — sets active to false on the server).
 * All existing transactions linked to this category are preserved.
 * @param id - Category UUID
 */
delete(id: string): Promise<void> {
  return apiClient.delete(`/categories/${id}`)
},

/**
 * Permanently delete a category (hard delete — irreversible).
 * Only valid when the category has zero transactions and no active subcategories.
 * @param id - Category UUID
 */
hardDelete(id: string): Promise<void> {
  return apiClient.delete(`/categories/${id}/permanent`)
},
```

- [ ] **Step 5.2: Run type-check**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS"
```

Expected: No errors.

- [ ] **Step 5.3: Commit**

```bash
git add src/api/categories.ts
git commit -m "feat(api): add hardDelete to categoriesApi — DELETE /categories/:id/permanent"
```

---

## Chunk 3: SyncManager — handle `delete_permanent`

### Task 6: Fix all exhaustive-switch gaps in `sync-manager.ts`

**Files:**
- Modify: `frontend/src/offline/sync-manager.ts`

After Task 1 extended the union, TypeScript flagged every `switch (mutation.operation)` that lacks a `delete_permanent` case. There are distinct locations:

1. `sendAccount()` — switch on operation
2. `sendCategory()` — switch on operation
3. `sendTransaction()`, `sendTransfer()`, `sendDashboard()`, `sendDashboardWidget()` — each needs a `delete_permanent` case that throws (these entity types should never receive a hard-delete mutation; throwing surfaces accidental misuse)
4. `processQueue()` — the guard `mutation.operation !== 'delete'` before `markSynced` must also exclude `delete_permanent`

- [ ] **Step 6.1: Update `sendAccount` to handle `delete_permanent`**

In `sendAccount`, after the `case 'delete':` block, add:

```typescript
case 'delete_permanent':
  await accountsApi.hardDelete(mutation.entity_id)
  // Hard delete: the entity was already removed from IndexedDB and the
  // reactive store by hardDeleteAccount() before this mutation was enqueued.
  // Return a minimal object so processQueue's type system is satisfied.
  return { id: mutation.entity_id } as Account
```

- [ ] **Step 6.2: Update `sendCategory` to handle `delete_permanent`**

In `sendCategory`, after the `case 'delete':` block, add:

```typescript
case 'delete_permanent':
  await categoriesApi.hardDelete(mutation.entity_id)
  return { id: mutation.entity_id } as Category
```

- [ ] **Step 6.3: Add `delete_permanent` throw case to `sendTransaction`, `sendTransfer`, `sendDashboard`, `sendDashboardWidget`**

For each of these four helpers, add after the existing `case 'delete':` block:

```typescript
case 'delete_permanent':
  throw new Error(
    `[SyncManager] delete_permanent is not valid for ${mutation.entity_type}`
  )
```

- [ ] **Step 6.4: Update the `markSynced` guard in `processQueue`**

Find this line (approximately line 317 in the original file):

```typescript
if (mutation.operation !== 'delete') {
```

Change it to:

```typescript
if (mutation.operation !== 'delete' && mutation.operation !== 'delete_permanent') {
```

Reason: for both soft and hard deletes, the entity has already been removed from IndexedDB before the mutation was enqueued. There is nothing to mark as synced.

- [ ] **Step 6.5: Run type-check — all errors from Task 1 must be resolved**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS"
```

Expected: Zero TypeScript errors. If any remain, address them before continuing.

- [ ] **Step 6.6: Run lint**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run lint 2>&1 | grep -v "^$"
```

Expected: No lint errors.

- [ ] **Step 6.7: Commit**

```bash
git add src/offline/sync-manager.ts
git commit -m "feat(sync): handle delete_permanent in sendAccount and sendCategory"
```

---

## Chunk 4: Accounts Store

### Task 7: Refactor `accountsStore` — archive, hard delete, restore

**Files:**
- Modify: `frontend/src/stores/accounts.ts`

The existing `deleteAccount(id)` is repurposed into three distinct operations:

- `archiveAccount(id)`: sets `active = false` in IndexedDB, keeps the record, enqueues `delete` mutation (the backend `DELETE /accounts/:id` is a soft-delete).
- `hardDeleteAccount(id)`: verifies zero movements in Dexie (transactions + transfers), removes the record from IndexedDB, enqueues `delete_permanent`.
- `restoreAccount(id)`: sets `active = true`, enqueues `update` with `{ active: true }`.
- `archivedAccounts` computed: filters `active === false`.

The original `deleteAccount` is kept as an alias pointing to `archiveAccount` to avoid breaking any callers outside this task.

- [ ] **Step 7.1: Add `archivedAccounts` computed**

After the existing `activeAccounts` computed in `accounts.ts`:

```typescript
const archivedAccounts = computed(() =>
  accounts.value.filter(account => account.active === false)
)
```

- [ ] **Step 7.2: Add `archiveAccount` action**

Add after `updateAccount` in `accounts.ts`:

```typescript
/**
 * Archive an account (soft delete).
 *
 * Sets active = false in IndexedDB — the record is preserved so all
 * historical transactions and transfers remain intact. Enqueues a `delete`
 * mutation which the SyncManager sends to DELETE /accounts/:id on the server
 * (the backend's soft-delete endpoint).
 *
 * If the account was created offline (pending CREATE), cancel the CREATE
 * and remove everything locally — the server never saw this account.
 */
async function archiveAccount(id: string) {
  loading.value = true
  error.value = null
  try {
    const pendingCreate = await mutationQueue.findPendingCreate('account', id)
    if (pendingCreate && pendingCreate.id != null) {
      // Account never reached the server — clean up everything locally.
      await mutationQueue.remove(pendingCreate.id)
      await db.accounts.delete(id)
      accounts.value = accounts.value.filter(a => a.id !== id)
      balances.value.delete(id)
      if (selectedAccountId.value === id) selectedAccountId.value = null
      return
    }

    const now = new Date().toISOString()
    // Step 1 — Mark inactive in IndexedDB (keep the record).
    await db.accounts.update(id, {
      active: false,
      _sync_status: 'pending',
      _local_updated_at: now
    })

    // Step 2 — Update reactive state.
    const idx = accounts.value.findIndex(a => a.id === id)
    if (idx !== -1) {
      accounts.value[idx] = {
        ...accounts.value[idx],
        active: false,
        _sync_status: 'pending',
        _local_updated_at: now
      }
    }

    // Step 3 — Enqueue the soft-delete mutation.
    await mutationQueue.enqueue({
      entity_type: 'account',
      entity_id: id,
      operation: 'delete',
      payload: { id }
    })
  } catch (err: any) {
    error.value = err.message || 'Error al archivar cuenta'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 7.3: Add `hardDeleteAccount` action**

```typescript
/**
 * Permanently delete an account.
 *
 * Precondition: the account must have zero transactions and zero transfers
 * referencing it in IndexedDB. If movements exist, throws an error (the UI
 * should have disabled the button via hasMovements before calling this).
 *
 * Removes the record from IndexedDB immediately, then enqueues a
 * `delete_permanent` mutation for the SyncManager to call
 * DELETE /accounts/:id/permanent on the server.
 */
async function hardDeleteAccount(id: string) {
  loading.value = true
  error.value = null
  try {
    // Verify no movements exist locally before proceeding.
    const txCount = await db.transactions.where('account_id').equals(id).count()
    const transfersAsSource = await db.transfers.where('source_account_id').equals(id).count()
    const transfersAsDest = await db.transfers.where('destination_account_id').equals(id).count()
    if (txCount + transfersAsSource + transfersAsDest > 0) {
      throw new Error('No se puede borrar una cuenta con movimientos. Usa Archivar.')
    }

    // If a pending CREATE exists, cancel it — the server never saw this account.
    const pendingCreate = await mutationQueue.findPendingCreate('account', id)
    if (pendingCreate && pendingCreate.id != null) {
      await mutationQueue.remove(pendingCreate.id)
      await db.accounts.delete(id)
      accounts.value = accounts.value.filter(a => a.id !== id)
      balances.value.delete(id)
      if (selectedAccountId.value === id) selectedAccountId.value = null
      return
    }

    // Step 1 — Remove from IndexedDB.
    await db.accounts.delete(id)

    // Step 2 — Update reactive state.
    accounts.value = accounts.value.filter(a => a.id !== id)
    balances.value.delete(id)
    if (selectedAccountId.value === id) selectedAccountId.value = null

    // Step 3 — Enqueue permanent delete mutation.
    await mutationQueue.enqueue({
      entity_type: 'account',
      entity_id: id,
      operation: 'delete_permanent',
      payload: { id }
    })
  } catch (err: any) {
    error.value = err.message || 'Error al borrar cuenta permanentemente'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 7.4: Add `restoreAccount` action**

```typescript
/**
 * Restore an archived account (set active = true).
 *
 * Enqueues an `update` mutation with { active: true } so the SyncManager
 * sends PUT /accounts/:id to the server.
 */
async function restoreAccount(id: string) {
  loading.value = true
  error.value = null
  try {
    const now = new Date().toISOString()

    // Step 1 — Mark active in IndexedDB.
    await db.accounts.update(id, {
      active: true,
      _sync_status: 'pending',
      _local_updated_at: now
    })

    // Step 2 — Update reactive state.
    const idx = accounts.value.findIndex(a => a.id === id)
    if (idx !== -1) {
      accounts.value[idx] = {
        ...accounts.value[idx],
        active: true,
        _sync_status: 'pending',
        _local_updated_at: now
      }
    }

    // Step 3 — Enqueue update mutation.
    // Merge optimisation: collapse into pending CREATE if one exists.
    const pendingCreate = await mutationQueue.findPendingCreate('account', id)
    if (pendingCreate && pendingCreate.id != null) {
      await mutationQueue.updatePayload(pendingCreate.id, {
        ...pendingCreate.payload,
        active: true
      })
    } else {
      await mutationQueue.enqueue({
        entity_type: 'account',
        entity_id: id,
        operation: 'update',
        payload: { active: true }
      })
    }
  } catch (err: any) {
    error.value = err.message || 'Error al restaurar cuenta'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 7.5: Keep `deleteAccount` as an alias for backward compatibility**

Replace the existing `deleteAccount` function body so it delegates to `archiveAccount`:

```typescript
// Backward-compatibility alias — once all callers are migrated this alias
// can be removed. For now it prevents breaking callers outside this task.
async function deleteAccount(id: string) {
  return archiveAccount(id)
}
```

- [ ] **Step 7.6: Export the new computed and actions from the store's return object**

Add to the `return` statement:

```typescript
// Computed
archivedAccounts,
// Actions
archiveAccount,
hardDeleteAccount,
restoreAccount,
```

- [ ] **Step 7.7: Verify `createAccount` already sets `active: true`**

```bash
grep -n "active:" /Users/angelcorredor/Code/Wallet/frontend/src/stores/accounts.ts
```

Expected: A line with `active: true` inside the `localAccount` object literal in `createAccount`. No change needed.

- [ ] **Step 7.8: Run type-check**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS"
```

Expected: Zero errors.

- [ ] **Step 7.9: Commit**

```bash
git add src/stores/accounts.ts
git commit -m "feat(store): archive, hardDelete, and restore actions for accounts"
```

---

## Chunk 5: Categories Store

### Task 8: Refactor `categoriesStore` — archive, hard delete, restore, fix `createCategory`

**Files:**
- Modify: `frontend/src/stores/categories.ts`

Changes:
- Fix `createCategory` to include `active: true` (now required by the `Category` interface).
- Add `archiveCategory(id)` with cascade: archives active children first (one mutation per child), then the parent.
- Add `hardDeleteCategory(id)`: verifies zero transactions and zero active subcategories.
- Add `restoreCategory(id)`.
- Add `archivedCategories` computed.
- Add `activeCategories` computed for dropdowns and list views.
- Update `categoryTree` to iterate over `activeCategories` instead of `categories`.
- Update `compatibleParentCategories` to exclude archived categories.
- Keep `deleteCategory` as alias for `archiveCategory`.

- [ ] **Step 8.1: Fix `createCategory` to include `active: true`**

In the `localCategory` literal inside `createCategory`, add:

```typescript
const localCategory: LocalCategory = {
  id: tempId,
  name: data.name,
  type: data.type,
  icon: data.icon,
  color: data.color,
  parent_category_id: data.parent_category_id,
  active: true,              // NEW — all new categories start active
  created_at: now,
  updated_at: now,
  _sync_status: 'pending',
  _local_updated_at: now
}
```

- [ ] **Step 8.2: Add `archivedCategories` and `activeCategories` computed**

After the existing `parentCategories` computed:

```typescript
// activeCategories: treat missing active field as true (backward compat with
// records fetched from server before this feature was deployed).
const activeCategories = computed(() =>
  categories.value.filter(cat => cat.active !== false)
)

const archivedCategories = computed(() =>
  categories.value.filter(cat => cat.active === false)
)
```

- [ ] **Step 8.3: Update `categoryTree` to iterate over `activeCategories`**

In the `categoryTree` computed, change the two `for (const cat of categories.value)` loops to:

```typescript
for (const cat of activeCategories.value) {
```

Both occurrences must be updated. This ensures archived categories are excluded from the tree used by `CategorySelect` and the list view's collapsible sections.

- [ ] **Step 8.4: Update `compatibleParentCategories` to exclude archived categories**

Add an early return at the top of the filter callback:

```typescript
function compatibleParentCategories(type: CategoryType, excludeId?: string): LocalCategory[] {
  return categories.value.filter(cat => {
    // Exclude archived categories — they cannot be selected as parents
    if (cat.active === false) return false

    if (cat.parent_category_id) return false
    if (excludeId && cat.id === excludeId) return false
    if (excludeId && cat.parent_category_id === excludeId) return false

    const t = type as string
    const ct = cat.type as string
    if (t === 'income') return ct === 'income' || ct === 'both'
    if (t === 'expense') return ct === 'expense' || ct === 'both'
    if (t === 'both') return ct === 'both'
    return false
  })
}
```

- [ ] **Step 8.5: Add `archiveCategory` action**

```typescript
/**
 * Archive a category (soft delete).
 *
 * If the category has active subcategories, archives each child first
 * (one IndexedDB update + one `delete` mutation per child) before
 * archiving the parent. This preserves FIFO causality: the server
 * processes children before the parent.
 *
 * Uses a single loading state for the entire cascade so the UI spinner
 * reflects the full operation.
 */
async function archiveCategory(id: string) {
  loading.value = true
  error.value = null
  try {
    const now = new Date().toISOString()

    // --- Cascade: archive active children first ---
    const activeChildren = categories.value.filter(
      c => c.parent_category_id === id && c.active !== false
    )

    for (const child of activeChildren) {
      const childPendingCreate = await mutationQueue.findPendingCreate('category', child.id)
      if (childPendingCreate && childPendingCreate.id != null) {
        await mutationQueue.remove(childPendingCreate.id)
        await db.categories.delete(child.id)
        categories.value = categories.value.filter(c => c.id !== child.id)
        continue
      }

      await db.categories.update(child.id, {
        active: false,
        _sync_status: 'pending',
        _local_updated_at: now
      })
      const childIdx = categories.value.findIndex(c => c.id === child.id)
      if (childIdx !== -1) {
        categories.value[childIdx] = {
          ...categories.value[childIdx],
          active: false,
          _sync_status: 'pending',
          _local_updated_at: now
        }
      }
      await mutationQueue.enqueue({
        entity_type: 'category',
        entity_id: child.id,
        operation: 'delete',
        payload: { id: child.id }
      })
    }

    // --- Archive the parent ---
    const pendingCreate = await mutationQueue.findPendingCreate('category', id)
    if (pendingCreate && pendingCreate.id != null) {
      await mutationQueue.remove(pendingCreate.id)
      await db.categories.delete(id)
      categories.value = categories.value.filter(c => c.id !== id)
      return
    }

    await db.categories.update(id, {
      active: false,
      _sync_status: 'pending',
      _local_updated_at: now
    })
    const idx = categories.value.findIndex(c => c.id === id)
    if (idx !== -1) {
      categories.value[idx] = {
        ...categories.value[idx],
        active: false,
        _sync_status: 'pending',
        _local_updated_at: now
      }
    }
    await mutationQueue.enqueue({
      entity_type: 'category',
      entity_id: id,
      operation: 'delete',
      payload: { id }
    })
  } catch (err: any) {
    error.value = err.message || 'Error al archivar categoría'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 8.6: Add `hardDeleteCategory` action**

```typescript
/**
 * Permanently delete a category.
 *
 * Precondition: zero transactions referencing this category in IndexedDB
 * AND zero active subcategories. Throws if either condition is not met.
 */
async function hardDeleteCategory(id: string) {
  loading.value = true
  error.value = null
  try {
    const txCount = await db.transactions.where('category_id').equals(id).count()
    if (txCount > 0) {
      throw new Error('No se puede borrar una categoría con transacciones. Usa Archivar.')
    }
    const activeChildCount = categories.value.filter(
      c => c.parent_category_id === id && c.active !== false
    ).length
    if (activeChildCount > 0) {
      throw new Error('No se puede borrar una categoría con subcategorías activas. Archívalas primero.')
    }

    const pendingCreate = await mutationQueue.findPendingCreate('category', id)
    if (pendingCreate && pendingCreate.id != null) {
      await mutationQueue.remove(pendingCreate.id)
      await db.categories.delete(id)
      categories.value = categories.value.filter(c => c.id !== id)
      return
    }

    await db.categories.delete(id)
    categories.value = categories.value.filter(c => c.id !== id)

    await mutationQueue.enqueue({
      entity_type: 'category',
      entity_id: id,
      operation: 'delete_permanent',
      payload: { id }
    })
  } catch (err: any) {
    error.value = err.message || 'Error al borrar categoría permanentemente'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 8.7: Add `restoreCategory` action**

```typescript
/**
 * Restore an archived category (set active = true).
 * Does not automatically restore archived children — the user restores them
 * individually from the list view if needed.
 */
async function restoreCategory(id: string) {
  loading.value = true
  error.value = null
  try {
    const now = new Date().toISOString()
    await db.categories.update(id, {
      active: true,
      _sync_status: 'pending',
      _local_updated_at: now
    })
    const idx = categories.value.findIndex(c => c.id === id)
    if (idx !== -1) {
      categories.value[idx] = {
        ...categories.value[idx],
        active: true,
        _sync_status: 'pending',
        _local_updated_at: now
      }
    }
    const pendingCreate = await mutationQueue.findPendingCreate('category', id)
    if (pendingCreate && pendingCreate.id != null) {
      await mutationQueue.updatePayload(pendingCreate.id, {
        ...pendingCreate.payload,
        active: true
      })
    } else {
      await mutationQueue.enqueue({
        entity_type: 'category',
        entity_id: id,
        operation: 'update',
        payload: { active: true }
      })
    }
  } catch (err: any) {
    error.value = err.message || 'Error al restaurar categoría'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 8.8: Keep `deleteCategory` as alias for `archiveCategory`**

Replace the body of `deleteCategory`:

```typescript
async function deleteCategory(id: string) {
  return archiveCategory(id)
}
```

- [ ] **Step 8.9: Export new computed and actions**

Add to the store's `return` statement:

```typescript
// Computed
activeCategories,
archivedCategories,
// Actions
archiveCategory,
hardDeleteCategory,
restoreCategory,
```

- [ ] **Step 8.10: Run type-check**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS"
```

Expected: Zero errors.

- [ ] **Step 8.11: Commit**

```bash
git add src/stores/categories.ts
git commit -m "feat(store): archive, hardDelete, and restore actions for categories"
```

---

## Chunk 6: AccountDetailView — archive/hard delete/restore UI

### Task 9: Update `AccountDetailView.vue`

**Files:**
- Modify: `frontend/src/views/accounts/AccountDetailView.vue`

Replace the single "Eliminar" button with three contextual actions:
- **Archivar**: always enabled (shown when account is active).
- **Borrar**: enabled only when `hasMovements === false`; shows a tooltip otherwise.
- **Activar**: shown when account is archived (replaces the other two).

Two separate dialog refs are needed — one for archive and one for hard delete.

- [ ] **Step 9.1: Update the `<script setup>` section**

Replace the entire `<script setup>` block with:

```typescript
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAccountsStore, useTransactionsStore, useUiStore } from '@/stores'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import TransactionList from '@/components/transactions/TransactionList.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import { formatAccountType } from '@/utils/formatters'

const route = useRoute()
const router = useRouter()
const accountsStore = useAccountsStore()
const transactionsStore = useTransactionsStore()
const uiStore = useUiStore()
const exchangeRatesStore = useExchangeRatesStore()
const settingsStore = useSettingsStore()

const accountId = route.params.id as string

const showArchiveDialog = ref(false)
const showHardDeleteDialog = ref(false)
const acting = ref(false)

const account = computed(() =>
  accountsStore.accounts.find(a => a.id === accountId)
)

const balance = computed(() =>
  accountsStore.getAccountBalance(accountId)
)

const transactions = computed(() =>
  transactionsStore.getTransactionsByAccount(accountId)
)

// hasMovements is a conservative UI guard. The store's hardDeleteAccount()
// performs a definitive Dexie count query before executing — so even if this
// computed misses a transfer (transfers store not loaded here), the store will
// catch it and surface the error via uiStore.showError.
const hasMovements = computed(() => transactions.value.length > 0)

onMounted(async () => {
  try {
    await Promise.all([
      accountsStore.fetchAccountById(accountId),
      transactionsStore.fetchByAccount(accountId)
    ])
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar cuenta')
    router.push('/accounts')
  }
})

function editAccount() {
  router.push(`/accounts/${accountId}/edit`)
}

async function confirmArchive() {
  acting.value = true
  try {
    await accountsStore.archiveAccount(accountId)
    uiStore.showSuccess('Cuenta archivada')
    router.push('/accounts')
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al archivar cuenta')
  } finally {
    acting.value = false
    showArchiveDialog.value = false
  }
}

async function confirmHardDelete() {
  acting.value = true
  try {
    await accountsStore.hardDeleteAccount(accountId)
    uiStore.showSuccess('Cuenta eliminada permanentemente')
    router.push('/accounts')
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al eliminar cuenta')
  } finally {
    acting.value = false
    showHardDeleteDialog.value = false
  }
}

async function confirmRestore() {
  acting.value = true
  try {
    await accountsStore.restoreAccount(accountId)
    uiStore.showSuccess('Cuenta activada')
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al activar cuenta')
  } finally {
    acting.value = false
  }
}

function goToTransaction(transaction: any) {
  router.push(`/transactions/${transaction.id}/edit`)
}
</script>
```

- [ ] **Step 9.2: Update the template header section**

Replace the header `<div>` (the one with `flex items-center justify-between` at the top of the template):

```html
<!-- Header -->
<div class="flex items-center justify-between">
  <div class="flex items-center gap-2">
    <h1 class="text-2xl font-bold">{{ account.name }}</h1>
    <span
      v-if="account.active === false"
      class="text-xs px-2 py-0.5 rounded-full bg-dark-bg-tertiary text-dark-text-secondary"
    >
      Archivada
    </span>
  </div>

  <div class="flex gap-2 flex-wrap justify-end">
    <template v-if="account.active !== false">
      <BaseButton variant="secondary" size="sm" @click="editAccount">
        Editar
      </BaseButton>
      <BaseButton variant="secondary" size="sm" @click="showArchiveDialog = true">
        Archivar
      </BaseButton>
      <!-- Hard delete: disabled with tooltip when account has movements -->
      <div class="relative group">
        <BaseButton
          variant="danger"
          size="sm"
          :disabled="hasMovements"
          @click="!hasMovements && (showHardDeleteDialog = true)"
        >
          Borrar
        </BaseButton>
        <div
          v-if="hasMovements"
          class="absolute right-0 top-full mt-1 z-10 hidden group-hover:block
                 w-64 rounded-lg bg-dark-bg-tertiary border border-dark-bg-tertiary/50
                 px-3 py-2 text-xs text-dark-text-secondary shadow-lg"
        >
          No se puede borrar una cuenta con movimientos. Usa Archivar.
        </div>
      </div>
    </template>

    <template v-else>
      <BaseButton variant="secondary" size="sm" :loading="acting" @click="confirmRestore">
        Activar
      </BaseButton>
    </template>
  </div>
</div>
```

- [ ] **Step 9.3: Replace the single `ConfirmDialog` with two dialogs**

Remove the existing `ConfirmDialog` block at the bottom of the template. Replace with:

```html
<!-- Archive confirmation dialog -->
<ConfirmDialog
  :show="showArchiveDialog"
  title="Archivar cuenta"
  message="¿Archivar esta cuenta? La cuenta dejará de aparecer en tus balances y en el dashboard, pero todos tus movimientos anteriores (transacciones y transferencias) se conservarán intactos en el historial."
  confirm-text="Archivar"
  variant="warning"
  :loading="acting"
  @confirm="confirmArchive"
  @cancel="showArchiveDialog = false"
/>

<!-- Hard delete confirmation dialog -->
<ConfirmDialog
  :show="showHardDeleteDialog"
  title="Borrar cuenta permanentemente"
  message="¿Borrar esta cuenta permanentemente? Esta acción no se puede deshacer."
  confirm-text="Borrar permanentemente"
  variant="danger"
  :loading="acting"
  @confirm="confirmHardDelete"
  @cancel="showHardDeleteDialog = false"
/>
```

- [ ] **Step 9.4: Run type-check and lint**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS" && npm run lint 2>&1 | grep -v "^$"
```

Expected: Zero errors and zero lint warnings.

- [ ] **Step 9.5: Commit**

```bash
git add src/views/accounts/AccountDetailView.vue
git commit -m "feat(ui): archive/hard-delete/restore UI in AccountDetailView"
```

---

## Chunk 7: CategoryEditView — archive/hard delete/restore UI

### Task 10: Update `CategoryEditView.vue`

**Files:**
- Modify: `frontend/src/views/categories/CategoryEditView.vue`

Same structural pattern as `AccountDetailView`. The archive modal text depends on whether the category has active subcategories.

- [ ] **Step 10.1: Update the `<script setup>` section**

Replace the entire `<script setup>` block with:

```typescript
<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCategoriesStore, useUiStore } from '@/stores'
import { db } from '@/offline'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import { CATEGORY_TYPES, CATEGORY_ICONS, CATEGORY_COLORS } from '@/utils/constants'
import { required, minLength, maxLength } from '@/utils/validators'
import type { UpdateCategoryDto, CategoryType } from '@/types'

const route = useRoute()
const router = useRouter()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const categoryId = route.params.id as string

const showArchiveDialog = ref(false)
const showHardDeleteDialog = ref(false)
const acting = ref(false)
// Transaction count loaded once on mount — used to enable/disable hard delete.
const txCount = ref(0)

const category = computed(() =>
  categoriesStore.categories.find(c => c.id === categoryId)
)

const form = reactive({
  name: '',
  type: '' as CategoryType,
  icon: '',
  color: '#3b82f6',
  parent_category_id: '' as string
})

const errors = reactive({
  name: '',
  type: ''
})

const hasChildren = computed(() =>
  categoriesStore.getSubcategories(categoryId).length > 0
)

// Active subcategories count — drives the cascade message and hard-delete guard.
const activeChildCount = computed(() =>
  categoriesStore.categories.filter(
    c => c.parent_category_id === categoryId && c.active !== false
  ).length
)

// Archive modal message: mentions N subcategories when a cascade will occur.
const archiveMessage = computed(() => {
  if (activeChildCount.value > 0) {
    const n = activeChildCount.value
    return `Archivar esta categoría también archivará sus ${n} subcategoría${n === 1 ? '' : 's'}. ¿Continuar?`
  }
  return '¿Archivar esta categoría? Dejará de aparecer en los formularios, pero todas las transacciones asociadas se conservarán intactas en el historial.'
})

const parentOptions = computed(() => {
  if (!form.type) return []
  return categoriesStore.compatibleParentCategories(form.type as CategoryType, categoryId)
    .map(cat => ({
      value: cat.id,
      label: `${cat.icon ?? ''} ${cat.name}`.trim()
    }))
})

watch(() => form.type, () => {
  form.parent_category_id = ''
})

onMounted(async () => {
  if (!category.value) {
    try {
      await categoriesStore.fetchCategoryById(categoryId)
    } catch (error: any) {
      uiStore.showError(error.message || 'Error al cargar categoría')
      router.push('/categories')
      return
    }
  }

  if (category.value) {
    form.name = category.value.name
    form.type = category.value.type
    form.icon = category.value.icon || ''
    form.color = category.value.color || '#3b82f6'
    form.parent_category_id = category.value.parent_category_id ?? ''
  }

  // Load transaction count for hard-delete guard (single Dexie index read).
  txCount.value = await db.transactions.where('category_id').equals(categoryId).count()
})

function validateForm(): boolean {
  let isValid = true
  const nameValidation = required(form.name) && minLength(2)(form.name) && maxLength(50)(form.name)
  if (nameValidation !== true) {
    errors.name = nameValidation as string
    isValid = false
  } else {
    errors.name = ''
  }
  if (!form.type) {
    errors.type = 'Debes seleccionar un tipo'
    isValid = false
  } else {
    errors.type = ''
  }
  return isValid
}

async function handleSubmit() {
  if (!validateForm()) return
  try {
    const data: UpdateCategoryDto = {
      name: form.name.trim(),
      type: form.type,
      icon: form.icon || undefined,
      color: form.color || undefined,
      parent_category_id: form.parent_category_id || undefined
    }
    if (!form.parent_category_id && category.value?.parent_category_id) {
      (data as Record<string, unknown>).parent_category_id = ''
    }
    await categoriesStore.updateCategory(categoryId, data)
    uiStore.showSuccess('Categoría actualizada exitosamente')
    router.push('/categories')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al actualizar categoría')
  }
}

function handleCancel() {
  router.back()
}

async function confirmArchive() {
  acting.value = true
  try {
    await categoriesStore.archiveCategory(categoryId)
    uiStore.showSuccess('Categoría archivada')
    router.push('/categories')
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al archivar categoría')
  } finally {
    acting.value = false
    showArchiveDialog.value = false
  }
}

async function confirmHardDelete() {
  acting.value = true
  try {
    await categoriesStore.hardDeleteCategory(categoryId)
    uiStore.showSuccess('Categoría eliminada permanentemente')
    router.push('/categories')
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al eliminar categoría')
  } finally {
    acting.value = false
    showHardDeleteDialog.value = false
  }
}

async function confirmRestore() {
  acting.value = true
  try {
    await categoriesStore.restoreCategory(categoryId)
    uiStore.showSuccess('Categoría activada')
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al activar categoría')
  } finally {
    acting.value = false
  }
}
</script>
```

- [ ] **Step 10.2: Update the template header**

Replace the header `<div>` (the one containing `Editar Categoría` and the single `Eliminar` button):

```html
<!-- Header -->
<div class="flex items-center justify-between">
  <div class="flex items-center gap-2">
    <h1 class="text-2xl font-bold">Editar Categoría</h1>
    <span
      v-if="category.active === false"
      class="text-xs px-2 py-0.5 rounded-full bg-dark-bg-tertiary text-dark-text-secondary"
    >
      Archivada
    </span>
  </div>

  <div class="flex gap-2 flex-wrap justify-end">
    <template v-if="category.active !== false">
      <BaseButton variant="secondary" size="sm" @click="showArchiveDialog = true">
        Archivar
      </BaseButton>
      <div class="relative group">
        <BaseButton
          variant="danger"
          size="sm"
          :disabled="txCount > 0"
          @click="txCount === 0 && (showHardDeleteDialog = true)"
        >
          Borrar
        </BaseButton>
        <div
          v-if="txCount > 0"
          class="absolute right-0 top-full mt-1 z-10 hidden group-hover:block
                 w-64 rounded-lg bg-dark-bg-tertiary border border-dark-bg-tertiary/50
                 px-3 py-2 text-xs text-dark-text-secondary shadow-lg"
        >
          No se puede borrar una categoría con transacciones. Usa Archivar.
        </div>
      </div>
    </template>

    <template v-else>
      <BaseButton variant="secondary" size="sm" :loading="acting" @click="confirmRestore">
        Activar
      </BaseButton>
    </template>
  </div>
</div>
```

- [ ] **Step 10.3: Replace the single `ConfirmDialog` with two dialogs**

Remove the existing dialog block and replace with:

```html
<!-- Archive confirmation dialog -->
<ConfirmDialog
  :show="showArchiveDialog"
  title="Archivar categoría"
  :message="archiveMessage"
  confirm-text="Archivar"
  variant="warning"
  :loading="acting"
  @confirm="confirmArchive"
  @cancel="showArchiveDialog = false"
/>

<!-- Hard delete confirmation dialog -->
<ConfirmDialog
  :show="showHardDeleteDialog"
  title="Borrar categoría permanentemente"
  message="¿Borrar esta categoría permanentemente? Esta acción no se puede deshacer."
  confirm-text="Borrar permanentemente"
  variant="danger"
  :loading="acting"
  @confirm="confirmHardDelete"
  @cancel="showHardDeleteDialog = false"
/>
```

- [ ] **Step 10.4: Run type-check and lint**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS" && npm run lint 2>&1 | grep -v "^$"
```

Expected: Zero errors and zero lint warnings.

- [ ] **Step 10.5: Commit**

```bash
git add src/views/categories/CategoryEditView.vue
git commit -m "feat(ui): archive/hard-delete/restore UI in CategoryEditView"
```

---

## Chunk 8: List Views — "Mostrar archivadas" toggle

### Task 11: Update `AccountsListView.vue`

**Files:**
- Modify: `frontend/src/views/accounts/AccountsListView.vue`

Add a toggle that shows/hides archived accounts. Active accounts are shown via the existing `AccountList` component. Archived accounts render as a flat list at the bottom with reduced opacity and an "Archivada" badge.

- [ ] **Step 11.1: Update script section**

Replace the `<script setup>` block:

```typescript
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountsStore, useUiStore } from '@/stores'
import AccountList from '@/components/accounts/AccountList.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'

const router = useRouter()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const showArchived = ref(false)

const activeAccounts = computed(() => accountsStore.activeAccounts)
const archivedAccounts = computed(() => accountsStore.archivedAccounts)

const balances = computed(() => {
  const map = new Map<string, number>()
  accountsStore.accounts.forEach(account => {
    map.set(account.id, accountsStore.getAccountBalance(account.id))
  })
  return map
})

onMounted(async () => {
  try {
    await accountsStore.fetchAccounts()
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar cuentas')
  }
})

function goToAccount(account: any) {
  router.push(`/accounts/${account.id}`)
}

function createAccount() {
  router.push('/accounts/new')
}
</script>
```

- [ ] **Step 11.2: Update template**

Replace the full `<template>` block:

```html
<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Cuentas</h1>
      <button
        v-if="archivedAccounts.length > 0"
        class="text-sm text-dark-text-secondary underline underline-offset-2"
        @click="showArchived = !showArchived"
      >
        {{ showArchived ? 'Ocultar archivadas' : `Mostrar archivadas (${archivedAccounts.length})` }}
      </button>
    </div>

    <!-- Active accounts -->
    <AccountList
      :accounts="activeAccounts"
      :balances="balances"
      :loading="accountsStore.loading"
      @account-click="goToAccount"
      @create-click="createAccount"
    />

    <!-- Archived accounts (shown at bottom when toggle is on) -->
    <div v-if="showArchived && archivedAccounts.length > 0" class="space-y-2">
      <p class="text-sm text-dark-text-secondary font-medium">Archivadas</p>
      <div
        v-for="account in archivedAccounts"
        :key="account.id"
        class="opacity-50 cursor-pointer rounded-xl bg-dark-bg-secondary
               border border-dark-bg-tertiary/50 px-4 py-3 flex items-center gap-3
               hover:opacity-70 transition-opacity"
        @click="goToAccount(account)"
      >
        <div class="flex-1 min-w-0">
          <p class="font-medium truncate">{{ account.name }}</p>
          <p class="text-xs text-dark-text-secondary">{{ account.currency }}</p>
        </div>
        <span class="text-xs px-2 py-0.5 rounded-full bg-dark-bg-tertiary text-dark-text-secondary flex-shrink-0">
          Archivada
        </span>
      </div>
    </div>

    <!-- Floating Action Button -->
    <SimpleFab
      aria-label="Crear nueva cuenta"
      @click="createAccount"
    />
  </div>
</template>
```

- [ ] **Step 11.3: Run type-check and lint**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS" && npm run lint 2>&1 | grep -v "^$"
```

Expected: Zero errors.

- [ ] **Step 11.4: Commit**

```bash
git add src/views/accounts/AccountsListView.vue
git commit -m "feat(ui): show archived accounts toggle in AccountsListView"
```

---

### Task 12: Update `CategoriesListView.vue`

**Files:**
- Modify: `frontend/src/views/categories/CategoriesListView.vue`

Same toggle pattern. The active categories use the existing collapsible tree (which now excludes archived items automatically because `categoryTree` was updated in Task 8.3). Archived categories appear in a flat list at the bottom.

- [ ] **Step 12.1: Update script section**

Replace the `<script setup>` block:

```typescript
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoriesStore, useUiStore } from '@/stores'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'
import { formatCategoryType } from '@/utils/formatters'

const router = useRouter()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const expandedGroups = ref<Set<string>>(new Set())
const showArchived = ref(false)

function toggleGroup(parentId: string) {
  if (expandedGroups.value.has(parentId)) {
    expandedGroups.value.delete(parentId)
  } else {
    expandedGroups.value.add(parentId)
  }
}

onMounted(async () => {
  try {
    await categoriesStore.fetchCategories()
  } catch (error: any) {
    console.error('Error loading categories in CategoriesListView:', error)
    uiStore.showError(error.message || 'Error al cargar categorías')
  }
})

function goToCategory(id: string) {
  router.push(`/categories/${id}/edit`)
}

function createCategory() {
  router.push('/categories/new')
}

const groupsWithChildren = () =>
  categoriesStore.categoryTree.filter(g => g.children.length > 0)

const standaloneGroups = () =>
  categoriesStore.categoryTree.filter(g => g.children.length === 0)
</script>
```

- [ ] **Step 12.2: Update template — add header toggle and archived section**

Replace the header `<div>` with:

```html
<!-- Header -->
<div class="flex items-center justify-between">
  <h1 class="text-2xl font-bold">Categorías</h1>
  <button
    v-if="categoriesStore.archivedCategories.length > 0"
    class="text-sm text-dark-text-secondary underline underline-offset-2"
    @click="showArchived = !showArchived"
  >
    {{ showArchived ? 'Ocultar archivadas' : `Mostrar archivadas (${categoriesStore.archivedCategories.length})` }}
  </button>
</div>
```

After the closing `</div>` of the `<!-- Grouped category list -->` section (just before `SimpleFab`), add:

```html
<!-- Archived categories (shown at bottom when toggle is on) -->
<div v-if="showArchived && categoriesStore.archivedCategories.length > 0" class="space-y-2">
  <p class="text-sm text-dark-text-secondary font-medium">Archivadas</p>
  <div
    v-for="cat in categoriesStore.archivedCategories"
    :key="cat.id"
    class="opacity-50 cursor-pointer rounded-xl bg-dark-bg-secondary
           border border-dark-bg-tertiary/50 flex items-center px-4 py-3 gap-3
           hover:opacity-70 transition-opacity"
    @click="goToCategory(cat.id)"
  >
    <div
      v-if="cat.color"
      class="w-3 h-3 rounded-full flex-shrink-0"
      :style="{ backgroundColor: cat.color }"
    ></div>
    <span class="text-xl flex-shrink-0">{{ cat.icon || '📁' }}</span>
    <span class="font-medium truncate flex-1 min-w-0">{{ cat.name }}</span>
    <span class="text-xs px-2 py-0.5 rounded-full bg-dark-bg-tertiary text-dark-text-secondary flex-shrink-0">
      Archivada
    </span>
  </div>
</div>
```

- [ ] **Step 12.3: Run type-check and lint**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1 | grep "error TS" && npm run lint 2>&1 | grep -v "^$"
```

Expected: Zero errors.

- [ ] **Step 12.4: Commit**

```bash
git add src/views/categories/CategoriesListView.vue
git commit -m "feat(ui): show archived categories toggle in CategoriesListView"
```

---

## Chunk 9: Final Verification

### Task 13: Verify dropdown filtering and run final checks

**Files:**
- Verify: `frontend/src/components/categories/CategorySelect.vue` (read-only check — no code changes expected)
- Verify: `frontend/src/components/accounts/AccountSelect.vue` (read-only check — no code changes expected)

`AccountSelect.vue` already filters `account.active` — no change needed.
`CategorySelect.vue` reads from `categoriesStore.categoryTree`. Since Task 8.3 updated `categoryTree` to iterate over `activeCategories`, the dropdown will automatically exclude archived categories.

- [ ] **Step 13.1: Confirm `CategorySelect` uses `categoryTree` (not raw `categories`)**

```bash
grep -n "categoryTree\|\.categories" /Users/angelcorredor/Code/Wallet/frontend/src/components/categories/CategorySelect.vue
```

Expected: Only `categoryTree` references. If `categories.value` appears, add an `active !== false` filter at that usage point.

- [ ] **Step 13.2: Confirm `AccountSelect` already filters active-only**

```bash
grep -n "active" /Users/angelcorredor/Code/Wallet/frontend/src/components/accounts/AccountSelect.vue
```

Expected: A line with `account.active` in the filter returning `true`/`false`. No change needed.

- [ ] **Step 13.3: Run full type-check and lint**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check && npm run lint
```

Expected: Both commands exit with code 0 and zero output to stderr.

- [ ] **Step 13.4: Manual acceptance checklist**

Work through each item in the browser:

1. **Archive account with movements:** Create account + transaction. Navigate to detail. Click "Archivar". Confirm correct Spanish modal text. After confirm: redirected to list, account absent. Toggle "Mostrar archivadas" — account appears with "Archivada" badge.
2. **Restore archived account:** From detail view of archived account, "Activar" button appears. Click it. Account returns to active list.
3. **Hard delete blocked by movements:** With movements present, hover "Borrar" — tooltip text visible. Button is not clickable.
4. **Hard delete with no movements:** Create new account with no transactions. "Borrar" enabled. Confirm modal: "¿Borrar esta cuenta permanentemente? Esta acción no se puede deshacer." After confirm: account gone, does not appear in "Mostrar archivadas".
5. **Archive category with subcategories:** Parent + 2 children. Click "Archivar" on parent. Modal: "Archivar esta categoría también archivará sus 2 subcategorías. ¿Continuar?" After confirm: all three absent from main list, visible in "Mostrar archivadas".
6. **Archive category without subcategories:** Modal: "¿Archivar esta categoría? Dejará de aparecer en los formularios, pero todas las transacciones asociadas se conservarán intactas en el historial."
7. **Hard delete blocked (category):** Category with transactions. "Borrar" tooltip: "No se puede borrar una categoría con transacciones. Usa Archivar."
8. **Transaction form category dropdown:** Archived category absent. Active categories present.
9. **Transfer form account dropdown:** Archived account absent. Active accounts present.

- [ ] **Step 13.5: Commit if any verification fixes were needed**

If Steps 13.1 or 13.2 found issues that required changes:

```bash
git add src/components/categories/CategorySelect.vue src/components/accounts/AccountSelect.vue
git commit -m "fix(components): exclude archived items from account and category dropdowns"
```

---

## Edge Cases and Error Handling Summary

**Offline hard delete with server having movements:** If `hardDeleteAccount` is called while offline with no movements in local IndexedDB, the `delete_permanent` mutation is enqueued. When connectivity returns, the server may reject the request (409 or 422) if other devices have created movements since the last sync. The SyncManager's existing 4xx permanent-error path marks the mutation as `error` and surfaces it via the sync error badge. The account remains deleted locally — no automatic reconciliation. The user must manually re-create the account if needed.

**Cascade archive partial failure:** `archiveCategory` iterates children sequentially within a single `try/catch`. If one child fails (e.g., IndexedDB write error), the `catch` re-throws immediately. Children already archived stay archived. The parent is not archived. The user sees the error toast and can retry — re-archiving the parent will attempt to archive the remaining active children again (idempotent for already-archived children since `active !== false` filter skips them).

**`active` field missing on server-fetched records:** Categories from server responses before this feature will lack `active`. The Dexie v6 migration backfills existing IndexedDB rows. New rows from `fullReadSync` are stored as-is. The `activeCategories !== false` guard treats `undefined` as active, so they appear correctly without requiring a backend migration first.

**`hasMovements` in `AccountDetailView` is conservative:** Only checks the loaded `transactions` array (no transfers). The store's `hardDeleteAccount` performs a definitive three-way Dexie count (transactions + source transfers + destination transfers) before executing. If the UI guard passes but the store guard catches a transfer, `uiStore.showError` surfaces the message: "No se puede borrar una cuenta con movimientos. Usa Archivar."
