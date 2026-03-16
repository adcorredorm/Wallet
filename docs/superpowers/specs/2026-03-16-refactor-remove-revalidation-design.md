# Design: Refactor — Eliminar fetchAllWithRevalidation y fetchByIdWithRevalidation

**Date:** 2026-03-16
**Notion:** https://www.notion.so/32579901d1b881538397d2c7436c630e
**Status:** Approved

---

## Overview

Los stores del frontend tienen dos mecanismos paralelos para obtener datos:

1. **SyncManager** — orquestador oficial. Mantiene Dexie actualizado vía `fullReadSync` e `incrementalSync`. Dispara `wallet:sync-complete` → `refreshFromDB()` en todos los stores.
2. **`fetchAllWithRevalidation` / `fetchByIdWithRevalidation`** — patrón stale-while-revalidate heredado de antes del SyncManager. Cada vez que una vista monta, hace un GET al backend en background.

El segundo mecanismo es redundante. Este refactor lo elimina completamente.

**Contrato post-refactor:**
```
Backend ←→ SyncManager ←→ Dexie ←→ Stores ←→ UI
```
Los stores solo leen Dexie. Nunca hacen llamadas HTTP directas en sus funciones de fetch.

---

## Scope

**In scope:**
- Refactorizar 9 funciones de fetch en 4 stores
- Eliminar `transfers.fetchByAccount` (0 callers en vistas)
- Eliminar parámetro `type?` de `fetchCategories` (0 callers pasan tipo)
- Eliminar parámetro `customFilters?` de `fetchTransactions` y `fetchTransfers` (el filtrado lo hace el backend vía sync, no las vistas)
- Eliminar parámetro `customFilters?` de `transactions.fetchByAccount` (0 callers pasan filtros)
- Actualizar `DashboardView.vue`: cambiar `fetchTransactions({ limit: 5 })` → `fetchTransactions()` (el `{ limit: 5 }` era un parámetro para el backend que ya no aplica; la vista ya filtra vía `slice(0, 5)` en computed)
- Limpiar imports deprecados en los 4 stores
- Limpiar mocks en 5 archivos de tests
- Limpiar comentarios stale en `sync-manager.ts`
- Eliminar `repository.ts` completo
- Limpiar `offline/index.ts`

**Out of scope:**
- Modificar SyncManager (salvo comentarios stale)
- Modificar funciones de escritura (create/update/delete)
- Cambios en backend

---

## Funciones afectadas

### Commit 1 — Funciones de lista

| Función | Store | Cambio |
|---|---|---|
| `fetchTransactions(customFilters?)` | transactions.ts | Eliminar param → `refreshFromDB()` |
| `fetchTransfers(customFilters?)` | transfers.ts | Eliminar param → `refreshFromDB()` |
| `fetchCategories(type?)` | categories.ts | Eliminar param → `refreshFromDB()` |
| `fetchByAccount(accountId)` | transfers.ts | **Eliminar función** (0 callers) |

### Commit 2 — Funciones por ID + cleanup

| Función | Store | Implementación nueva |
|---|---|---|
| `fetchAccountById(id)` | accounts.ts | `db.accounts.get(id)` + normalizeBalance |
| `fetchTransactionById(id)` | transactions.ts | `db.transactions.get(id)` |
| `fetchTransferById(id)` | transfers.ts | `db.transfers.get(id)` |
| `fetchCategoryById(id)` | categories.ts | `db.categories.get(id)` |
| `fetchByAccount(accountId)` | transactions.ts | `db.transactions.where('account_id').equals(accountId).toArray()` |

---

## Patrones de implementación

### Funciones de lista → refreshFromDB()
```typescript
async function fetchTransactions() {
  loading.value = true
  error.value = null
  try {
    await refreshFromDB()
  } catch (err: any) {
    error.value = err.message || 'Error al cargar transacciones'
    throw err
  } finally {
    loading.value = false
  }
}
```
Idéntico al patrón ya usado por `fetchAccounts()`. Aplica igual para `fetchTransfers()` y `fetchCategories()`.

### Funciones por ID → Dexie direct read
```typescript
async function fetchAccountById(id: string) {
  loading.value = true
  error.value = null
  try {
    const item = await db.accounts.get(id)
    if (item) {
      const normalized = normalizeBalance(item)
      const index = accounts.value.findIndex(a => a.id === id)
      if (index >= 0) accounts.value[index] = normalized
      else accounts.value.push(normalized)
      return normalized
    }
  } catch (err: any) {
    error.value = err.message || 'Error al cargar cuenta'
    throw err
  } finally {
    loading.value = false
  }
}
```

**Nota sobre balance en `fetchAccountById`:** La implementación anterior preservaba `balances.value.get(id)` para evitar que el backend sobreescribiera el balance correcto. Tras el refactor, leemos directamente de Dexie — que ya contiene el balance correcto (escrito por `adjustBalance()` en cada operación). La lógica de preservación se elimina porque ya no hay riesgo de sobreescritura del backend. El computed `accountsWithBalances` sigue usando `balances.value.get(id)?.balance ?? account.balance` como fallback, que es correcto.

### transactions.fetchByAccount → Dexie where query
```typescript
async function fetchByAccount(accountId: string) {
  loading.value = true
  error.value = null
  try {
    const data = await db.transactions
      .where('account_id').equals(accountId)
      .toArray()
    transactions.value = [...data].sort(byDateDesc)
  } catch (err: any) {
    error.value = err.message || 'Error al cargar transacciones de la cuenta'
    throw err
  } finally {
    loading.value = false
  }
}
```

**Nota:** `fetchByAccount` reemplaza `transactions.value` con solo las transacciones del account solicitado. Este es el mismo comportamiento que la implementación anterior. Implica que si el usuario navega de `AccountDetailView` a otra vista sin que el SyncManager haya disparado `refreshFromDB()`, `transactions.value` contendrá solo las transacciones de ese account. Esto es aceptable — las vistas que necesitan todas las transacciones llaman `fetchTransactions()` en su propio `onMounted`.

---

## Cleanup de infraestructura

### `offline/repository.ts` — eliminar completamente
El archivo solo contiene `fetchAllWithRevalidation`, `fetchByIdWithRevalidation`, y helpers internos (`toLocalItem`, `mergeWithPending`) que solo sirven a esas dos funciones. Sin exportaciones activas, el archivo no tiene razón de existir.

### `offline/index.ts` — remover línea de re-export
```typescript
// Eliminar esta línea:
export { fetchAllWithRevalidation, fetchByIdWithRevalidation } from './repository'
```

### Imports en stores — limpiar
Remover `fetchAllWithRevalidation` y/o `fetchByIdWithRevalidation` de los imports de `@/offline` en los 4 stores. Los demás imports (`db`, `generateTempId`, `mutationQueue`) se mantienen.

### Tests — limpiar mocks stale
Remover `fetchAllWithRevalidation` y `fetchByIdWithRevalidation` del objeto mock de `@/offline` en:
- `frontend/src/stores/transactions.spec.ts`
- `frontend/src/stores/transfers.spec.ts`
- `frontend/src/stores/accounts.spec.ts`
- `frontend/src/stores/exchangeRates.spec.ts`
- `frontend/src/stores/__tests__/categories-hierarchy.spec.ts`

**Caso especial — `accounts.spec.ts` línea ~361:** hay una aserción que importa `fetchAllWithRevalidation` directamente desde `@/offline` dentro del cuerpo del test y verifica que no fue llamada. Una vez eliminada del barrel, esta importación retornará `undefined` y la aserción fallará silenciosamente. Eliminar el bloque completo de esa aserción — la garantía que ofrece (que no se llama al backend) se verifica implícitamente por el resto del test suite tras el refactor.

### `sync-manager.ts` — limpiar comentarios stale
Remover o actualizar las referencias a `repository.ts` por nombre en los comentarios (líneas ~216-217 y ~1488). El archivo no existirá después del refactor.

### `DashboardView.vue` — actualizar llamada
```typescript
// Antes:
transactionsStore.fetchTransactions({ limit: 5 })

// Después:
transactionsStore.fetchTransactions()
```
El `{ limit: 5 }` era un hint para el backend (ya no aplica). La vista ya limita vía `transactionsStore.transactions.slice(0, 5)` en el computed `recentTransactions`.

---

## Edge cases

- **Item no en Dexie (`get()` → `undefined`)**: función retorna `undefined` silenciosamente. Las vistas ya manejan esto: `AccountEditView`, `TransactionEditView`, `TransferEditView` solo llaman la función si el item no está ya en state, y redirigen si la función no retorna nada.
- **`AccountDetailView` con `fetchByAccount`**: usa el Dexie where query — solo retorna transacciones del account solicitado. Comportamiento idéntico al filtro anterior.
- **Pending items en Dexie**: `db.*.get(id)` y `db.*.where().toArray()` retornan todos los items independientemente de `_sync_status` — correcto, queremos mostrar también los pending.
- **Dashboard carga todas las transacciones**: `fetchTransactions()` carga `db.transactions.toArray()` (todas). `recentTransactions` computed aplica `slice(0, 5)`. Performance aceptable — Dexie es local y la lectura es síncrona para el tamaño típico de datos de una app de finanzas personales.

---

## Archivos modificados

**Stores:**
- `frontend/src/stores/accounts.ts`
- `frontend/src/stores/transactions.ts`
- `frontend/src/stores/transfers.ts`
- `frontend/src/stores/categories.ts`

**Infraestructura offline:**
- `frontend/src/offline/repository.ts` (**eliminar**)
- `frontend/src/offline/index.ts`
- `frontend/src/offline/sync-manager.ts` (comentarios stale)

**Vistas:**
- `frontend/src/views/DashboardView.vue`

**Tests:**
- `frontend/src/stores/transactions.spec.ts`
- `frontend/src/stores/transfers.spec.ts`
- `frontend/src/stores/accounts.spec.ts`
- `frontend/src/stores/exchangeRates.spec.ts`
- `frontend/src/stores/__tests__/categories-hierarchy.spec.ts`

---

## Acceptance criteria

- [ ] Ningún store llama al backend en sus funciones de fetch
- [ ] Todas las vistas siguen mostrando datos correctos al montar
- [ ] `repository.ts` eliminado; `fetchAllWithRevalidation` y `fetchByIdWithRevalidation` no existen en el codebase
- [ ] `DashboardView` llama `fetchTransactions()` sin argumentos
- [ ] `cd frontend && npm run type-check` — sin errores
- [ ] `cd frontend && npm run lint` — sin errores
- [ ] `cd backend && python -m pytest` — 305/305 pasando
