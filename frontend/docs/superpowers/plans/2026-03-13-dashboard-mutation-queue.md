# Dashboard Mutation Queue Integration — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire dashboards and dashboard_widgets into the existing offline-first mutation queue so that all write operations (create/update/delete) go through `mutationQueue.enqueue()` + `SyncManager`, replacing the current inline fire-and-forget API pattern.

**Architecture:** Extend `PendingMutation.entity_type` to include `'dashboard' | 'dashboard_widget'`, add the corresponding send/resolve/mark handlers to `SyncManager`, and rewrite all 6 write actions in `dashboards.ts` to follow the same three-step offline-first pattern (Dexie → reactive state → mutationQueue) used by accounts/transactions/transfers/categories.

**Tech Stack:** Vue 3 + Pinia, Dexie v5, TypeScript strict

---

## Chunk 1: Type and SyncManager changes

### Task 1: Extend `PendingMutation.entity_type`

**Files:**
- Modify: `src/offline/types.ts:80`

- [ ] **Step 1: Add dashboard entity types to the union**

In `src/offline/types.ts`, change line 80:

```typescript
// BEFORE:
entity_type: 'account' | 'transaction' | 'transfer' | 'category' | 'setting'

// AFTER:
entity_type: 'account' | 'transaction' | 'transfer' | 'category' | 'setting' | 'dashboard' | 'dashboard_widget'
```

- [ ] **Step 2: Verify type-check passes**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check
```

Expected: TypeScript errors in sync-manager.ts because the switches are now non-exhaustive. That is expected — they get fixed in Task 2.

- [ ] **Step 3: Commit**

```bash
git add src/offline/types.ts
git commit -m "feat(offline): add dashboard | dashboard_widget to PendingMutation entity_type"
```

---

### Task 2: Extend SyncManager with dashboard/widget handlers

**Files:**
- Modify: `src/offline/sync-manager.ts`

The SyncManager has 7 switch statements and 1 lookup map that all need new cases. Also needs new import types and two new private send methods.

- [ ] **Step 1: Add DTO imports**

At the top of `src/offline/sync-manager.ts`, the existing type import from `@/types` is:

```typescript
import type {
  Account,
  Transaction,
  Transfer,
  Category,
  CreateAccountDto,
  UpdateAccountDto,
  CreateTransactionDto,
  UpdateTransactionDto,
  CreateTransferDto,
  UpdateTransferDto,
  CreateCategoryDto,
  UpdateCategoryDto
} from '@/types'
```

Add a second import block after it:

```typescript
import type {
  Dashboard,
  DashboardWidget,
  CreateDashboardDto,
  UpdateDashboardDto,
  CreateWidgetDto,
  UpdateWidgetDto,
} from '@/types/dashboard'
```

- [ ] **Step 2: Extend DEPENDENCY_FIELDS map**

Change `DEPENDENCY_FIELDS` (around line 142) from:

```typescript
const DEPENDENCY_FIELDS: Record<PendingMutation['entity_type'], string[]> = {
  account: [],
  transaction: ['account_id', 'category_id'],
  transfer: ['source_account_id', 'destination_account_id'],
  category: ['parent_category_id'],
  setting: []
}
```

To:

```typescript
const DEPENDENCY_FIELDS: Record<PendingMutation['entity_type'], string[]> = {
  account: [],
  transaction: ['account_id', 'category_id'],
  transfer: ['source_account_id', 'destination_account_id'],
  category: ['parent_category_id'],
  setting: [],
  // dashboard_widget depends on dashboard via dashboard_id (so if a dashboard
  // CREATE fails offline, any widget creates for it are blocked too).
  dashboard: [],
  dashboard_widget: ['dashboard_id'],
}
```

- [ ] **Step 3: Add cases to `sendToServer()` switch**

In `sendToServer()` (around line 393), add two new cases at the bottom of the switch:

```typescript
case 'dashboard':
  return this.sendDashboard(mutation, payload)

case 'dashboard_widget':
  return this.sendDashboardWidget(mutation, payload)
```

- [ ] **Step 4: Add `sendDashboard()` private method**

Add after the `sendSetting()` method:

```typescript
private async sendDashboard(
  mutation: PendingMutation,
  payload: Record<string, unknown>
): Promise<Dashboard> {
  switch (mutation.operation) {
    case 'create': {
      const { id: _id, ...createPayload } = payload as Record<string, unknown> & { id?: string }
      void _id
      return dashboardsApi.create(createPayload as unknown as CreateDashboardDto)
    }

    case 'update': {
      const { id: _id, ...updatePayload } = payload as Record<string, unknown> & { id?: string }
      void _id
      return dashboardsApi.update(mutation.entity_id, updatePayload as unknown as UpdateDashboardDto)
    }

    case 'delete':
      await dashboardsApi.delete(mutation.entity_id)
      return { id: mutation.entity_id } as Dashboard
  }
}
```

- [ ] **Step 5: Add `sendDashboardWidget()` private method**

Add after `sendDashboard()`:

```typescript
/**
 * Send a dashboard_widget mutation to the API.
 *
 * Why extract dashboard_id from payload?
 * The dashboards API requires dashboardId as a URL path parameter (not body).
 * The store encodes it in the payload so the SyncManager can route the request
 * to the correct endpoint. We strip it from the body before sending.
 */
private async sendDashboardWidget(
  mutation: PendingMutation,
  payload: Record<string, unknown>
): Promise<DashboardWidget> {
  const dashboardId = payload['dashboard_id'] as string

  switch (mutation.operation) {
    case 'create': {
      const { id: _id, dashboard_id: _did, ...createPayload } =
        payload as Record<string, unknown> & { id?: string; dashboard_id?: string }
      void _id
      void _did
      return dashboardsApi.createWidget(dashboardId, createPayload as unknown as CreateWidgetDto)
    }

    case 'update': {
      const { id: _id, dashboard_id: _did, ...updatePayload } =
        payload as Record<string, unknown> & { id?: string; dashboard_id?: string }
      void _id
      void _did
      return dashboardsApi.updateWidget(
        dashboardId,
        mutation.entity_id,
        updatePayload as unknown as UpdateWidgetDto
      )
    }

    case 'delete':
      await dashboardsApi.deleteWidget(dashboardId, mutation.entity_id)
      return { id: mutation.entity_id } as DashboardWidget
  }
}
```

- [ ] **Step 6: Add cases to `resolveTemporaryId()` switch**

In `resolveTemporaryId()` (around line 678), add after the `case 'setting':` break:

```typescript
case 'dashboard':
  // Update dashboard_widget rows that reference this dashboard via dashboard_id.
  await db.dashboardWidgets
    .where('dashboard_id')
    .equals(tempId)
    .modify({ dashboard_id: realId })
  break

case 'dashboard_widget':
  // dashboard_widget does not act as a FK in any other table.
  break
```

- [ ] **Step 7: Add cases to `replaceEntityWithRealId()` switch**

In `replaceEntityWithRealId()` (around line 770), add after `case 'setting':` break:

```typescript
case 'dashboard': {
  const old = await db.dashboards.get(tempId)
  if (old) {
    const updated: LocalDashboard = { ...old, id: realId, server_id: realId }
    await db.dashboards.delete(tempId)
    await db.dashboards.put(updated)
  }
  break
}

case 'dashboard_widget': {
  const old = await db.dashboardWidgets.get(tempId)
  if (old) {
    const updated: LocalDashboardWidget = { ...old, id: realId, server_id: realId }
    await db.dashboardWidgets.delete(tempId)
    await db.dashboardWidgets.put(updated)
  }
  break
}
```

- [ ] **Step 8: Add cases to `markSynced()` switch**

In `markSynced()` (around line 855), add after `case 'setting':` block:

```typescript
case 'dashboard':
  await db.dashboards.update(serverResult.id, syncFields)
  break

case 'dashboard_widget':
  await db.dashboardWidgets.update(serverResult.id, syncFields)
  break
```

- [ ] **Step 9: Add cases to `markEntitySyncStatus()` switch**

In `markEntitySyncStatus()` (around line 994), add after `case 'setting':` line:

```typescript
case 'dashboard': await db.dashboards.update(entityId, fields); break
case 'dashboard_widget': await db.dashboardWidgets.update(entityId, fields); break
```

- [ ] **Step 10: Add cases to `markError()` switch**

In `markError()` (around line 1031), add after `case 'setting':` block:

```typescript
case 'dashboard':
  await db.dashboards.update(entityId, errorFields)
  break

case 'dashboard_widget':
  await db.dashboardWidgets.update(entityId, errorFields)
  break
```

- [ ] **Step 11: Extend `findServerId()` to look up dashboard/widget tables**

In `findServerId()` (around line 463), add after the `category` lookup:

```typescript
const dashboard = await db.dashboards.get(tempId)
if (dashboard?.server_id) return dashboard.server_id

const widget = await db.dashboardWidgets.get(tempId)
if (widget?.server_id) return widget.server_id
```

- [ ] **Step 12: Update `syncDashboards()` comment**

The old comment said dashboards are "read-only in the sync layer (no mutation queue entries)". Update this line to reflect the new reality:

```typescript
// Why prune stale records for dashboards?
// Dashboards are now wired into the mutation queue, but deletes still need
// reconciliation: after a fullReadSync the server is authoritative, so any
// dashboard ID no longer returned by the server should be removed from Dexie.
```

- [ ] **Step 13: Run type-check**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check
```

Expected: PASS (no TypeScript errors).

- [ ] **Step 14: Commit**

```bash
git add src/offline/sync-manager.ts
git commit -m "feat(sync): add dashboard and dashboard_widget handlers to SyncManager"
```

---

## Chunk 2: Store and app wiring

### Task 3: Rewrite dashboards.ts write operations

**Files:**
- Modify: `src/stores/dashboards.ts`

Replace the current inline fire-and-forget async pattern with the standard three-step offline-first pattern: (1) write to Dexie, (2) update reactive state, (3) `mutationQueue.enqueue()`.

- [ ] **Step 1: Add missing imports**

At the top of `src/stores/dashboards.ts`, add:

```typescript
import { mutationQueue } from '@/offline'
import { generateTempId } from '@/offline/temp-id'
```

- [ ] **Step 2: Rewrite `createDashboard()`**

Replace the entire `createDashboard` function with:

```typescript
async function createDashboard(dto: CreateDashboardDto) {
  const settingsStore = useSettingsStore()
  const payload: CreateDashboardDto = {
    ...dto,
    display_currency: dto.display_currency || settingsStore.primaryCurrency
  }

  loading.value = true
  error.value = null
  try {
    const tempId = generateTempId()
    const now = new Date().toISOString()
    const optimistic: LocalDashboard = {
      id: tempId,
      name: payload.name,
      description: payload.description ?? null,
      display_currency: payload.display_currency,
      layout_columns: payload.layout_columns ?? 2,
      is_default: payload.is_default ?? false,
      sort_order: payload.sort_order ?? 0,
      created_at: now,
      updated_at: now,
      _sync_status: 'pending',
      _local_updated_at: now,
    }

    await db.dashboards.put(optimistic)
    dashboards.value.push(optimistic)

    await mutationQueue.enqueue({
      entity_type: 'dashboard',
      entity_id: tempId,
      operation: 'create',
      payload: { ...payload, client_id: tempId } as Record<string, unknown>,
    })

    return optimistic
  } catch (err: any) {
    error.value = err.message || 'Error al crear dashboard'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 3: Rewrite `updateDashboard()`**

Replace with:

```typescript
async function updateDashboard(id: string, dto: UpdateDashboardDto) {
  loading.value = true
  error.value = null
  try {
    const existing = await db.dashboards.get(id)
    if (!existing) throw new Error('Dashboard not found in local DB')

    const now = new Date().toISOString()
    const patch = {
      ...(dto.name !== undefined && { name: dto.name }),
      ...(dto.description !== undefined && { description: dto.description }),
      ...(dto.display_currency !== undefined && { display_currency: dto.display_currency }),
      ...(dto.layout_columns !== undefined && { layout_columns: dto.layout_columns }),
      ...(dto.is_default !== undefined && { is_default: dto.is_default }),
      ...(dto.sort_order !== undefined && { sort_order: dto.sort_order }),
      updated_at: now,
      _sync_status: 'pending' as const,
      _local_updated_at: now,
    }

    await db.dashboards.update(id, patch)
    const optimistic: LocalDashboard = { ...existing, ...patch }

    const idx = dashboards.value.findIndex(d => d.id === id)
    if (idx >= 0) dashboards.value[idx] = optimistic
    if (currentDashboard.value?.id === id) {
      currentDashboard.value = { ...optimistic, widgets: currentDashboard.value.widgets }
    }

    // Merge into pending CREATE if one exists (avoids POST + PATCH round-trip)
    const pendingCreate = await mutationQueue.findPendingCreate('dashboard', id)
    if (pendingCreate?.id != null) {
      await mutationQueue.updatePayload(pendingCreate.id, { ...pendingCreate.payload, ...dto })
    } else {
      await mutationQueue.enqueue({
        entity_type: 'dashboard',
        entity_id: id,
        operation: 'update',
        payload: dto as Record<string, unknown>,
      })
    }

    return optimistic
  } catch (err: any) {
    error.value = err.message || 'Error al actualizar dashboard'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 4: Rewrite `deleteDashboard()`**

Replace with:

```typescript
async function deleteDashboard(id: string) {
  loading.value = true
  error.value = null
  try {
    await db.dashboards.delete(id)
    const widgetIds = await db.dashboardWidgets.where('dashboard_id').equals(id).primaryKeys()
    if (widgetIds.length > 0) await db.dashboardWidgets.bulkDelete(widgetIds)

    dashboards.value = dashboards.value.filter(d => d.id !== id)
    if (currentDashboard.value?.id === id) currentDashboard.value = null

    // If there is a pending CREATE (dashboard never reached server), cancel it
    const pendingCreate = await mutationQueue.findPendingCreate('dashboard', id)
    if (pendingCreate?.id != null) {
      await mutationQueue.remove(pendingCreate.id)
      // No DELETE mutation needed — entity never existed on server
    } else {
      await mutationQueue.enqueue({
        entity_type: 'dashboard',
        entity_id: id,
        operation: 'delete',
        payload: {},
      })
    }
  } catch (err: any) {
    error.value = err.message || 'Error al eliminar dashboard'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 5: Rewrite `createWidget()`**

Replace with:

```typescript
async function createWidget(dashboardId: string, dto: CreateWidgetDto) {
  loading.value = true
  error.value = null
  try {
    const tempId = generateTempId()
    const now = new Date().toISOString()
    const optimistic: LocalDashboardWidget = {
      id: tempId,
      dashboard_id: dashboardId,
      widget_type: dto.widget_type,
      title: dto.title,
      position_x: dto.position_x ?? 0,
      position_y: dto.position_y ?? 0,
      width: dto.width ?? 1,
      height: dto.height ?? 1,
      config: dto.config,
      created_at: now,
      updated_at: now,
      _sync_status: 'pending',
      _local_updated_at: now,
    }

    await db.dashboardWidgets.put(optimistic)
    if (currentDashboard.value?.id === dashboardId) {
      currentDashboard.value = {
        ...currentDashboard.value,
        widgets: [...currentDashboard.value.widgets, optimistic],
      }
    }

    await mutationQueue.enqueue({
      entity_type: 'dashboard_widget',
      entity_id: tempId,
      operation: 'create',
      // dashboard_id is included so SyncManager can route to the correct endpoint
      payload: { ...dto, dashboard_id: dashboardId, client_id: tempId } as Record<string, unknown>,
    })

    return optimistic
  } catch (err: any) {
    error.value = err.message || 'Error al crear widget'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 6: Rewrite `updateWidget()`**

Replace with:

```typescript
async function updateWidget(dashboardId: string, widgetId: string, dto: UpdateWidgetDto) {
  loading.value = true
  error.value = null
  try {
    const existing = await db.dashboardWidgets.get(widgetId)
    if (!existing) throw new Error('Widget not found in local DB')

    const now = new Date().toISOString()
    const patch = {
      ...(dto.widget_type !== undefined && { widget_type: dto.widget_type }),
      ...(dto.title !== undefined && { title: dto.title }),
      ...(dto.config !== undefined && { config: dto.config }),
      ...(dto.position_x !== undefined && { position_x: dto.position_x }),
      ...(dto.position_y !== undefined && { position_y: dto.position_y }),
      ...(dto.width !== undefined && { width: dto.width }),
      ...(dto.height !== undefined && { height: dto.height }),
      updated_at: now,
      _sync_status: 'pending' as const,
      _local_updated_at: now,
    }

    await db.dashboardWidgets.update(widgetId, patch)
    const optimistic: LocalDashboardWidget = { ...existing, ...patch }

    if (currentDashboard.value?.id === dashboardId) {
      const widgetIdx = currentDashboard.value.widgets.findIndex(w => w.id === widgetId)
      if (widgetIdx >= 0) {
        const newWidgets = [...currentDashboard.value.widgets]
        newWidgets[widgetIdx] = optimistic
        currentDashboard.value = { ...currentDashboard.value, widgets: newWidgets }
      }
    }

    const pendingCreate = await mutationQueue.findPendingCreate('dashboard_widget', widgetId)
    if (pendingCreate?.id != null) {
      await mutationQueue.updatePayload(pendingCreate.id, { ...pendingCreate.payload, ...dto })
    } else {
      await mutationQueue.enqueue({
        entity_type: 'dashboard_widget',
        entity_id: widgetId,
        operation: 'update',
        // dashboard_id is needed by SyncManager to build the correct URL
        payload: { ...dto, dashboard_id: dashboardId } as Record<string, unknown>,
      })
    }

    return optimistic
  } catch (err: any) {
    error.value = err.message || 'Error al actualizar widget'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 7: Rewrite `deleteWidget()`**

Replace with:

```typescript
async function deleteWidget(dashboardId: string, widgetId: string) {
  loading.value = true
  error.value = null
  try {
    await db.dashboardWidgets.delete(widgetId)
    if (currentDashboard.value?.id === dashboardId) {
      currentDashboard.value = {
        ...currentDashboard.value,
        widgets: currentDashboard.value.widgets.filter(
          w => w.id !== widgetId
        ) as LocalDashboardWidget[],
      }
    }

    const pendingCreate = await mutationQueue.findPendingCreate('dashboard_widget', widgetId)
    if (pendingCreate?.id != null) {
      await mutationQueue.remove(pendingCreate.id)
    } else {
      await mutationQueue.enqueue({
        entity_type: 'dashboard_widget',
        entity_id: widgetId,
        operation: 'delete',
        // dashboard_id needed by SyncManager to build the DELETE URL
        payload: { dashboard_id: dashboardId },
      })
    }
  } catch (err: any) {
    error.value = err.message || 'Error al eliminar widget'
    throw err
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 8: Run type-check and lint**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check && npm run lint
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/stores/dashboards.ts
git commit -m "feat(store): wire dashboards/widgets into offline mutation queue"
```

---

### Task 4: Wire dashboardsStore into sync-complete event

**Files:**
- Modify: `src/main.ts`

- [ ] **Step 1: Import dashboardsStore**

In `src/main.ts`, find where the other stores are imported for the sync-complete handler and add:

```typescript
const dashboardsStore = useDashboardsStore()
```

(If `useDashboardsStore` is not already imported, add the import at the top of the file.)

- [ ] **Step 2: Add dashboardsStore.refreshFromDB() to sync-complete handler**

Find the `wallet:sync-complete` event listener and add the dashboards refresh call:

```typescript
window.addEventListener('wallet:sync-complete', () => {
  accountsStore.refreshFromDB()
  transactionsStore.refreshFromDB()
  transfersStore.refreshFromDB()
  categoriesStore.refreshFromDB()
  dashboardsStore.refreshFromDB()          // ← ADD THIS
  accountsStore.recomputeBalancesFromTransactions()
})
```

- [ ] **Step 3: Run type-check**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check
```

Expected: PASS.

- [ ] **Step 4: Build**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run build
```

Expected: build succeeds, no errors.

- [ ] **Step 5: Commit**

```bash
git add src/main.ts
git commit -m "feat(app): refresh dashboards store after sync-complete"
```

---

## Final verification

- [ ] Deploy to Nginx: `docker cp dist/. wallet_frontend:/usr/share/nginx/html/`
- [ ] Clear site data in browser
- [ ] Test offline: edit a widget → changes persist immediately
- [ ] Go online → verify pending mutation syncs (check console for `[SyncManager] Mutation id=X synced successfully`)
- [ ] Test create dashboard offline → create widget offline → go online → both appear on server
- [ ] Test delete widget offline → go online → widget gone from server
