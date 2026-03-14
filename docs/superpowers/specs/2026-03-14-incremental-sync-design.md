# Incremental Sync: Cursor-Based Design Spec

**Date:** 2026-03-14
**Ticket:** [Sync incremental](https://www.notion.so/32179901d1b881f9851fc356ea129ff6)
**Status:** Approved

---

## Overview

`fullReadSync` descarga todos los registros del backend en cada carga de la app (`limit: 10000` para transactions y transfers). Con volúmenes crecientes de datos, esto escala mal. Esta feature reemplaza ese comportamiento con un sync incremental basado en cursores opacos: el backend solo retorna registros modificados desde el último sync, y responde `304 Not Modified` cuando no hubo cambios.

Se incluye también un flag `initialSyncComplete` en el sync store para eliminar el "doble render" visible en el chart cuando Dexie está vacío al cargar.

---

## Scope

**In scope:**
- Cursor-based incremental sync para: transactions, transfers, accounts, categories, dashboards (incluyendo widgets via cascada), exchange_rates
- `304 Not Modified` cuando no hubo cambios — siempre con nuevo cursor en el header
- Full sync **solo cuando Dexie está vacío** (primer load / install) o cuando el usuario lo solicita explícitamente desde Settings
- Botón "Forzar sincronización completa" en la pantalla de configuración
- Flag `initialSyncComplete` en el sync store
- `updated_at` cascade en dashboard cuando un widget es creado/modificado/eliminado

**Explícitamente excluido del incremental sync:**
- `user_settings` — el endpoint retorna `{ settings: { key: value } }` (dict plano), no un array de entidades con `updated_at`. Se sincronizan solo durante full syncs.

**Out of scope:**
- Full sync periódico automático (eliminado — hard-deletes se detectan solo via full sync manual)
- Multi-usuario (el cursor está diseñado para extenderse — ver nota en ticket de multi-usuario)
- Sync push / WebSockets

---

## Cursor Design

El cursor es un string opaco en base64 que encapsula metadata del sync. El cliente nunca interpreta su contenido.

```json
base64url({ "t": "2026-03-14T10:00:00.000Z", "v": 1 })
```

- `t` — timestamp ISO UTC del momento en que se realizó la consulta (no del último cambio)
- `v` — versión del schema del cursor (permite evolución futura, ej. añadir `uid` para multi-usuario)

**El cursor representa "última vez que consultaste"**, no "último cambio". Esto garantiza que el time window de la siguiente consulta sea siempre el mínimo posible.

El backend **siempre** genera y retorna un nuevo cursor en `X-Sync-Cursor` con el timestamp actual, incluso en respuestas `304`.

---

## Backend

### Helper: `app/utils/sync_cursor.py`

```python
from datetime import datetime, timezone

def encode_cursor() -> str:
    """Genera un cursor con datetime.now(timezone.utc)."""
    # Usar timezone-aware datetime para evitar ambigüedad naive/aware
    # Serializar como ISO con sufijo Z: "2026-03-14T10:00:00.000Z"

def decode_cursor(header: str | None) -> datetime | None:
    """
    Decodifica el cursor. Retorna None si:
    - header es None
    - base64 inválido
    - JSON malformado
    - campo 't' ausente o inválido
    - versión desconocida

    NUNCA lanza excepción — errores se tratan como full sync silencioso.
    Retorna datetime naive (sin timezone) para ser compatible con las
    columnas updated_at de BaseModel, que también son naive.
    """
```

**Nota sobre timezone:** `BaseModel.updated_at` usa `datetime.utcnow()` (naive). El `decode_cursor` debe retornar un datetime naive para que la comparación `WHERE updated_at >= updated_since` sea consistente. Internamente el cursor codifica UTC en formato ISO con `Z`, pero al decodificar se retorna naive (strip timezone info).

### Cambios en repositorios

Los repositorios afectados reciben `updated_since: datetime | None = None` en sus métodos de listado. Si se provee, agrega:

```sql
WHERE updated_at >= updated_since
```

El operador es `>=` (inclusivo) — un registro modificado exactamente en el timestamp del cursor debe ser retornado.

**Repositorios y métodos afectados:**
- `TransactionRepository.list()` — ya acepta filtros; agregar `updated_since`
- `TransferRepository.get_all()` — agregar `updated_since`
- `AccountRepository.get_all()` — agregar `updated_since`
- `CategoryRepository.get_all()` — agregar `updated_since`
- `DashboardRepository.get_all()` — agregar `updated_since`
- `ExchangeRateRepository.get_all()` — agregar `updated_since`. **Nota:** `ExchangeRateRepository` no hereda de `BaseRepository` — tiene su propio `get_all()` con raw SQL. El `updated_since` se agrega directamente como cláusula `WHERE` en ese método, sin delegar a un método base.

`SettingsRepository` queda sin cambios (excluido del incremental sync).

### DashboardWidgets: cascade `updated_at`

DashboardWidgets no tienen endpoint de listado propio — se acceden via `GET /api/v1/dashboards/:id`. Para que el cursor de dashboards detecte cambios en widgets, el servicio `DashboardCrudService` (en `app/services/dashboard_crud.py`) debe actualizar `Dashboard.updated_at` en `create_widget`, `update_widget` y `delete_widget`:

```python
# Al final de cada operación de widget en DashboardCrudService:
db.session.execute(
    update(Dashboard)
    .where(Dashboard.id == widget.dashboard_id)
    .values(updated_at=datetime.now(timezone.utc).replace(tzinfo=None))  # naive UTC
)
db.session.commit()
```

Consecuencia: si el cursor de dashboards retorna `304`, ningún widget cambió. Si retorna `200`, el frontend re-fetcha `getById()` para cada dashboard devuelto y hace `bulkPut` de sus widgets.

### Cambios en endpoints

**Regla para endpoints con paginación (transactions, transfers):**
Cuando `If-Sync-Cursor` está presente (modo incremental), el endpoint retorna una **lista plana** sin wrapper de paginación. Cuando no hay cursor (full sync), mantiene el comportamiento actual con `paginated_response()`.

Cada endpoint `GET` relevante sigue este patrón:

```
1. Leer header If-Sync-Cursor
2. decode_cursor(header) → updated_since (o None)
3. Consultar repositorio con updated_since
4. new_cursor = encode_cursor()
5. Siempre incluir header X-Sync-Cursor: new_cursor en la response
6a. Si results vacío Y updated_since NO es None → 304 (sin body, requerido HTTP)
6b. Si updated_since es None → response normal (paginated o lista según endpoint)
6c. Si results no vacío Y updated_since NO es None → 200 + lista plana de registros
```

**Endpoints afectados:**
- `GET /api/v1/transactions` — paginado sin cursor / lista plana con cursor
- `GET /api/v1/transfers` — paginado sin cursor / lista plana con cursor
- `GET /api/v1/accounts` — lista plana siempre
- `GET /api/v1/categories` — lista plana siempre
- `GET /api/v1/dashboards` — lista plana siempre
- `GET /api/v1/exchange-rates` — **caso especial**: el endpoint actualmente retorna `{ rates: [...], last_updated: "..." }`. Con cursor, retorna lista plana de `ExchangeRate` records (igual que el resto). Sin cursor (full sync), mantiene el formato actual.

`GET /api/v1/dashboards/:id` (widgets) no recibe cursor — se llama solo cuando el endpoint de dashboards retornó `200`.

`GET /api/v1/settings` — sin cambios (excluido del incremental sync).

**Flask 304 + headers:** Para garantizar que `X-Sync-Cursor` llegue en la respuesta `304`, el backend debe construir el response explícitamente, no usar `abort(304)`. Flask puede ignorar headers en 304 si se usa `abort()` directamente.

---

## Frontend

### `syncClient` — cliente Axios dedicado para sync

El interceptor de respuesta de `apiClient` desenvuelve el payload (`{ success: true, data: ... }`) y descarta los headers. El SyncManager necesita acceder a `X-Sync-Cursor` en los response headers. Por eso se crea un cliente Axios separado **sin** el interceptor de desenvuelto:

**`frontend/src/api/sync-client.ts`**:
```ts
// Axios instance sin response interceptor de desenvuelto.
// Retorna AxiosResponse<T> completo — SyncManager maneja el parsing del envelope.
// validateStatus permite 304 sin lanzar error.
export const syncClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
  validateStatus: (status) => (status >= 200 && status < 300) || status === 304,
})
```

El SyncManager usa `syncClient.get<{ success: boolean; data: T[] }>(url, config)` directamente. Debe desenvolver el payload manualmente: `response.data.data` para lista plana, o `response.data.data.items` para paginated (solo en full sync path). El cursor se extrae con `response.headers['x-sync-cursor']`.

### Cursores en Dexie

La tabla `settings` (ya existente) almacena cursores de sync. Para evitar colisión con las user settings reales (keys como `primary_currency`), todos los keys de sync usan el prefijo `__sync__`:

| key | valor |
|-----|-------|
| `__sync__cursor_transactions` | `eyJ0Ijo...` |
| `__sync__cursor_transfers` | `eyJ0Ijo...` |
| `__sync__cursor_accounts` | `eyJ0Ijo...` |
| `__sync__cursor_categories` | `eyJ0Ijo...` |
| `__sync__cursor_dashboards` | `eyJ0Ijo...` |
| `__sync__cursor_exchange_rates` | `eyJ0Ijo...` |

**Schema de Dexie:** No se requiere bump de versión. La tabla `settings` ya acepta keys arbitrarios.

### Lógica en `processQueue()` — cuándo hacer full vs incremental

Al final de `processQueue()` (después de flush de mutations), la decisión es:

```ts
const dexieIsEmpty = await isDexieEmpty()  // true si accounts, transactions, transfers están vacíos

if (dexieIsEmpty) {
  await this.fullReadSync()   // primer load o Dexie limpiado
} else {
  await this.incrementalSync()  // caso normal
}
```

`isDexieEmpty()` comprueba que las tablas principales (accounts, transactions, transfers) tengan count = 0. La presencia de cualquier dato en Dexie indica que hubo un full sync previo y se puede usar el modo incremental.

**Full sync forzado desde Settings:** El SyncManager expone un método público `forceFullSync()` que limpia todos los cursores `__sync__cursor_*` de Dexie y ejecuta `fullReadSync()` directamente. El botón de Settings llama a este método.

### `incrementalSync()` — nuevo método privado

Para cada entidad en paralelo (`Promise.allSettled`):
1. Leer cursor de Dexie (`__sync__cursor_<entity>`)
2. Request con `syncClient.get(url, { headers: { 'If-Sync-Cursor': cursor ?? undefined } })`
3. Leer `response.headers['x-sync-cursor']` → guardar en Dexie
4. Si `response.status === 304` → no tocar Dexie con datos de la entidad
5. Si `response.status === 200` → `bulkPut` con `response.data.data` (lista plana)

Para dashboards: si `200`, también re-fetchar `getById()` (usando `apiClient` existente) para cada dashboard retornado y hacer `bulkPut` de sus widgets.

**Comportamiento ante fallo parcial:** Si el request de una entidad falla (5xx, timeout), `Promise.allSettled` continúa con las demás. La entidad fallida **no actualiza su cursor** — en el próximo `processQueue()` se reintentará con el cursor anterior.

### `fullReadSync()` — modificaciones

El `fullReadSync()` existente se migra de `apiClient` a `syncClient` con llamadas directas a las URLs. Al finalizar exitosamente, guarda el cursor de cada response (`response.headers['x-sync-cursor']`) en `__sync__cursor_<entity>` en Dexie.

Las llamadas en `fullReadSync()` no envían `If-Sync-Cursor` (full sync = sin cursor). El SyncManager desenvuelve manualmente: `response.data.data.items ?? response.data.data`.

### `initialSyncComplete` flag (Parte 2)

El `syncStore` de Pinia (existente en `frontend/src/stores/sync.ts`) recibe un nuevo campo y su setter, siguiendo el patrón establecido (`setSyncing`, etc.):

```ts
const initialSyncComplete = ref(false)

function setInitialSyncComplete(value: boolean): void {
  initialSyncComplete.value = value
}

return {
  // ... existentes ...
  initialSyncComplete: readonly(initialSyncComplete),
  setInitialSyncComplete,
}
```

Se pone `true` en el bloque `finally` de `processQueue()`:

```ts
async processQueue() {
  try {
    // ... mutations + full/incremental sync ...
  } catch (e) {
    // ... manejo de error existente ...
  } finally {
    getSyncStore().setInitialSyncComplete(true)  // siempre, pase lo que pase
  }
}
```

Condición para mostrar skeleton en componentes:
```ts
const showSkeleton = computed(() =>
  !syncStore.initialSyncComplete && dexieIsEmpty.value
)
```

Si Dexie ya tiene data de sesiones anteriores (`dexieIsEmpty = false`), `showSkeleton` nunca es `true`.

### Multi-tab

Los cursores (`__sync__cursor_*`) se guardan en la tabla `settings` de Dexie compartida entre tabs. Si dos tabs corren `incrementalSync()` simultáneamente con el mismo cursor, ambas hacen el mismo `bulkPut` — operación idempotente (upsert), sin riesgo de corrupción. No se implementa locking.

---

## Testing

### Backend

- **`sync_cursor.py`**: encode/decode roundtrip; cursor `None`; base64 inválido; JSON malformado; campo `t` ausente — todos retornan `None` sin exception; datetime retornado es naive
- **Repositorios**: registro antes de `updated_since` no incluido; registro después incluido; registro exactamente en el timestamp **incluido** (`>=`)
- **Endpoints (integración)**:
  - Sin cursor → `200` + body con formato original + `X-Sync-Cursor`
  - Con cursor, sin cambios → `304` + **sin body** + `X-Sync-Cursor` nuevo
  - Con cursor, con cambios → `200` + **lista plana** + `X-Sync-Cursor` nuevo
  - Con cursor inválido → `200` + body completo (full sync silencioso) + `X-Sync-Cursor` nuevo
  - Primer sync (BD vacía, sin cursor) → `200` + array vacío + `X-Sync-Cursor` (no `304`)
- **DashboardWidget cascade**: crear/modificar/eliminar widget actualiza `Dashboard.updated_at` del padre

### Frontend

- **`syncClient`**: `response.headers['x-sync-cursor']` accesible; `304` no lanza error
- **Decisión full vs incremental**: Dexie vacío → `fullReadSync()`; Dexie con data → `incrementalSync()`
- **`forceFullSync()`**: limpia cursores y ejecuta `fullReadSync()`
- **`incrementalSync()`**: mock `304` → Dexie no modificado, cursor actualizado; mock `200` → `bulkPut` con registros recibidos, cursor actualizado; fallo parcial → otras entidades no afectadas, cursor del fallido sin cambios
- **`fullReadSync()` guarda cursores**: verificar `__sync__cursor_*` en Dexie tras full sync exitoso
- **Namespace**: keys `__sync__*` no colisionan con user settings
- **`initialSyncComplete`**: `false` al inicio; `true` tras primer `processQueue()` (incluso si falla, via `finally`)
- **Skeleton**: visible solo cuando `!initialSyncComplete && dexieIsEmpty`
