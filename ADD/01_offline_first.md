# Wallet - Offline-First Specification

## 1. Descripcion General

**Offline-first** es una estrategia de arquitectura donde la aplicacion trata la conexion a internet como una mejora y no como un requisito. La aplicacion funciona completamente sin conexion, almacenando datos localmente en el navegador, y sincroniza con el servidor cuando la conexion esta disponible.

### Vision

Transformar Wallet de una SPA dependiente de conexion a una aplicacion offline-first que permita al usuario registrar y gestionar sus finanzas en cualquier momento y lugar, sin importar el estado de la red. La sincronizacion con el backend ocurre de forma transparente, sin intervencion del usuario.

### Valor para el Usuario

- **Disponibilidad total**: Registrar un gasto en el metro, en un avion, o en cualquier zona sin cobertura
- **Velocidad percibida**: Las operaciones se ejecutan contra la base de datos local (instantaneas), eliminando la latencia de red
- **Confianza**: Los datos nunca se pierden por problemas de conexion; la app siempre responde
- **Experiencia nativa**: Comportamiento indistinguible de una aplicacion instalada gracias a PWA

---

## 2. Objetivos

### Objetivo Principal

Implementar una arquitectura offline-first que permita operar Wallet sin conexion a internet, con sincronizacion automatica y transparente cuando la red este disponible.

### Objetivos Especificos

1. Convertir la SPA en una PWA instalable con Service Worker para cachear assets y shell de la aplicacion
2. Implementar una base de datos local (IndexedDB) como fuente de verdad inmediata para todas las operaciones del usuario
3. Crear una cola de mutaciones que encole operaciones de escritura offline y las sincronice al recuperar conexion
4. Detectar cambios en el estado de la red y reflejarlos en la UI de forma no intrusiva
5. Garantizar la integridad de datos entre la base local y el servidor mediante una estrategia de resolucion de conflictos
6. Mantener la experiencia de usuario fluida sin importar el estado de la conexion

---

## 3. Principios de Diseno

- **Local-first**: IndexedDB es la fuente de verdad inmediata para el render inicial. La UI siempre lee de la base local y nunca espera al servidor para mostrar datos — incluso en cold-start (IndexedDB vacia). La API es siempre una operacion de background
- **IndexedDB como unica fuente de verdad para datos mostrados**: El frontend es una aplicacion autonoma (standalone). IndexedDB es la unica fuente de verdad para TODOS los datos que se muestran en la UI — incluyendo balances de cuentas. El backend se usa EXCLUSIVAMENTE para sincronizacion: enviar mutaciones locales al servidor y descargar escrituras del servidor hechas desde otros dispositivos. Ningun endpoint del backend se consulta con el proposito de mostrar datos al usuario
- **Balances computados localmente**: Los balances de cuentas se calculan siempre a partir de las transacciones y transferencias almacenadas en IndexedDB. El endpoint `/accounts/:id/balance` del backend NO se usa para mostrar balances. Esto es critico porque el endpoint del servidor no incluye transacciones pendientes de sincronizacion creadas offline, lo cual produciria balances incorrectos
- **Sync transparente**: La sincronizacion ocurre en segundo plano. El usuario no necesita iniciarla ni gestionarla
- **Optimistic UI**: Las operaciones de escritura se aplican inmediatamente en la base local y la UI se actualiza al instante. La sincronizacion con el servidor es eventual
- **Graceful degradation**: Si la sincronizacion falla, la app sigue funcionando. Los errores de sync se manejan silenciosamente con reintentos
- **Minimal backend changes**: El backend actual (Flask REST API) se mantiene practicamente intacto. Los cambios se concentran en el frontend
- **Progressive enhancement**: La funcionalidad offline se agrega encima de la arquitectura existente, sin reescribir los stores ni la capa de API

---

## 4. Alcance

### Dentro del Alcance

| # | Feature | Descripcion |
|---|---------|-------------|
| 4.1 | PWA + Service Worker | Registrar Service Worker via `vite-plugin-pwa`, cachear app shell y assets estaticos |
| 4.2 | IndexedDB local | Base de datos local con Dexie.js que replica el esquema de PostgreSQL |
| 4.3 | Cola de mutaciones | Sistema de encolado para operaciones CREATE, UPDATE, DELETE realizadas offline |
| 4.4 | Sincronizacion automatica | Enviar mutaciones pendientes al servidor al detectar conexion |
| 4.5 | Cache de lecturas | Almacenar respuestas de la API en IndexedDB para servir datos offline |
| 4.6 | Deteccion de red | Indicador visual del estado de conexion con `useOnline()` de @vueuse/core |
| 4.7 | Resolucion de conflictos | Estrategia last-write-wins basada en `updated_at` para un solo usuario |
| 4.8 | Indicadores de sync | Feedback visual sutil del estado de sincronizacion (pendiente, sincronizando, sincronizado, error) |
| 4.9 | Manifest PWA | `manifest.json` con iconos, colores e informacion para instalacion |

### Fuera del Alcance

- Sincronizacion multi-usuario o multi-dispositivo simultaneo
- Merge manual de conflictos (no necesario con un solo usuario)
- Push notifications desde el servidor
- Sincronizacion parcial o selectiva de datos (se sincroniza todo)
- Encriptacion de la base de datos local
- Streaming / real-time updates (WebSocket)
- Compresion de payloads de sync
- Cambios en el esquema de la API REST del backend

---

## 5. Arquitectura Propuesta

### 5.1 Stack Tecnologico Nuevo

| Tecnologia | Proposito | Justificacion |
|-----------|-----------|---------------|
| `vite-plugin-pwa` | Generacion de Service Worker y manifest | Integracion nativa con Vite, usa Workbox internamente |
| Workbox | Estrategias de caching del Service Worker | Estandar de la industria para PWA, mantenido por Google |
| Dexie.js | Wrapper sobre IndexedDB | API prometida, tipado TypeScript, migraciones de esquema, excelente rendimiento |
| `@vueuse/core` (useOnline) | Deteccion reactiva del estado de red | Ya instalado como dependencia del proyecto |

### 5.2 Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────┐
│                       VISTA (Vue Components)                │
│   DashboardView, AccountsListView, TransactionCreateView... │
├─────────────────────────────────────────────────────────────┤
│                    STORES (Pinia - existentes)              │
│   accounts, transactions, transfers, categories, ui        │
│   + nuevo: sync (estado de sincronizacion)                 │
├─────────────────────────────────────────────────────────────┤
│                    OFFLINE LAYER (nuevo)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ OfflineDB   │  │ MutationQueue│  │  SyncManager      │  │
│  │ (Dexie.js)  │  │ (cola FIFO)  │  │  (orquestador)    │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                │                    │             │
├─────────┼────────────────┼────────────────────┼─────────────┤
│         │         API LAYER (Axios - existente)             │
│         │         apiClient con interceptors                │
├─────────┼───────────────────────────────────────────────────┤
│         │         SERVICE WORKER (nuevo)                    │
│         │         Workbox: cache assets + runtime caching   │
├─────────┼───────────────────────────────────────────────────┤
│   IndexedDB              Network               PostgreSQL   │
│   (navegador)            (internet)             (servidor)  │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Flujo de Datos: Lectura

```
1. Componente solicita datos al store (ej: fetchAccounts)
2. Store consulta OfflineDB (IndexedDB) → retorna datos locales inmediatamente (pueden ser un array vacio en cold-start)
3. Si hay conexion: store lanza fetch a la API en segundo plano (nunca bloquea el retorno)
4. Respuesta de la API se guarda en OfflineDB (actualiza cache local)
5. Store reactivo se actualiza via callback → componente re-renderiza si los datos cambiaron
6. Si IndexedDB estaba vacia y la API responde: la UI pasa de estado vacio/skeleton a mostrar datos
7. Si IndexedDB estaba vacia y la API falla: la UI muestra estado vacio (no error critico)
```

Este patron se conoce como **stale-while-revalidate sin bloqueo**: IndexedDB es siempre la fuente de verdad para el render inicial, incluso cuando esta vacia. La API es siempre una operacion de background. No existe un camino bloqueante (cold-start) — la UI es responsable de manejar el estado vacio inicial con skeletons o spinners mientras llega la revalidacion.

**Proteccion de balances en revalidacion**: Cuando la revalidacion de background actualiza las cuentas desde el servidor (via `bulkPut` en IndexedDB), el endpoint de lista del servidor puede retornar `balance: 0` para cuentas con transacciones pendientes de sincronizacion (porque el servidor no tiene esas transacciones aun). Los callbacks `onFreshData` en `fetchAccounts()` y `fetchAccountById()` detectan esta situacion y restauran el balance correcto desde la fuente local (`balances.value` o `accounts.value`), reparando tambien IndexedDB despues del `bulkPut`.

### 5.4 Flujo de Datos: Escritura

```
1. Componente ejecuta accion (ej: createTransaction)
2. Store genera un UUID temporal (client-side)
3. Store escribe en OfflineDB inmediatamente → UI se actualiza
4. Store ajusta el balance de la cuenta afectada inmediatamente via adjustBalance()
5. Store agrega la mutacion a la MutationQueue
6. Si hay conexion:
   a. SyncManager procesa la cola en orden FIFO
   b. Envia peticion a la API
   c. Recibe respuesta con datos del servidor (ID real, timestamps)
   d. Actualiza OfflineDB con datos confirmados del servidor
   e. Marca mutacion como completada y la elimina de la cola
7. Si NO hay conexion:
   a. La mutacion queda en la cola
   b. Cuando vuelva la conexion, el SyncManager procesa toda la cola
```

**Nota sobre el paso 4**: `adjustBalance(accountId, delta)` actualiza tres lugares simultaneamente: el mapa reactivo `balances.value` (en memoria), `accounts.value[idx].balance` (ref reactivo), e IndexedDB (fire-and-forget para persistencia). Esto garantiza que los balances mostrados son siempre correctos, incluso offline, sin necesidad de consultar el backend.

### 5.5 Gestion de Balances de Cuentas

Esta seccion documenta como los balances de cuenta se calculan y mantienen localmente, sin usar los endpoints `/accounts/:id/balance` del backend.

#### 5.5.1 Principio Fundamental

**Los balances mostrados al usuario siempre se derivan de IndexedDB, nunca del backend.** Las funciones `fetchBalance(accountId)` y `fetchAllBalances()` que antes llamaban al endpoint `/accounts/:id/balance` han sido eliminadas del store de cuentas y de toda la interfaz publica. La razon: el backend no conoce las transacciones creadas offline que aun no se han sincronizado, por lo que su respuesta de balance seria incorrecta para la UI.

#### 5.5.2 API de Balances del Store de Cuentas

| Funcion | Proposito | Cuando se usa |
|---------|-----------|---------------|
| `adjustBalance(accountId, delta)` | Ajuste optimista e inmediato: suma `delta` al balance actual. Escribe en `balances.value` (memoria) + `accounts.value[idx].balance` + IndexedDB (fire-and-forget) | Llamada por los stores de transacciones y transferencias en cada create/update/delete |
| `recomputeBalancesFromTransactions()` | Recomputa todos los balances sumando todas las transacciones y transferencias de IndexedDB | Llamada despues de `wallet:sync-complete`, cuando `fullReadSync` ha cargado el historial completo del servidor en IndexedDB |
| `getAccountBalance(accountId)` | Lectura: retorna balance de `balances.value`, con fallback a `account.balance` de IndexedDB | Usada por componentes que necesitan el balance de una cuenta |
| `accountsWithBalances` (computed) | Mapea cada cuenta con su balance preferente: `balances.value` > `account.balance` > `0` | Usada por las vistas de lista de cuentas |

#### 5.5.3 Ciclo de Vida del Balance

```
1. ESCRITURA (transaccion/transferencia creada, editada o eliminada)
   → transactions.ts / transfers.ts llaman adjustBalance(accountId, delta)
   → balances.value (en memoria) se actualiza
   → accounts.value[idx].balance se actualiza
   → db.accounts.update(id, { balance }) — fire-and-forget, para persistencia

2. RECARGA DE PAGINA
   → fetchAccounts() lee de IndexedDB
   → account.balance tiene el valor persistido en paso 1
   → La UI muestra el balance correcto inmediatamente

3. REVALIDACION DE BACKGROUND (fetchAccounts background revalidation)
   → El servidor puede retornar balance: 0 para cuentas con transacciones pendientes
   → El callback onFreshData detecta esto y restaura el balance local
   → Se repara IndexedDB despues del bulkPut del servidor

4. POST-SINCRONIZACION (wallet:sync-complete)
   → fullReadSync ha cargado todas las transacciones del servidor en IndexedDB
   → refreshFromDB() actualiza accounts.value desde IndexedDB
   → recomputeBalancesFromTransactions() recalcula desde el historial completo
   → El resultado es autoritativo (identico al que retornaria el servidor)
```

#### 5.5.4 Archivos que Participan en el Ciclo de Balance

| Archivo | Rol en gestion de balances |
|---------|---------------------------|
| `frontend/src/stores/accounts.ts` | Define `adjustBalance`, `recomputeBalancesFromTransactions`, `getAccountBalance`, `accountsWithBalances`. Protege balances locales en callbacks de revalidacion |
| `frontend/src/stores/transactions.ts` | Llama `adjustBalance` en `createTransaction`, `updateTransaction`, `deleteTransaction` |
| `frontend/src/stores/transfers.ts` | Llama `adjustBalance` en `createTransfer`, `updateTransfer`, `deleteTransfer` (ambas cuentas: origen y destino) |
| `frontend/src/main.ts` | En `wallet:sync-complete`: llama `refreshFromDB()` → luego `recomputeBalancesFromTransactions()` |

#### 5.5.5 Funciones Eliminadas

Las siguientes funciones existian en versiones anteriores y fueron eliminadas como parte de esta decision arquitectonica:

| Funcion eliminada | Que hacia | Por que se elimino |
|-------------------|-----------|-------------------|
| `fetchBalance(accountId)` | Llamaba `GET /accounts/:id/balance` y actualizaba `balances.value` | El backend no conoce transacciones offline; el balance retornado seria incorrecto |
| `fetchAllBalances()` | Iteraba sobre todas las cuentas llamando `fetchBalance` para cada una | Misma razon; ademas generaba N llamadas HTTP innecesarias |

Las vistas que antes llamaban a estas funciones despues de crear/editar/eliminar una transaccion o transferencia (TransactionCreateView, TransactionEditView, TransferCreateView, TransferEditView) ya no necesitan hacerlo. El balance se actualiza de forma optimista e inmediata via `adjustBalance()` en el store correspondiente.

### 5.6 Nuevos Modulos del Frontend

| Modulo | Ruta propuesta | Responsabilidad |
|--------|----------------|-----------------|
| `OfflineDB` | `src/offline/db.ts` | Clase Dexie con esquema de tablas, migraciones, operaciones CRUD locales |
| `MutationQueue` | `src/offline/mutation-queue.ts` | Cola FIFO en IndexedDB para operaciones pendientes de sync |
| `SyncManager` | `src/offline/sync-manager.ts` | Orquestador de sincronizacion: procesa cola, maneja errores, reintentos |
| `useNetworkStatus` | `src/composables/useNetworkStatus.ts` | Composable que expone estado de red reactivo y emite eventos |
| `useSyncStatus` | `src/composables/useSyncStatus.ts` | Composable que expone estado de la cola de sync para la UI |
| `syncStore` | `src/stores/sync.ts` | Store Pinia para estado global de sincronizacion |
| `NetworkBanner` | `src/components/sync/NetworkBanner.vue` | Componente visual de estado offline/online (push-down layout, no overlay) |
| `SyncIndicator` | `src/components/SyncIndicator.vue` | Indicador sutil de operaciones pendientes de sincronizacion |

---

## 6. Cambios en el Frontend

### 6.1 Dependencias Nuevas

```json
{
  "dependencies": {
    "dexie": "^4.x",
    "dexie-cloud-addon": null
  },
  "devDependencies": {
    "vite-plugin-pwa": "^0.20.x"
  }
}
```

**Nota**: `@vueuse/core` ya esta instalado en el proyecto (version ^10.9.0). No se necesita instalar.

### 6.2 Configuracion de Vite (vite.config.js)

Se agrega `vite-plugin-pwa` al array de plugins con configuracion de Workbox para:
- Precachear el app shell (HTML, CSS, JS, fuentes, iconos)
- Runtime caching para peticiones a la API con estrategia NetworkFirst
- Manifest PWA con nombre, iconos, tema y color de fondo

### 6.3 Esquema de IndexedDB (Dexie)

La base de datos local replica las 4 entidades del modelo de datos del MVP:

```typescript
// src/offline/db.ts
import Dexie, { type Table } from 'dexie'

interface LocalAccount {
  id: string              // UUID (puede ser temporal si se creo offline)
  server_id?: string      // UUID del servidor (null si no sincronizado)
  nombre: string
  tipo: 'debito' | 'credito' | 'efectivo'
  divisa: string
  descripcion?: string
  tags: string[]
  activa: boolean
  balance: number         // Balance computado localmente (nunca del backend)
  created_at: string
  updated_at: string
  _sync_status: 'synced' | 'pending' | 'error'
  _local_updated_at: string  // timestamp local para resolucion de conflictos
}

// Mismo patron para LocalTransaction, LocalTransfer, LocalCategory

interface PendingMutation {
  id?: number             // Auto-increment (orden FIFO)
  entity_type: 'account' | 'transaction' | 'transfer' | 'category'
  entity_id: string       // ID local de la entidad
  operation: 'create' | 'update' | 'delete'
  payload: Record<string, any>  // Datos de la operacion
  created_at: string      // Timestamp de cuando se encolo
  retry_count: number     // Numero de reintentos fallidos
  last_error?: string     // Ultimo error de sincronizacion
}

class WalletDB extends Dexie {
  accounts!: Table<LocalAccount>
  transactions!: Table<LocalTransaction>
  transfers!: Table<LocalTransfer>
  categories!: Table<LocalCategory>
  pendingMutations!: Table<PendingMutation>

  constructor() {
    super('WalletDB')
    this.version(1).stores({
      accounts: 'id, server_id, tipo, activa, _sync_status',
      transactions: 'id, server_id, cuenta_id, categoria_id, tipo, fecha, _sync_status',
      transfers: 'id, server_id, cuenta_origen_id, cuenta_destino_id, fecha, _sync_status',
      categories: 'id, server_id, tipo, categoria_padre_id, _sync_status',
      pendingMutations: '++id, entity_type, entity_id, operation, queued_at'
    })
  }
}
```

**Campos adicionales por entidad**:

| Campo | Tipo | Proposito |
|-------|------|-----------|
| `_sync_status` | `'synced' \| 'pending' \| 'error'` | Estado de sincronizacion de la entidad |
| `_local_updated_at` | `string` (ISO timestamp) | Marca temporal local para resolucion de conflictos |
| `server_id` | `string \| undefined` | UUID del servidor; undefined si la entidad se creo offline |
| `balance` (solo cuentas) | `number` | Balance computado localmente; persistido por `adjustBalance()` y `recomputeBalancesFromTransactions()` |

### 6.4 Adaptacion de Stores Existentes

Los stores de Pinia (accounts, transactions, transfers, categories) se adaptan para usar el patron **local-first** sin cambiar su interfaz publica. Los componentes existentes no necesitan cambios.

**Patron de adaptacion para cada store**:

```
ANTES (online-only):
  createTransaction(data) → API.post() → actualizar ref

DESPUES (offline-first):
  createTransaction(data) → generar UUID → escribir OfflineDB
    → actualizar ref → adjustBalance() → encolar mutacion
    → si online: SyncManager.process()
```

**Nota sobre balances**: En la version anterior, las vistas llamaban `fetchBalance()` despues de cada operacion de escritura para actualizar el balance desde el backend. Ahora, `adjustBalance()` se invoca directamente dentro de los stores de transacciones y transferencias (no en las vistas), actualizando el balance de forma optimista e inmediata. Las vistas ya no participan en la gestion de balances.

**Estrategia de migracion**: Se crea una capa intermedia (`src/offline/repository.ts`) que abstrae las operaciones de lectura/escritura. Los stores llaman al repository en lugar de llamar directamente a la API. El repository siempre retorna datos de IndexedDB inmediatamente (incluso si esta vacia) y lanza la revalidacion con la API en segundo plano si hay conexion. No existe un camino bloqueante para ninguna operacion de lectura.

```
┌───────────┐     ┌──────────────┐     ┌──────────┐
│  Store     │────►│  Repository  │────►│ OfflineDB│
│  (Pinia)   │     │  (nuevo)     │────►│ API      │
└───────────┘     └──────────────┘     └──────────┘
```

### 6.5 Cola de Mutaciones

La `MutationQueue` es una tabla en IndexedDB (`pendingMutations`) que funciona como una cola FIFO. Cada operacion de escritura que el usuario realiza se registra como una mutacion pendiente.

**Estructura de una mutacion**:

```typescript
{
  id: 1,                           // Auto-increment interno de Dexie
  entity_type: 'transaction',      // Tipo de entidad
  entity_id: 'temp-uuid-abc123',   // ID local
  operation: 'create',             // create | update | delete
  payload: {                       // Datos completos de la operacion
    tipo: 'gasto',
    monto: 150.00,
    fecha: '2026-02-23',
    cuenta_id: 'uuid-cuenta-1',
    categoria_id: 'uuid-cat-1',
    titulo: 'Supermercado'
  },
  queued_at: '2026-02-23T14:30:00.000Z',  // Timestamp de encolamiento, garantiza orden FIFO
  retry_count: 0,
  last_error: null
}
```

### 6.6 SyncManager

El `SyncManager` es el orquestador central de la sincronizacion. Sus responsabilidades:

1. **Detectar conexion**: Escucha eventos `online` del navegador y `useOnline()` de @vueuse/core
2. **Procesar cola**: Al detectar conexion, procesa mutaciones en orden FIFO estricto
3. **Manejar errores**: Reintenta mutaciones fallidas con backoff exponencial (max 5 reintentos)
4. **Resolver IDs temporales**: Reemplaza UUIDs temporales con IDs reales del servidor en entidades relacionadas
5. **Background Sync**: Registra un evento de Background Sync en el Service Worker para sincronizar incluso si la app no esta en primer plano
6. **Full sync periodico**: Cuando hay conexion, ejecuta una sincronizacion completa de lectura cada N minutos para mantener datos frescos
7. **Emitir `wallet:sync-complete`**: Despues de completar el ciclo de sync (cola vaciada + fullReadSync), emite un evento de ventana que dispara la recomputacion de balances desde IndexedDB

### 6.7 PWA y Service Worker

**Configuracion de vite-plugin-pwa**:

| Aspecto | Estrategia | Detalle |
|---------|-----------|---------|
| App shell | Precache | HTML, CSS, JS, fuentes: cacheados en build time |
| Imagenes / iconos | Precache | Incluidos en el bundle de Vite |
| Peticiones API (GET) | NetworkFirst | Intenta red primero; si falla, sirve de cache |
| Peticiones API (POST/PUT/DELETE) | No cacheadas por SW | Manejadas por la MutationQueue del frontend |
| Actualizacion de SW | Prompt al usuario | Notificar cuando hay una nueva version disponible |

**Manifest PWA** (`manifest.json`):

```json
{
  "name": "Wallet - Finanzas Personales",
  "short_name": "Wallet",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1a1a2e",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

### 6.8 Componentes UI Nuevos

**NetworkBanner** (`src/components/sync/NetworkBanner.vue`): Banner no intrusivo que aparece cuando se pierde la conexion.

- Texto: "Sin conexion - Los cambios se guardan y sincronizaran al reconectar"
- Color: Ambar (amber, `rgba(217, 119, 6, 0.95)`) sobre fondo oscuro — indica estado informativo, no error
- **Layout push-down** (no overlay): El banner es parte del flujo flex normal del layout. Cuando aparece, empuja el header y todo el contenido hacia abajo usando una animacion de `max-height` (0 a 3rem). Cuando desaparece, el contenido retracta suavemente hacia arriba. Esto reemplaza la estrategia anterior de `fixed top-0 z-50` que superponia el banner sobre el header
- Desaparece automaticamente al recuperar conexion con un breve toast de confirmacion
- Accesibilidad: `role="alert"` + `aria-live="polite"` para screen readers

**Justificacion del cambio de overlay a push-down**: La estrategia de overlay (`fixed top-0 z-50`) causaba que el banner cubriera los primeros pixeles del header, ocultando elementos interactivos (como el boton de retroceso) durante el estado offline. El push-down evita esta ocultacion al reservar espacio real en el layout para el banner.

**SyncIndicator**: Indicador en el header o barra de navegacion.

- Icono de nube con estados: sincronizado (check), sincronizando (animacion), pendiente (reloj), error (exclamacion)
- Tap/click muestra detalle: numero de operaciones pendientes
- No bloquea la interaccion del usuario en ningun caso

---

## 7. Flujos Clave

### 7.1 Usuario Offline Registra un Gasto

```
1. Usuario abre la app (cargada desde Service Worker cache)
2. App detecta que no hay conexion → muestra NetworkBanner (empuja el UI hacia abajo)
3. Usuario navega a "Nueva Transaccion" (datos de cuentas y categorias vienen de IndexedDB)
4. Usuario completa el formulario y presiona "Guardar"
5. Store genera UUID temporal (ej: "temp-txn-a1b2c3")
6. Store escribe la transaccion en OfflineDB con _sync_status = 'pending'
7. Store llama adjustBalance(cuenta_id, -monto) → balance en memoria + IndexedDB actualizado
8. Store encola la mutacion en pendingMutations
9. UI muestra la transaccion en la lista con un indicador sutil de "pendiente"
10. El balance de la cuenta ya refleja la nueva transaccion (actualizado en paso 7)
11. SyncIndicator muestra "1 cambio pendiente"
```

**Nota**: La vista no llama a ningun endpoint de balance. El paso 7 ocurre dentro de `createTransaction()` en el store de transacciones.

### 7.2 Conexion Recuperada - Sincronizacion Automatica

```
1. Navegador emite evento 'online'
2. useNetworkStatus detecta el cambio → oculta NetworkBanner (retraccion suave)
3. SyncManager se activa y lee la cola de pendingMutations (ordenada por queued_at ASC)
4. Para cada mutacion en orden:
   a. Envia peticion HTTP correspondiente (POST/PUT/DELETE)
   b. Si exito:
      - Actualiza OfflineDB con datos del servidor (ID real, timestamps)
      - Reemplaza UUID temporal en entidades relacionadas si aplica
      - Marca _sync_status = 'synced'
      - Elimina la mutacion de la cola
   c. Si error transitorio (timeout, 5xx):
      - Incrementa retry_count
      - Si retry_count < 5: reintenta con backoff exponencial
      - Si retry_count >= 5: marca _sync_status = 'error'
        → Si la mutacion fallida era de tipo 'create':
          - Escanear cola restante buscando mutaciones cuyo payload referencie el entity_id fallido
          - Marcar esas mutaciones con last_error = 'blocked: dependency on <entity_id> failed'
          - Marcar sus entidades locales con _sync_status = 'error'
          - Saltarlas sin procesar
        → Continua con la siguiente mutacion no bloqueada
   d. Si error permanente (4xx):
      - Marca _sync_status = 'error'
      - Registra last_error con detalle del error
      - Si la mutacion fallida era de tipo 'create':
        - Escanear cola restante buscando mutaciones cuyo payload referencie el entity_id fallido
        - Marcar esas mutaciones con last_error = 'blocked: dependency on <entity_id> failed'
        - Marcar sus entidades locales con _sync_status = 'error'
        - Saltarlas sin procesar
      - Continua con la siguiente mutacion no bloqueada
5. SyncIndicator se actualiza en tiempo real
6. Al terminar: SyncManager ejecuta un full-read-sync para refrescar datos del servidor
7. SyncManager emite evento wallet:sync-complete
8. main.ts escucha wallet:sync-complete:
   a. Llama refreshFromDB() en todos los stores (accounts, transactions, transfers, categories)
   b. Despues de que todos completan, llama recomputeBalancesFromTransactions()
   c. Los balances se recomputan desde el historial completo ahora en IndexedDB (autoritativo)
9. Toast breve: "Datos sincronizados"
```

**Nota sobre el paso 8**: El `wallet:sync-complete` handler en `main.ts` usa `Promise.allSettled()` para los `refreshFromDB()` y luego `.then()` para `recomputeBalancesFromTransactions()`. Nunca se llama a un endpoint de balance del backend.

### 7.3 Usuario Edita un Registro Pendiente de Sync

```
1. Usuario creo una transaccion offline (estado: pending)
2. Antes de recuperar conexion, usuario decide editar esa transaccion
3. Store actualiza la entidad en OfflineDB
4. Store computa el delta de balance (balance viejo - balance nuevo) y llama adjustBalance()
5. Store busca la mutacion pendiente de CREATE para esa entidad:
   - Si existe: actualiza el payload de la mutacion CREATE (merge)
   - Esto evita enviar un CREATE seguido de un UPDATE innecesario
6. Si la entidad ya estaba sincronizada (synced) y se edita offline:
   - Se crea una nueva mutacion de tipo UPDATE en la cola
```

### 7.4 Usuario Elimina un Registro Pendiente de Sync

```
1. Usuario creo una transaccion offline (estado: pending, aun no sincronizada)
2. Usuario decide eliminarla antes de sincronizar
3. Store elimina la entidad de OfflineDB
4. Store llama adjustBalance() para revertir el efecto de la transaccion eliminada
5. Store elimina la mutacion CREATE pendiente de la cola
   - No necesita enviar ni CREATE ni DELETE al servidor (se cancelan)
6. Si la entidad ya estaba sincronizada y se elimina offline:
   - Se crea una mutacion DELETE en la cola
   - Se marca la entidad como eliminada en OfflineDB (soft delete local)
   - Se llama adjustBalance() para revertir el efecto
```

### 7.5 Primera Carga / Hydration Inicial

```
1. Usuario accede a la app por primera vez (con o sin conexion)
2. Service Worker se instala y cachea el app shell
3. Store lee de IndexedDB → retorna array vacio inmediatamente (no hay datos locales aun)
4. UI renderiza estado vacio con skeleton/spinner (no bloquea esperando la API)
5. Si hay conexion: fetch a la API en segundo plano → datos llegan → se guardan en OfflineDB → callback actualiza el store → UI re-renderiza con datos reales
6. Si NO hay conexion: la UI muestra estado vacio hasta que se recupere la conexion y la revalidacion complete
7. En cargas subsecuentes (IndexedDB tiene datos):
   a. Store lee de OfflineDB (instantaneo, datos visibles de inmediato)
   b. Balances se leen de account.balance en IndexedDB (persistido por adjustBalance en la sesion anterior)
   c. Si hay conexion: fetch de API en background → actualiza OfflineDB → re-renderiza si cambio
   d. La revalidacion de background preserva los balances locales (ver seccion 5.3)
```

**Nota sobre cold-start**: No existe un camino bloqueante para la primera carga. El principio "IndexedDB es siempre la fuente de verdad para el render inicial" aplica incluso cuando IndexedDB esta vacia. La UI debe estar preparada para renderizar listas vacias y transicionar suavemente cuando los datos lleguen del background.

---

## 8. Consideraciones Tecnicas

### 8.1 Resolucion de Conflictos

**Estrategia: Last-Write-Wins (LWW) basada en timestamp**

Dado que Wallet es una aplicacion de un solo usuario, los conflictos son infrecuentes y limitados a escenarios de edicion simultanea en multiples pestanas. La estrategia LWW es suficiente y simple:

```
Al sincronizar un UPDATE:
  1. Enviar updated_at local junto con los datos
  2. Servidor compara updated_at recibido con updated_at almacenado
  3. Si local >= servidor: aplicar cambio (el cliente gana)
  4. Si local < servidor: descartar cambio, retornar version del servidor
  5. Cliente actualiza su OfflineDB con la version que prevalecio
```

**Escenarios de conflicto y resolucion**:

| Escenario | Resolucion |
|-----------|------------|
| Mismo registro editado en dos pestanas | La ultima escritura gana (LWW) |
| Registro eliminado en servidor, editado offline | El DELETE prevalece; se notifica al usuario |
| Registro creado offline con FK a registro eliminado | Se marca como error; usuario debe corregir |

### 8.2 Generacion de IDs Temporales

Los IDs temporales para entidades creadas offline se generan con el prefijo `temp-` seguido de un UUID v4:

```typescript
function generateTempId(): string {
  return `temp-${crypto.randomUUID()}`
}
```

Esto permite distinguir facilmente entre entidades sincronizadas y pendientes. Al sincronizar, el `server_id` se asigna con la respuesta del servidor y se actualiza en todas las entidades que referencien el ID temporal.

### 8.3 Resolucion de IDs Temporales en Relaciones

Cuando una entidad creada offline referencia a otra entidad tambien creada offline, los IDs temporales deben resolverse en cadena:

```
Ejemplo:
  1. Usuario crea Cuenta offline → id: temp-cuenta-1
  2. Usuario crea Transaccion offline → cuenta_id: temp-cuenta-1
  3. Al sincronizar:
     a. SyncManager procesa CREATE Cuenta → servidor retorna id: uuid-real-abc
     b. SyncManager reemplaza temp-cuenta-1 → uuid-real-abc en:
        - La entidad Cuenta en OfflineDB
        - El campo cuenta_id de la Transaccion pendiente en OfflineDB
        - El payload de la mutacion pendiente de la Transaccion en la cola
     c. SyncManager procesa CREATE Transaccion con cuenta_id: uuid-real-abc
```

**Orden de sincronizacion**: Las mutaciones se procesan en orden FIFO (por `queued_at` ASC). Esto garantiza que las entidades padre (cuentas, categorias) se crean antes que sus dependientes (transacciones, transferencias), ya que el flujo de UI impide crear una transaccion sin una cuenta existente.

### 8.4 Manejo de Errores de Sincronizacion

| Tipo de Error | Accion | Reintentos |
|---------------|--------|------------|
| Sin conexion (network error) | Pausar sync, esperar evento online | Infinitos (espera conexion) |
| Timeout | Reintentar con backoff exponencial | Max 5 |
| Error 5xx (servidor) | Reintentar con backoff exponencial | Max 5 |
| Error 409 (conflicto) | Aplicar resolucion LWW | 1 (resolver y continuar) |
| Error 404 (entidad no existe) | Marcar como error, notificar usuario | 0 |
| Error 400 (validacion) | Marcar como error, notificar usuario | 0 |
| Error 422 (datos invalidos) | Marcar como error, notificar usuario | 0 |
| Error de dependencia (create padre fallo) | Marcar como blocked sin procesar; se desbloquea si el usuario resuelve el error raiz | 0 |

**Backoff exponencial**:

```
Delay = min(1000 * 2^retry_count, 30000)  // Max 30 segundos
  Retry 1: 2s
  Retry 2: 4s
  Retry 3: 8s
  Retry 4: 16s
  Retry 5: 30s → marcar como error
```

### 8.5 Estrategia de Cache del Service Worker

| Recurso | Estrategia Workbox | TTL | Detalle |
|---------|--------------------|-----|---------|
| App shell (HTML, CSS, JS) | Precache (build time) | Hasta nueva version | Se invalida al actualizar el SW |
| Fuentes, iconos estaticos | CacheFirst | 30 dias | Rara vez cambian |
| Peticiones GET `/api/v1/*` | NetworkFirst | Fallback a cache | Si la red falla, sirve ultimo dato cacheado |
| Peticiones POST/PUT/DELETE | No cacheadas por SW | N/A | Manejadas por MutationQueue |

### 8.6 Limites de Almacenamiento

IndexedDB tiene limites de almacenamiento que varian por navegador:

| Navegador | Limite aproximado |
|-----------|-------------------|
| Chrome / Edge | Hasta 80% del disco disponible |
| Firefox | Hasta 50% del disco (max ~2GB por origen) |
| Safari / iOS | ~1GB por origen |

Para una app de finanzas personales con datos de texto, estos limites son mas que suficientes. Un usuario con 10,000 transacciones ocuparia aproximadamente 5-10 MB.

### 8.7 Compatibilidad con el Backend Actual

El backend Flask REST API **no requiere cambios significativos**. Los ajustes menores:

| Cambio | Detalle | Impacto |
|--------|---------|---------|
| Header `If-Modified-Since` | Soportar en endpoints GET para sync incremental (opcional, fase futura) | Bajo |
| Campo `updated_at` en respuestas | Ya existe en todas las entidades | Ninguno |
| Idempotencia en POST | Aceptar `client_id` opcional para evitar duplicados en reintentos | Bajo |

**Nota sobre el endpoint `/accounts/:id/balance`**: Este endpoint sigue existiendo en el backend y es correcto a nivel de servidor. Sin embargo, el frontend NO lo consume para mostrar balances al usuario. El frontend computa balances localmente desde IndexedDB. El endpoint puede seguir siendo util para herramientas externas o APIs de terceros, pero no es parte del flujo de datos de la UI.

### 8.8 Migracion y Compatibilidad

La implementacion offline-first se agrega de forma aditiva:

- Los componentes Vue existentes no cambian su interfaz con los stores
- Los stores mantienen sus mismas funciones publicas; solo cambia la implementacion interna
- La capa de API (`src/api/*`) se conserva y es usada por el SyncManager para las peticiones al servidor
- Si IndexedDB no esta disponible (navegador muy antiguo), la app funciona como antes (online-only)

**Cambios en la interfaz publica de los stores**:
- `accounts` store: se eliminaron `fetchBalance()` y `fetchAllBalances()`. Se agregaron `adjustBalance()`, `recomputeBalancesFromTransactions()`, `getAccountBalance()`, y `refreshFromDB()`
- `transactions` store: `createTransaction`, `updateTransaction`, `deleteTransaction` ahora llaman `adjustBalance()` internamente
- `transfers` store: `createTransfer`, `updateTransfer`, `deleteTransfer` ahora llaman `adjustBalance()` internamente
- Las vistas de crear/editar transacciones y transferencias ya no contienen logica de actualizacion de balance

---

## 9. Fases de Implementacion

### Fase 1: PWA Base y Carga Offline

**Objetivo**: La app se puede instalar y cargar sin conexion (shell vacio, sin datos).

| # | Tarea | Criterio de Aceptacion |
|---|-------|------------------------|
| 1.1 | Instalar y configurar `vite-plugin-pwa` | Service Worker se registra correctamente en produccion |
| 1.2 | Configurar precache de app shell | La app carga el shell (HTML/CSS/JS) sin conexion |
| 1.3 | Crear `manifest.json` con iconos | La app es instalable en Chrome/Safari con icono correcto |
| 1.4 | Prompt de actualizacion del SW | Al desplegar nueva version, el usuario recibe notificacion para actualizar |

### Fase 2: IndexedDB y Lectura Offline

**Objetivo**: Los datos se almacenan localmente y se pueden consultar sin conexion.

| # | Tarea | Criterio de Aceptacion |
|---|-------|------------------------|
| 2.1 | Instalar Dexie.js y definir esquema `WalletDB` | Base de datos se crea con tablas para las 4 entidades + pendingMutations |
| 2.2 | Crear capa `Repository` | CRUD generico contra OfflineDB con tipado TypeScript |
| 2.3 | Adaptar stores para leer de OfflineDB | Stores cargan datos de IndexedDB primero, luego sincronizan con API en background |
| 2.4 | Hydration inicial | Al primer uso con conexion, todos los datos se descargan y guardan en OfflineDB |
| 2.5 | Verificar lectura offline | Con red deshabilitada, la app muestra cuentas, transacciones, transferencias y categorias cargadas previamente |

### Fase 3: Escritura Offline y Cola de Mutaciones

**Objetivo**: El usuario puede crear, editar y eliminar datos sin conexion.

| # | Tarea | Criterio de Aceptacion |
|---|-------|------------------------|
| 3.1 | Implementar `MutationQueue` | Las operaciones de escritura se encolan en IndexedDB como mutaciones pendientes |
| 3.2 | Adaptar stores para escritura offline | CREATE/UPDATE/DELETE se ejecutan contra OfflineDB primero y se encolan |
| 3.3 | Generacion de IDs temporales | Entidades creadas offline reciben UUID temporal con prefijo `temp-` |
| 3.4 | Optimizacion de cola (merge create+update, cancelar create+delete) | Editar una entidad pending fusiona la mutacion; eliminar una pending cancela ambas |
| 3.5 | Implementar `adjustBalance()` | Los balances se actualizan optimistamente en cada escritura sin consultar el backend |
| 3.6 | Eliminar `fetchBalance()` / `fetchAllBalances()` de la interfaz publica | Ninguna vista ni store llama al endpoint `/accounts/:id/balance` para display |
| 3.7 | Verificar escritura offline | Con red deshabilitada, el usuario puede crear una cuenta y una transaccion; ambas aparecen en la UI con balances correctos |

### Fase 4: Sincronizacion Automatica

**Objetivo**: Al recuperar conexion, los datos se sincronizan automaticamente.

| # | Tarea | Criterio de Aceptacion |
|---|-------|------------------------|
| 4.1 | Implementar `SyncManager` | Procesa la cola FIFO al detectar conexion; envia peticiones HTTP en orden |
| 4.2 | Resolucion de IDs temporales | Al sincronizar un CREATE, el ID temporal se reemplaza por el ID real en todas las entidades relacionadas |
| 4.3 | Manejo de errores con backoff exponencial | Errores transitorios se reintentan hasta 5 veces; errores permanentes se marcan como error |
| 4.4 | Resolucion de conflictos LWW | Al sincronizar un UPDATE, se compara `updated_at`; la version mas reciente prevalece |
| 4.5 | Background Sync registration | Si el navegador soporta Background Sync, la sincronizacion puede ocurrir en segundo plano |
| 4.6 | Implementar `wallet:sync-complete` con `recomputeBalancesFromTransactions()` | Despues de fullReadSync, los balances se recomputan desde el historial completo en IndexedDB (nunca desde el backend) |
| 4.7 | Proteger revalidacion de background | `onFreshData` en `fetchAccounts()` y `fetchAccountById()` preserva balances locales cuando el servidor retorna valores stale |
| 4.8 | Verificar ciclo completo | Crear datos offline → desconectar → verificar datos y balances locales → reconectar → verificar datos en servidor → verificar balances post-sync |

### Fase 5: UI de Estado y Polish

**Objetivo**: El usuario tiene visibilidad clara del estado de conexion y sincronizacion.

| # | Tarea | Criterio de Aceptacion |
|---|-------|------------------------|
| 5.1 | Crear `syncStore` (Pinia) | Estado reactivo de la sincronizacion accesible desde cualquier componente |
| 5.2 | Implementar `NetworkBanner` | Banner push-down visible cuando no hay conexion; empuja el UI hacia abajo; desaparece al reconectar con animacion suave |
| 5.3 | Implementar `SyncIndicator` | Icono en header que muestra estado de sync (pendiente/sincronizando/error/ok) |
| 5.4 | Indicador por entidad | Transacciones/cuentas pendientes de sync muestran un badge sutil en listas |
| 5.5 | Manejo de errores de sync en UI | Entidades con error de sync muestran opcion de reintentar o descartar |
| 5.6 | Toast de confirmacion de sync | Al completar sincronizacion, toast breve: "Datos sincronizados" |

---

## 10. Definicion de Done (Global)

La feature de offline-first se considera completa cuando:

- [ ] La app es instalable como PWA en Chrome, Safari (iOS) y Firefox
- [ ] La app carga completamente sin conexion a internet (app shell + datos locales)
- [ ] El usuario puede crear, editar y eliminar cuentas, transacciones, transferencias y categorias sin conexion
- [ ] Al recuperar conexion, todos los cambios se sincronizan automaticamente sin intervencion del usuario
- [ ] Los balances se calculan correctamente a partir de datos locales en IndexedDB (transacciones + transferencias), sin consultar el backend
- [ ] Los balances se actualizan inmediatamente despues de cada escritura via `adjustBalance()` y se recomputan autoritativamente despues de cada sync via `recomputeBalancesFromTransactions()`
- [ ] Los balances locales sobreviven recargas de pagina (persistidos en IndexedDB por `adjustBalance`)
- [ ] La revalidacion de background del servidor no sobreescribe balances locales correctos con valores stale del servidor
- [ ] El estado de conexion y sincronizacion es visible pero no intrusivo (NetworkBanner con push-down layout)
- [ ] Las entidades con errores de sincronizacion son identificables y permiten accion del usuario
- [ ] No hay perdida de datos en ningun escenario de perdida/recuperacion de conexion
- [ ] Los datos se mantienen consistentes entre IndexedDB y PostgreSQL despues de la sincronizacion
- [ ] La experiencia de usuario en modo online no se degrada (no hay latencia adicional perceptible)
- [ ] Ningun componente de vista llama directamente a endpoints de balance del backend

---

## 11. Glosario

| Termino | Definicion |
|---------|------------|
| Offline-first | Arquitectura donde la app funciona sin conexion como caso base, no como caso excepcional |
| PWA | Progressive Web App: aplicacion web que puede instalarse y funcionar como app nativa |
| Service Worker | Script que se ejecuta en segundo plano en el navegador; intercepta peticiones de red y gestiona cache |
| IndexedDB | Base de datos NoSQL nativa del navegador, asincrona y de alto rendimiento. En esta arquitectura, es la unica fuente de verdad para todos los datos mostrados al usuario |
| Dexie.js | Wrapper minimalista sobre IndexedDB que simplifica su API y agrega tipado TypeScript |
| MutationQueue | Cola FIFO de operaciones de escritura pendientes de sincronizacion |
| SyncManager | Modulo que orquesta la sincronizacion entre IndexedDB y el servidor |
| Stale-while-revalidate | Patron donde se sirven datos locales (IndexedDB) inmediatamente — incluso si estan vacios — y se revalidan con la API en segundo plano sin bloquear la UI |
| LWW (Last-Write-Wins) | Estrategia de resolucion de conflictos donde la escritura mas reciente prevalece |
| Hydration | Proceso de poblar la base de datos local con datos del servidor. Ocurre en segundo plano (no bloquea la UI) la primera vez que se accede a la app con conexion |
| Optimistic UI | Patron donde la UI refleja el resultado esperado de una operacion antes de la confirmacion del servidor |
| Background Sync | API del navegador que permite sincronizar datos en segundo plano, incluso si la app no esta en primer plano |
| Backoff exponencial | Estrategia de reintento donde el tiempo entre intentos crece exponencialmente |
| App shell | Estructura minima de HTML, CSS y JS necesaria para renderizar la interfaz de la aplicacion |
| adjustBalance | Funcion del store de cuentas que actualiza el balance de una cuenta de forma optimista e inmediata (en memoria + IndexedDB) sin consultar el backend |
| recomputeBalancesFromTransactions | Funcion que recalcula todos los balances sumando transacciones y transferencias desde IndexedDB. Ejecutada despues de cada sync completo para producir un balance autoritativo |
| wallet:sync-complete | Evento de ventana emitido por el SyncManager despues de completar un ciclo de sincronizacion (cola vaciada + fullReadSync). Dispara refreshFromDB() y recomputeBalancesFromTransactions() |

---

## 12. Registro de Decisiones Arquitectonicas

### ADR-001: IndexedDB como unica fuente de verdad para datos mostrados (2026-02-24)

**Estado**: Aceptada e implementada

**Contexto**: La arquitectura inicial de offline-first (v1.0) seguia el principio de que IndexedDB es la fuente de verdad para el render inicial, pero mantenia el backend como fuente autoritativa para balances. Las vistas llamaban `fetchBalance()` despues de cada operacion de escritura para obtener el balance actualizado del servidor.

**Problema**: En una arquitectura offline-first, el backend no conoce las transacciones creadas localmente que aun no se han sincronizado. El endpoint `/accounts/:id/balance` retorna un balance que excluye esas transacciones, produciendo valores incorrectos en la UI. Ademas, en modo offline, el endpoint no es accesible en absoluto, dejando los balances desactualizados.

**Decision**: Evolucionar de "el backend es la fuente autoritativa para balances" a "IndexedDB es la unica fuente de verdad para TODOS los datos mostrados, incluyendo balances". Eliminar `fetchBalance()` y `fetchAllBalances()` de la interfaz publica. Computar balances localmente via `adjustBalance()` (optimista, en cada escritura) y `recomputeBalancesFromTransactions()` (autoritativo, post-sync).

**Consecuencias**:
- (+) Los balances son siempre correctos, incluso offline
- (+) Cero llamadas HTTP para mostrar balances — rendimiento mejorado
- (+) Las vistas se simplifican al no tener logica de balance
- (+) El ciclo de balance es predecible: escribir → adjust → sync → recompute
- (-) El frontend asume la responsabilidad de la correctitud del calculo de balance
- (-) Si la logica de calculo de balance cambia en el backend, debe cambiar tambien en el frontend
- (-) Los callbacks `onFreshData` requieren logica adicional para proteger balances locales de la sobreescritura del servidor

**Archivos afectados**:
- `frontend/src/stores/accounts.ts` — eliminadas fetchBalance/fetchAllBalances, agregadas adjustBalance/recomputeBalancesFromTransactions, proteccion en onFreshData
- `frontend/src/stores/transactions.ts` — adjustBalance en create/update/delete
- `frontend/src/stores/transfers.ts` — adjustBalance en create/update/delete
- `frontend/src/main.ts` — wallet:sync-complete usa recomputeBalancesFromTransactions
- `frontend/src/views/transactions/TransactionCreateView.vue` — eliminada llamada a fetchBalance
- `frontend/src/views/transactions/TransactionEditView.vue` — eliminadas llamadas a fetchBalance
- `frontend/src/views/transfers/TransferCreateView.vue` — eliminadas llamadas a fetchBalance
- `frontend/src/views/transfers/TransferEditView.vue` — eliminadas llamadas a fetchBalance

### ADR-002: NetworkBanner como elemento de flujo (push-down) en lugar de overlay (2026-02-24)

**Estado**: Aceptada e implementada

**Contexto**: La implementacion inicial del NetworkBanner usaba `fixed top-0 z-50` para superponer el banner sobre la parte superior de la pantalla sin afectar el layout.

**Problema**: El overlay cubria el header y sus controles interactivos (boton de retroceso, titulo), reduciendo la usabilidad durante el estado offline — precisamente cuando el usuario mas necesita navegar la app.

**Decision**: Cambiar el NetworkBanner de `fixed top-0 z-50` a un elemento normal dentro del flujo flex del layout. Usar una animacion de `max-height` (0 a 3rem) para crear un efecto de push-down suave que empuja el header y todo el contenido hacia abajo.

**Consecuencias**:
- (+) El header permanece completamente visible y funcional durante el estado offline
- (+) La animacion de push-down es menos desorientadora que un overlay que aparece sobre contenido existente
- (-) El cambio de layout (contenido moviéndose hacia abajo) es un layout shift, aunque mitigado por la animacion suave

**Archivo afectado**: `frontend/src/components/sync/NetworkBanner.vue`

---

*Documento generado: Febrero 2026*
*Version: 2.0 - Offline-First con IndexedDB como unica fuente de verdad para datos mostrados*
*Actualizado: 2026-02-24 - ADR-001 (balances locales), ADR-002 (NetworkBanner push-down)*
