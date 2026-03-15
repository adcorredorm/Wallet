# Multiusuario — Frontend Implementation Plan (nico-front)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar autenticación Google OAuth en el frontend de Wallet: AuthDB, useAuthStore, vista /login, interceptores Axios, banner de invitado, lógica de logout en Settings, interceptor 401 en SyncManager, y lógica post-login con onboarding.

**Architecture:** AuthDB (Dexie separada de WalletDB) persiste refresh_token y last_user_id en IndexedDB. El accessToken vive SOLO en memoria dentro de useAuthStore. Todos los clientes Axios inyectan el token via interceptor de request. WalletDB (v6) no recibe ningún cambio de schema.

**Tech Stack:** Vue 3 Composition API (`<script setup>`), Pinia, Dexie 4, Axios, Google Identity Services SDK (`google.accounts.id`), Tailwind CSS, TypeScript.

---

## Mapa de archivos

### Archivos a CREAR

| Archivo | Responsabilidad |
|---------|----------------|
| `frontend/src/offline/auth-db.ts` | AuthDB — Dexie separada con tabla `{ key, value }` para `refresh_token` y `last_user_id` |
| `frontend/src/stores/auth.ts` | useAuthStore — estado de sesión, acciones loginWithGoogle / refresh / logout |
| `frontend/src/api/auth.ts` | Funciones de API puras para /auth/google, /auth/refresh, /auth/logout, /api/v1/onboarding/seed |
| `frontend/src/views/LoginView.vue` | Vista /login — botón único "Continuar con Google" |
| `frontend/src/components/sync/GuestBanner.vue` | Banner de modo invitado (visible cuando !isAuthenticated) |

### Archivos a MODIFICAR

| Archivo | Qué cambia |
|---------|-----------|
| `frontend/src/api/index.ts` | Agregar interceptor de request que inyecta `Authorization: Bearer <accessToken>` desde authStore |
| `frontend/src/api/sync-client.ts` | Agregar interceptor de request que inyecta `Authorization: Bearer <accessToken>` desde authStore |
| `frontend/src/offline/sync-manager.ts` | Agregar interceptor 401: refresh → retry / banner invitado si falla; exponer `reset()` para cambio de usuario |
| `frontend/src/stores/sync.ts` | Agregar estado `guest` a `syncStatus` y setter `setGuest()` |
| `frontend/src/views/settings/SettingsView.vue` | Agregar saludo "Hola, [nombre]" al inicio y botón "Cerrar sesión" con prompt al final |
| `frontend/src/components/layout/AppLayout.vue` | Agregar `<GuestBanner />` junto a `<NetworkBanner />` |
| `frontend/src/router/index.ts` | Agregar ruta `/login` (pública, sin layout completo) |
| `frontend/index.html` | Agregar script de Google Identity Services SDK |
| `frontend/src/main.ts` | Inicializar authStore al boot: intentar refresh silencioso |

---

## Chunk 1: Fundación — AuthDB, useAuthStore y API de auth

### Task 1: Crear `src/offline/auth-db.ts`

**Files:**
- Create: `frontend/src/offline/auth-db.ts`

**Contexto:** AuthDB es una instancia de Dexie completamente separada de WalletDB. Almacena exactamente dos claves: `refresh_token` y `last_user_id`. Al ser una DB separada, no puede entrar accidentalmente al pipeline de sync de WalletDB. Usamos el patrón singleton igual que WalletDB lo hace con `export const db`.

- [ ] **Step 1: Crear el archivo `frontend/src/offline/auth-db.ts`**

```typescript
/**
 * AuthDB — Dexie separada para datos de sesión/autenticación.
 *
 * Por qué una DB separada de WalletDB?
 * WalletDB tiene un pipeline de sync (MutationQueue → SyncManager) que
 * procesa todas las tablas registradas. Si auth data viviera en WalletDB,
 * podría filtrarse accidentalmente hacia el backend de sync. AuthDB es
 * completamente aislada: no tiene pendingMutations, no participa en sync.
 *
 * Claves almacenadas:
 * - 'refresh_token' — token opaco de 90d para renovar el JWT
 * - 'last_user_id'  — UUID del último usuario autenticado; detecta cambio de usuario
 *
 * Por qué key/value genérico en lugar de campos tipados?
 * Máxima flexibilidad con mínima complejidad de schema. Solo hay dos claves
 * y ambas son strings. Una tabla key/value de propósito general es más simple
 * y fácil de razonar que una tabla con columnas específicas.
 */

import Dexie, { type Table } from 'dexie'

export interface AuthEntry {
  key: string   // 'refresh_token' | 'last_user_id'
  value: string
}

class AuthDB extends Dexie {
  auth!: Table<AuthEntry>

  constructor() {
    super('AuthDB')
    this.version(1).stores({
      auth: 'key' // PK es la clave string
    })
  }
}

/**
 * Singleton AuthDB.
 *
 * Por qué singleton?
 * Misma razón que WalletDB: abrir conexiones IndexedDB es costoso.
 * Un objeto compartido garantiza que todas las operaciones de auth
 * usen el mismo scope de transacción.
 */
export const authDb = new AuthDB()

// ---------------------------------------------------------------------------
// Helpers tipados para las dos claves conocidas.
//
// Por qué helpers en lugar de acceso directo a authDb.auth?
// Los helpers encapsulan la lógica de get/set/delete y garantizan que
// los callers (useAuthStore) no necesitan conocer los nombres de las claves
// internamente. Si en el futuro se agrega una tercera clave, solo se modifica
// aquí.
// ---------------------------------------------------------------------------

export async function getRefreshToken(): Promise<string | undefined> {
  const entry = await authDb.auth.get('refresh_token')
  return entry?.value
}

export async function setRefreshToken(token: string): Promise<void> {
  await authDb.auth.put({ key: 'refresh_token', value: token })
}

export async function deleteRefreshToken(): Promise<void> {
  await authDb.auth.delete('refresh_token')
}

export async function getLastUserId(): Promise<string | undefined> {
  const entry = await authDb.auth.get('last_user_id')
  return entry?.value
}

export async function setLastUserId(userId: string): Promise<void> {
  await authDb.auth.put({ key: 'last_user_id', value: userId })
}

export async function deleteLastUserId(): Promise<void> {
  await authDb.auth.delete('last_user_id')
}

/**
 * Limpiar completamente AuthDB — llamado en logout.
 * Elimina refresh_token y last_user_id.
 */
export async function clearAuthDb(): Promise<void> {
  await authDb.auth.clear()
}
```

- [ ] **Step 2: Verificar que TypeScript no reporta errores**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

Expected: sin errores relacionados con `auth-db.ts`.

- [ ] **Step 3: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/offline/auth-db.ts && git commit -m "feat(auth): add AuthDB — separate Dexie instance for session data"
```

---

### Task 2: Crear `src/api/auth.ts`

**Files:**
- Create: `frontend/src/api/auth.ts`

**Contexto:** Funciones de API puras para los endpoints de auth. Usan `axios` directamente (no `apiClient`) porque los endpoints `/auth/*` son públicos — no necesitan el interceptor de Authorization que se agregará a `apiClient` en la Task 5. El endpoint `/api/v1/onboarding/seed` sí usa `apiClient` porque requiere autenticación.

- [ ] **Step 1: Crear el archivo `frontend/src/api/auth.ts`**

```typescript
/**
 * Auth API — funciones puras para los endpoints de autenticación.
 *
 * Por qué un cliente Axios separado para los endpoints públicos?
 * Los endpoints /auth/* son públicos y no deben llevar el header
 * Authorization. Si usáramos apiClient (que tendrá un interceptor de
 * request para inyectar el token), podríamos crear un ciclo:
 *   - apiClient llama authStore.accessToken
 *   - authStore.refresh() llama apiClient
 *   - ciclo infinito de refresh
 *
 * El cliente público es una instancia Axios minimal sin interceptores.
 * /api/v1/onboarding/seed usa apiClient porque requiere auth.
 *
 * Por qué AUTH_BASE_URL en lugar de derivar de API_BASE_URL?
 * API_BASE_URL puede ser '/api/v1' (relativa, sin host — caso producción con nginx).
 * Los endpoints /auth/* están en el mismo servidor pero bajo la ruta /auth,
 * no bajo /api/v1. La forma más explícita y robusta es leer VITE_AUTH_BASE_URL
 * del entorno; si no existe, derivamos eliminando '/api/v1' del final de
 * VITE_API_BASE_URL. Esto funciona tanto para '/api/v1' → '' como para
 * 'http://localhost:5001/api/v1' → 'http://localhost:5001'.
 */

import axios from 'axios'
import { API_BASE_URL } from './index'
import apiClient from './index'

// Base URL para los endpoints públicos de auth.
// Elimina '/api/v1' del final para obtener el host/path base.
// Casos:
//   'http://localhost:5001/api/v1' → 'http://localhost:5001'  (dev)
//   '/api/v1'                      → ''                       (prod con nginx)
const AUTH_BASE_URL = (import.meta.env.VITE_AUTH_BASE_URL as string | undefined)
  ?? API_BASE_URL.replace(/\/api\/v1\/?$/, '')

// Cliente público sin interceptores — para endpoints /auth/* que no
// requieren Authorization header.
const publicClient = axios.create({
  baseURL: AUTH_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  }
})

// ---------------------------------------------------------------------------
// Tipos de respuesta
// ---------------------------------------------------------------------------

export interface GoogleAuthResponse {
  access_token: string
  refresh_token: string
  user: {
    id: string
    email: string
    name: string
  }
  is_new_user: boolean
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
}

export interface OnboardingSeedResponse {
  accounts_created: number
  categories_created: number
  dashboard_created: boolean
}

// ---------------------------------------------------------------------------
// Funciones de API
// ---------------------------------------------------------------------------

/**
 * POST /auth/google
 * Valida el id_token de Google, crea o encuentra al usuario, emite JWT + refresh token.
 */
export async function postAuthGoogle(idToken: string): Promise<GoogleAuthResponse> {
  const response = await publicClient.post<GoogleAuthResponse>('/auth/google', {
    id_token: idToken
  })
  return response.data
}

/**
 * POST /auth/refresh
 * Renueva el JWT y rota el refresh token. El token viejo queda inválido.
 */
export async function postAuthRefresh(refreshToken: string): Promise<RefreshResponse> {
  const response = await publicClient.post<RefreshResponse>('/auth/refresh', {
    refresh_token: refreshToken
  })
  return response.data
}

/**
 * POST /auth/logout
 * Revoca el refresh token en el servidor. Endpoint público — no requiere JWT.
 * Idempotente: si el token no existe, retorna 204 igualmente.
 */
export async function postAuthLogout(refreshToken: string): Promise<void> {
  await publicClient.post('/auth/logout', {
    refresh_token: refreshToken
  })
}

/**
 * POST /api/v1/onboarding/seed
 * Genera seed data para el usuario autenticado (requiere JWT válido).
 * Solo puede llamarse una vez — 409 si el usuario ya tiene datos.
 */
export async function postOnboardingSeed(): Promise<OnboardingSeedResponse> {
  const response = await apiClient.post<OnboardingSeedResponse>('/onboarding/seed')
  return response.data
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

Expected: sin errores en `auth.ts`.

- [ ] **Step 3: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/api/auth.ts && git commit -m "feat(auth): add auth API functions for /auth/* and /onboarding/seed"
```

---

### Task 3: Crear `src/stores/auth.ts`

**Files:**
- Create: `frontend/src/stores/auth.ts`

**Contexto:** useAuthStore es el store central de autenticación. Gestiona: el `accessToken` en memoria (NUNCA en localStorage ni IndexedDB), el objeto `user` decodificado del JWT payload, y las acciones `loginWithGoogle`, `refresh`, y `logout`. El `refresh_token` siempre pasa por AuthDB (helpers de `auth-db.ts`). El nombre del usuario se extrae SOLO del JWT payload — no hay endpoint GET /users/me.

**Nota sobre Google Sign-In SDK:** El SDK `google.accounts.id` se carga via `<script>` en `index.html` (Task 8). En este store lo usamos via `window.google.accounts.id`. TypeScript necesitará la declaración de tipo global.

- [ ] **Step 1: Crear el archivo `frontend/src/stores/auth.ts`**

```typescript
/**
 * useAuthStore — store central de autenticación.
 *
 * INVARIANTES DE SEGURIDAD:
 * 1. accessToken vive SOLO en memoria (esta ref). Nunca en localStorage, nunca en AuthDB.
 * 2. refresh_token vive SOLO en AuthDB (Dexie). Nunca en memoria ni localStorage.
 * 3. user.name viene SOLO del JWT payload decodificado. No hay GET /users/me.
 * 4. logout() limpia el estado local INDEPENDIENTEMENTE de la respuesta del servidor.
 *    El usuario nunca queda "atrapado" sin poder desloguearse.
 *
 * FLUJO DE AUTENTICACIÓN:
 * 1. loginWithGoogle(idToken) → POST /auth/google → guarda accessToken en memoria,
 *    refresh_token en AuthDB, last_user_id en AuthDB, user en estado.
 * 2. refresh() → lee refresh_token de AuthDB → POST /auth/refresh → actualiza
 *    accessToken en memoria y rota refresh_token en AuthDB.
 * 3. logout() → POST /auth/logout (fire-and-forget) → limpia estado local siempre.
 *
 * DECODIFICACIÓN DEL JWT:
 * Un JWT tiene la forma header.payload.signature donde cada parte es base64url.
 * El payload (segundo segmento) contiene { sub, email, name, ... }.
 * Decodificamos SOLO el payload — no verificamos la firma en el cliente
 * (la verificación ya la hizo el servidor al emitir el token).
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getRefreshToken,
  setRefreshToken,
  deleteRefreshToken,
  setLastUserId,
  getLastUserId,
  deleteLastUserId,
} from '@/offline/auth-db'
import {
  postAuthGoogle,
  postAuthRefresh,
  postAuthLogout,
  type GoogleAuthResponse
} from '@/api/auth'

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

export interface AuthUser {
  id: string
  email: string
  name: string
}

// ---------------------------------------------------------------------------
// Helper: decodificar JWT payload (base64url → objeto)
//
// Por qué decodificamos nosotros y no usamos una librería?
// El payload de un JWT es simplemente base64url. Son 3 líneas de código.
// Agregar una dependencia (jwt-decode, etc.) por 3 líneas sería over-engineering.
// NO verificamos la firma — eso lo hace el servidor. Aquí solo extraemos los
// campos user visibles (sub, email, name) para mostrarlos en la UI.
// ---------------------------------------------------------------------------
function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    // El JWT tiene 3 segmentos separados por '.': header.payload.signature
    const payloadBase64 = token.split('.')[1]
    if (!payloadBase64) throw new Error('JWT inválido: no tiene payload')

    // base64url usa '-' y '_' en lugar de '+' y '/'
    // atob() solo entiende base64 estándar — reemplazamos antes de decodificar
    const base64 = payloadBase64.replace(/-/g, '+').replace(/_/g, '/')

    // decodeURIComponent(escape()) maneja correctamente caracteres UTF-8
    // en los strings del payload (p.ej. nombres con acentos)
    const jsonStr = decodeURIComponent(escape(atob(base64)))
    return JSON.parse(jsonStr) as Record<string, unknown>
  } catch (err) {
    console.error('[useAuthStore] Error decodificando JWT payload:', err)
    return {}
  }
}

function extractUserFromJwt(token: string): AuthUser | null {
  const payload = decodeJwtPayload(token)
  const id = payload['sub'] as string | undefined
  const email = payload['email'] as string | undefined
  const name = payload['name'] as string | undefined

  if (!id || !email || !name) return null
  return { id, email, name }
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAuthStore = defineStore('auth', () => {
  // ── Estado ────────────────────────────────────────────────────────────────

  /**
   * JWT de corta duración (24h). Solo en memoria — no persiste entre recargas.
   * Al recargar la app, main.ts llama authStore.refresh() para renovarlo
   * silenciosamente usando el refresh_token guardado en AuthDB.
   */
  const accessToken = ref<string | null>(null)

  /**
   * Datos del usuario extraídos del JWT payload. null cuando no hay sesión
   * activa (modo invitado).
   */
  const user = ref<AuthUser | null>(null)

  // ── Computed ──────────────────────────────────────────────────────────────

  const isAuthenticated = computed(() => accessToken.value !== null && user.value !== null)

  // ── Acciones ──────────────────────────────────────────────────────────────

  /**
   * loginWithGoogle — flujo completo de login OAuth.
   *
   * 1. Llama POST /auth/google con el id_token de Google
   * 2. Guarda accessToken en memoria
   * 3. Extrae user del JWT payload
   * 4. Guarda refresh_token en AuthDB
   * 5. Actualiza last_user_id en AuthDB
   * 6. Retorna { is_new_user, response } para que el caller maneje el onboarding
   *
   * @param idToken — El id_token de Google proveniente de google.accounts.id callback
   * @returns La respuesta completa de /auth/google (incluye is_new_user)
   */
  async function loginWithGoogle(idToken: string): Promise<GoogleAuthResponse> {
    const response = await postAuthGoogle(idToken)

    // Actualizar estado en memoria
    accessToken.value = response.access_token
    user.value = extractUserFromJwt(response.access_token)

    // Persistir refresh_token en AuthDB
    await setRefreshToken(response.refresh_token)

    // Persistir last_user_id para detectar cambios de usuario en el futuro
    await setLastUserId(response.user.id)

    return response
  }

  /**
   * refresh — renovación silenciosa del accessToken.
   *
   * Lee el refresh_token de AuthDB, llama POST /auth/refresh, y:
   * - Si exitoso: actualiza accessToken en memoria y rota el refresh_token en AuthDB.
   * - Si falla (401, token expirado, etc.): limpia accessToken y user (modo invitado).
   *
   * @returns true si el refresh fue exitoso, false si falló.
   */
  async function refresh(): Promise<boolean> {
    const storedRefreshToken = await getRefreshToken()
    if (!storedRefreshToken) {
      // No hay refresh token — modo invitado desde el inicio
      return false
    }

    try {
      const response = await postAuthRefresh(storedRefreshToken)

      // Actualizar estado en memoria
      accessToken.value = response.access_token
      user.value = extractUserFromJwt(response.access_token)

      // Rotar refresh_token en AuthDB — el token viejo ya es inválido
      await setRefreshToken(response.refresh_token)

      return true
    } catch {
      // Refresh falló — limpiar estado (modo invitado)
      // No tocamos WalletDB — invariante: datos en IndexedDB nunca se pierden
      // por problemas de autenticación.
      accessToken.value = null
      user.value = null
      await deleteRefreshToken()
      return false
    }
  }

  /**
   * logout — cerrar sesión.
   *
   * INVARIANTE: Limpia el estado local INDEPENDIENTEMENTE de la respuesta del servidor.
   * Si el servidor responde 401, 500, o la red falla — el frontend limpia el estado
   * igualmente. El usuario nunca queda "atrapado" sin poder desloguearse.
   *
   * @param clearWalletDb — si true, el caller es responsable de limpiar WalletDB.
   *   Este store NO toca WalletDB directamente para mantener separación de responsabilidades.
   */
  async function logout(): Promise<void> {
    // Intentar revocar el refresh token en el servidor (fire-and-forget)
    const storedRefreshToken = await getRefreshToken()
    if (storedRefreshToken) {
      try {
        await postAuthLogout(storedRefreshToken)
      } catch {
        // Ignorar errores del servidor — el estado local se limpia de todas formas
        console.warn('[useAuthStore] logout: servidor respondió con error, ignorando')
      }
    }

    // Limpiar estado local SIEMPRE — independientemente del resultado del servidor
    accessToken.value = null
    user.value = null
    await deleteRefreshToken()
    // Mantenemos last_user_id para detectar cambio de usuario en el próximo login
  }

  /**
   * clearLocalAuthState — limpiar estado sin llamar al servidor.
   * Usado internamente cuando el refresh falla durante sync (401 irrecuperable).
   */
  function clearLocalAuthState(): void {
    accessToken.value = null
    user.value = null
  }

  return {
    // Estado (readonly para externos)
    accessToken,
    user,
    // Computed
    isAuthenticated,
    // Acciones
    loginWithGoogle,
    refresh,
    logout,
    clearLocalAuthState,
    // Helper para SyncManager (acceso directo al last_user_id de AuthDB)
    getLastUserId,
    setLastUserId,
    deleteLastUserId,
  }
})
```

- [ ] **Step 2: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

Expected: sin errores en `auth.ts`. Si hay errores sobre `window.google`, los resolveremos en la Task 8.

- [ ] **Step 3: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/stores/auth.ts && git commit -m "feat(auth): add useAuthStore with Google OAuth flow, JWT decode, AuthDB integration"
```

---

## Chunk 2: Vista /login e integración Google SDK

### Task 4: Agregar Google Identity Services SDK a `index.html`

**Files:**
- Modify: `frontend/index.html`

**Contexto:** Google Identity Services SDK se carga como script externo en el `<head>`. Es necesario antes de poder usar `google.accounts.id.initialize()`. También necesitamos declarar los tipos de `window.google` en TypeScript.

- [ ] **Step 1: Leer el archivo `frontend/index.html` actual**

Leer `/Users/angelcorredor/Code/Wallet/frontend/index.html` para ver su contenido actual antes de modificar.

- [ ] **Step 2: Agregar el script de Google GSI en el `<head>`**

En `frontend/index.html`, agregar dentro del `<head>` antes del cierre `</head>`:

```html
<!-- Google Identity Services SDK — necesario para google.accounts.id.initialize() -->
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

- [ ] **Step 3: Crear declaración de tipos para `window.google`**

Crear el archivo `frontend/src/types/google-gsi.d.ts`:

```typescript
/**
 * Declaración de tipos para Google Identity Services (GSI) SDK.
 *
 * El SDK se carga externamente via <script> en index.html, por lo que
 * TypeScript no lo conoce por defecto. Esta declaración minimal cubre
 * solo los métodos que useAuthStore y LoginView usan.
 *
 * Documentación completa: https://developers.google.com/identity/gsi/web/reference/js-reference
 */

interface GoogleAccountsId {
  initialize(config: {
    client_id: string
    callback: (response: { credential: string }) => void
    auto_select?: boolean
    cancel_on_tap_outside?: boolean
  }): void
  prompt(momentListener?: (notification: {
    isNotDisplayed(): boolean
    isSkippedMoment(): boolean
  }) => void): void
  renderButton(
    parent: HTMLElement,
    options: {
      theme?: 'outline' | 'filled_blue' | 'filled_black'
      size?: 'large' | 'medium' | 'small'
      text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'
      shape?: 'rectangular' | 'pill' | 'circle' | 'square'
      width?: number
      locale?: string
    }
  ): void
  disableAutoSelect(): void
  revoke(hint: string, callback?: () => void): void
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: GoogleAccountsId
      }
    }
  }
}

export {}
```

- [ ] **Step 4: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

Expected: sin errores de tipos relacionados con `window.google`.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/index.html frontend/src/types/google-gsi.d.ts && git commit -m "feat(auth): add Google Identity Services SDK and window.google type declarations"
```

---

### Task 5: Crear `src/views/LoginView.vue`

**Files:**
- Create: `frontend/src/views/LoginView.vue`

**Contexto:** Vista minimalista con un único botón "Continuar con Google". Usa el SDK de Google (`window.google.accounts.id`) para inicializar el flujo OAuth y obtener el `id_token`. El flujo es: usuario toca el botón → Google muestra su selector de cuenta → callback recibe `credential` (el id_token) → llamamos `authStore.loginWithGoogle(credential)`. Después del login exitoso, el router navega a `/`.

**Diseño mobile-first:** Pantalla oscura centrada verticalmente. Logo o nombre de app en la parte superior, botón único en el centro. Mínimo 44px de altura en el botón.

- [ ] **Step 1: Crear el archivo `frontend/src/views/LoginView.vue`**

```vue
<script setup lang="ts">
/**
 * LoginView — vista de autenticación.
 *
 * Por qué un solo botón?
 * El ADD especifica: "un único botón 'Continuar con Google'". Sin formularios,
 * sin campos, sin complejidad. Google valida la identidad — nosotros solo
 * iniciamos el flujo y procesamos el resultado.
 *
 * Flujo OAuth:
 * 1. onMounted: inicializa el SDK de Google con VITE_GOOGLE_CLIENT_ID
 * 2. Usuario toca "Continuar con Google"
 * 3. Google presenta el selector de cuenta (popup nativo del browser)
 * 4. callback recibe { credential: id_token }
 * 5. loginWithGoogle(id_token) → POST /auth/google → estado actualizado
 * 6. router.push('/') — navegamos al home
 *
 * Por qué onMounted para inicializar google.accounts.id?
 * El SDK debe inicializarse DESPUÉS de que el DOM existe. onMounted garantiza
 * que el componente está en el DOM antes de llamar initialize().
 *
 * Por qué VITE_GOOGLE_CLIENT_ID via import.meta.env?
 * Las variables VITE_* en Vite se inline en el bundle en build time.
 * Es la forma estándar de inyectar configuración pública en Vite.
 */

import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const isLoading = ref(false)
const error = ref<string | null>(null)

// ---------------------------------------------------------------------------
// Inicializar Google Identity Services SDK
// ---------------------------------------------------------------------------
onMounted(() => {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

  if (!clientId) {
    console.warn('[LoginView] VITE_GOOGLE_CLIENT_ID no está configurado.')
    error.value = 'Configuración de Google OAuth faltante.'
    return
  }

  if (!window.google?.accounts?.id) {
    error.value = 'No se pudo cargar el SDK de Google. Verifica tu conexión.'
    return
  }

  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: handleGoogleCallback,
    auto_select: false,
    cancel_on_tap_outside: true,
  })
})

// ---------------------------------------------------------------------------
// Manejador del callback de Google
// ---------------------------------------------------------------------------
async function handleGoogleCallback(response: { credential: string }): Promise<void> {
  isLoading.value = true
  error.value = null

  try {
    await authStore.loginWithGoogle(response.credential)
    // Navegamos al home — la lógica post-login (onboarding, etc.) se maneja allí
    await router.push('/')
  } catch (err: unknown) {
    error.value = err instanceof Error
      ? err.message
      : 'Error al iniciar sesión con Google. Inténtalo de nuevo.'
    console.error('[LoginView] Error en loginWithGoogle:', err)
  } finally {
    isLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Iniciar flujo de Google (el botón llama a prompt())
// ---------------------------------------------------------------------------
function handleLoginClick(): void {
  if (!window.google?.accounts?.id) {
    error.value = 'SDK de Google no disponible. Recarga la página.'
    return
  }
  error.value = null
  window.google.accounts.id.prompt()
}
</script>

<template>
  <!--
    Por qué min-h-screen con flex center?
    La vista de login no usa AppLayout (sin nav inferior, sin header).
    Centramos verticalmente usando flex para que el contenido quede en el
    "golden ratio" visual de la pantalla, sin importar el tamaño del dispositivo.
  -->
  <div
    class="min-h-screen flex flex-col items-center justify-center px-6"
    style="background-color: #0f172a;"
  >
    <!-- Contenedor de contenido — max-width para tablets/desktop -->
    <div class="w-full max-w-sm space-y-8">

      <!-- Logo / nombre de app -->
      <div class="text-center space-y-2">
        <h1 class="text-3xl font-bold" style="color: #f1f5f9;">
          Wallet
        </h1>
        <p class="text-sm" style="color: #cbd5e1;">
          Tu finanzas personales, siempre contigo.
        </p>
      </div>

      <!-- Card del botón de login -->
      <div
        class="rounded-2xl p-6 space-y-4"
        style="background-color: #1e293b; border: 1px solid rgba(51, 65, 85, 0.5);"
      >

        <!-- Texto introductorio -->
        <p class="text-center text-sm" style="color: #cbd5e1;">
          Inicia sesión para sincronizar tus datos en todos tus dispositivos.
        </p>

        <!--
          Botón "Continuar con Google"
          Por qué min-h-[44px]?
          WCAG y Apple HIG recomiendan mínimo 44x44px para touch targets.
          En pantallas móviles, botones más pequeños son difíciles de tocar
          con precisión.

          Por qué w-full?
          En móvil, los botones de acción principal deben ocupar todo el ancho
          disponible para maximizar el área de toque y seguir convenciones
          de apps nativas.
        -->
        <button
          @click="handleLoginClick"
          :disabled="isLoading"
          class="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl
                 font-medium text-sm transition-all duration-200
                 disabled:opacity-50 disabled:cursor-not-allowed
                 min-h-[44px]"
          style="background-color: #ffffff; color: #0f172a;"
          aria-label="Continuar con Google para iniciar sesión"
        >
          <!-- Spinner de carga -->
          <svg
            v-if="isLoading"
            class="w-5 h-5 animate-spin flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              class="opacity-25"
              cx="12" cy="12" r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>

          <!-- Icono de Google (SVG inline oficial) -->
          <svg
            v-else
            class="w-5 h-5 flex-shrink-0"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>

          <span>{{ isLoading ? 'Iniciando sesión...' : 'Continuar con Google' }}</span>
        </button>

        <!-- Mensaje de error -->
        <p
          v-if="error"
          class="text-center text-xs"
          style="color: #ef4444;"
          role="alert"
          aria-live="assertive"
        >
          {{ error }}
        </p>

      </div>

      <!-- Nota de modo invitado -->
      <p class="text-center text-xs" style="color: #64748b;">
        Puedes usar la app sin cuenta.
        <button
          @click="$router.push('/')"
          class="underline transition-colors duration-150"
          style="color: #3b82f6;"
        >
          Continuar como invitado
        </button>
      </p>

    </div>
  </div>
</template>
```

- [ ] **Step 2: Agregar la ruta `/login` en `frontend/src/router/index.ts`**

En `frontend/src/router/index.ts`, agregar la ruta antes del catch-all `/:pathMatch(.*)*`:

```typescript
{
  path: '/login',
  name: 'login',
  component: () => import('@/views/LoginView.vue'),
  meta: {
    title: 'Iniciar sesión',
    // Esta ruta NO usa AppLayout — tiene su propio layout centrado
    noLayout: true,
  }
},
```

- [ ] **Step 3: Actualizar `App.vue` para soportar `noLayout`**

En `frontend/src/App.vue`, modificar el template para que las rutas con `meta.noLayout: true` rendericen `RouterView` directamente sin `AppLayout`:

Leer el archivo primero, luego aplicar el cambio en el `<template>`:

```vue
<template>
  <div id="app" class="min-h-screen">
    <!-- Rutas con noLayout (ej: /login) no usan AppLayout -->
    <RouterView v-if="$route.meta.noLayout" />

    <!-- Resto de rutas usan el layout completo con navegación -->
    <AppLayout v-else>
      <RouterView />
    </AppLayout>

    <!-- Global toast notifications -->
    <BaseToast />
  </div>
</template>
```

- [ ] **Step 4: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

Expected: sin errores en `LoginView.vue`, `router/index.ts`, o `App.vue`.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/views/LoginView.vue frontend/src/router/index.ts frontend/src/App.vue && git commit -m "feat(auth): add /login view with Google OAuth button and noLayout router support"
```

---

## Chunk 3: Interceptores Axios y estado `guest` en SyncStore

### Task 6: Agregar interceptor Authorization en `src/api/index.ts`

**Files:**
- Modify: `frontend/src/api/index.ts`

**Contexto:** El interceptor de request de `apiClient` debe inyectar `Authorization: Bearer <accessToken>` cuando hay un accessToken en memoria. El store se accede via `useAuthStore()` lazy (igual que sync-manager accede a useSyncStore con un lazy getter) para evitar el problema de "getActivePinia was called before Pinia is ready".

- [ ] **Step 1: Leer el archivo actual**

Leer `/Users/angelcorredor/Code/Wallet/frontend/src/api/index.ts`.

- [ ] **Step 2: Reemplazar el interceptor de request vacío por uno que inyecta el token**

Localizar el bloque:

```typescript
// Request interceptor - Add auth token if needed in future
apiClient.interceptors.request.use(
  (config) => {
    // Future: Add authentication token here
    // const token = localStorage.getItem('auth_token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)
```

Reemplazar con:

```typescript
// Request interceptor — inyectar Authorization header cuando hay accessToken en memoria.
//
// Por qué un lazy getter en lugar de import directo al top?
// apiClient se instancia como singleton a nivel de módulo — antes de que Pinia
// esté inicializada. Si importamos useAuthStore() al top, useSyncStore() tiraría
// "getActivePinia was called with no active Pinia". El lazy getter difiere la
// llamada a useAuthStore() hasta el primer request, que siempre ocurre DESPUÉS
// de app.mount() y de pinia.use(app).
//
// Por qué no importar desde '@/stores' (barrel)?
// Evitamos import circulares: auth.ts importa auth API que importa apiClient.
// Importar directamente desde el archivo del store es más seguro.
import { useAuthStore } from '@/stores/auth'

function getAuthStore() {
  try {
    return useAuthStore()
  } catch {
    // Pinia aún no está lista (llamada a nivel de módulo)
    return null
  }
}

apiClient.interceptors.request.use(
  (config) => {
    const authStore = getAuthStore()
    if (authStore?.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)
```

**Nota importante:** El import de `useAuthStore` debe ir al principio del archivo, junto con los otros imports, no dentro del bloque del interceptor. Solo la función `getAuthStore()` va en el cuerpo del módulo.

La modificación real es:

1. Agregar `import { useAuthStore } from '@/stores/auth'` a los imports del archivo.
2. Agregar la función `getAuthStore()` antes de los interceptores.
3. Reemplazar el cuerpo del interceptor de request.

- [ ] **Step 3: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/api/index.ts && git commit -m "feat(auth): inject Authorization header in apiClient request interceptor"
```

---

### Task 7: Agregar interceptor Authorization en `src/api/sync-client.ts`

**Files:**
- Modify: `frontend/src/api/sync-client.ts`

**Contexto:** `syncClient` es una instancia Axios separada de `apiClient` porque necesita acceso a los headers de respuesta (el cursor de sync). Requiere el mismo interceptor de Authorization para que los requests de sync incluyan el JWT.

- [ ] **Step 1: Leer el archivo actual**

Leer `/Users/angelcorredor/Code/Wallet/frontend/src/api/sync-client.ts`.

- [ ] **Step 2: Agregar import y interceptor de request**

El archivo actual solo crea y exporta `syncClient`. Agregar al final del archivo (antes del export o inline):

```typescript
import { useAuthStore } from '@/stores/auth'

function getAuthStore() {
  try {
    return useAuthStore()
  } catch {
    return null
  }
}

// Inyectar Authorization header en todos los requests de sync.
// Mismo patrón que apiClient — lazy getter para evitar el problema de
// Pinia no inicializada a nivel de módulo.
syncClient.interceptors.request.use(
  (config) => {
    const authStore = getAuthStore()
    if (authStore?.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)
```

- [ ] **Step 3: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/api/sync-client.ts && git commit -m "feat(auth): inject Authorization header in syncClient request interceptor"
```

---

### Task 8: Agregar estado `guest` a `useSyncStore`

**Files:**
- Modify: `frontend/src/stores/sync.ts`

**Contexto:** El ADD requiere un nuevo estado `guest` en `syncStatus` para reflejar "online pero no autenticado". La prioridad en el computed `syncStatus` es: `offline` > `syncing` > `error` > `pending` > `guest` > `synced`. "Guest" significa: tenemos conectividad pero no hay JWT — los datos no se sincronizan con el servidor.

- [ ] **Step 1: Leer el archivo actual**

Leer `/Users/angelcorredor/Code/Wallet/frontend/src/stores/sync.ts`.

- [ ] **Step 2: Actualizar el tipo del computed `syncStatus`**

Localizar la línea:

```typescript
const syncStatus = computed<'synced' | 'syncing' | 'pending' | 'error' | 'offline'>(() => {
```

Reemplazar con:

```typescript
const syncStatus = computed<'synced' | 'syncing' | 'pending' | 'error' | 'offline' | 'guest'>(() => {
```

- [ ] **Step 3: Agregar ref `isGuest` y setter `setGuest()`**

Localizar la sección de refs (después de `const errors = ref<SyncError[]>([])`), agregar:

```typescript
/**
 * True cuando el usuario no está autenticado pero está online.
 * Indica modo invitado: la app funciona localmente pero no sincroniza.
 * Establecido por main.ts después del boot refresh o cuando un 401 es irrecuperable.
 */
const isGuest = ref(false)
```

- [ ] **Step 4: Agregar `guest` a la lógica del computed**

Localizar el computed actual:

```typescript
const syncStatus = computed<...>(() => {
  if (!isOnline.value) return 'offline'
  if (isSyncing.value) return 'syncing'
  if (errorCount.value > 0) return 'error'
  if (pendingCount.value > 0) return 'pending'
  return 'synced'
})
```

Reemplazar con:

```typescript
const syncStatus = computed<'synced' | 'syncing' | 'pending' | 'error' | 'offline' | 'guest'>(() => {
  if (!isOnline.value) return 'offline'
  if (isSyncing.value) return 'syncing'
  if (errorCount.value > 0) return 'error'
  if (pendingCount.value > 0) return 'pending'
  if (isGuest.value) return 'guest'
  return 'synced'
})
```

- [ ] **Step 5: Agregar setter `setGuest()` en la sección de Setters**

En la sección de setters (después de `function clearErrors()`), agregar:

```typescript
function setGuest(value: boolean): void {
  isGuest.value = value
}
```

- [ ] **Step 6: Agregar `isGuest` y `setGuest` al return del store**

En el `return { ... }` del store, agregar:

```typescript
isGuest,
setGuest,
```

- [ ] **Step 7: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

Expected: sin errores. Si hay lugares en el codebase que hacen match exhaustivo sobre `syncStatus` (`'synced' | 'syncing' | 'pending' | 'error' | 'offline'`), TypeScript los detectará — necesitan agregar el caso `'guest'`.

- [ ] **Step 8: Buscar y actualizar referencias a `syncStatus` que necesiten el caso `guest`**

```bash
cd /Users/angelcorredor/Code/Wallet && grep -r "syncStatus" frontend/src --include="*.vue" --include="*.ts" -l
```

Revisar cada archivo y agregar manejo del estado `guest` donde sea necesario (ej: `SyncBadge.vue`, `SyncIndicator.vue`).

- [ ] **Step 9: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/stores/sync.ts && git commit -m "feat(auth): add 'guest' status to syncStore syncStatus computed"
```

---

## Chunk 4: Banner de modo invitado, Settings y boot

### Task 9: Crear `src/components/sync/GuestBanner.vue`

**Files:**
- Create: `frontend/src/components/sync/GuestBanner.vue`

**Contexto:** Banner persistente visible cuando `!authStore.isAuthenticated`. Usa el mismo patrón de animación que `NetworkBanner.vue` (max-height collapse, push-down del layout). Aparece debajo de `NetworkBanner` en `AppLayout`. El texto es exactamente el especificado en el ADD. No tiene botón de cierre — se oculta automáticamente cuando el usuario se autentica.

- [ ] **Step 1: Crear el archivo `frontend/src/components/sync/GuestBanner.vue`**

```vue
<script setup lang="ts">
/**
 * GuestBanner — banner informativo para modo invitado.
 *
 * Visible cuando el usuario no está autenticado (isAuthenticated = false).
 * Informa que los cambios no se sincronizan con la nube y ofrece un enlace
 * directo a la vista de login.
 *
 * Por qué amber y no azul?
 * El banner de red usa amber (advertencia de conectividad). Reutilizamos
 * el mismo color semántico: amber = "algo a tener en cuenta, no un error".
 * El modo invitado no es un error — es un estado funcional informativo.
 *
 * Por qué no mostrar cuando está offline?
 * Si el dispositivo no tiene conexión (NetworkBanner visible), mostrar ambos
 * banners sería redundante y ocuparía demasiado espacio vertical en móvil.
 * El banner de red tiene prioridad visual. Cuando vuelva la conexión y siga
 * sin autenticación, GuestBanner aparecerá automáticamente.
 */

import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSyncStore } from '@/stores/sync'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const syncStore = useSyncStore()
const router = useRouter()

// Mostrar solo cuando: no autenticado Y online (NetworkBanner no está visible)
const isVisible = computed(
  () => !authStore.isAuthenticated && syncStore.isOnline
)

function goToLogin(): void {
  router.push('/login')
}
</script>

<template>
  <Transition name="banner">
    <div
      v-if="isVisible"
      role="status"
      aria-live="polite"
      class="w-full flex items-center justify-between gap-2 px-4 py-2 text-sm font-medium overflow-hidden"
      style="background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border-bottom: 1px solid rgba(245, 158, 11, 0.2);"
    >
      <span class="flex-1 text-xs leading-snug">
        Los cambios realizados no serán guardados en la nube. Inicia sesión para sincronizar tus datos.
      </span>
      <button
        @click="goToLogin"
        class="flex-shrink-0 text-xs font-semibold underline underline-offset-2 transition-opacity duration-150 hover:opacity-80 min-h-[44px] px-2"
        style="color: #fbbf24;"
        aria-label="Ir a la pantalla de inicio de sesión"
      >
        Iniciar sesión
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.banner-enter-active {
  transition: max-height 0.3s ease-out, opacity 0.3s ease-out;
}

.banner-leave-active {
  transition: max-height 0.25s ease-in, opacity 0.25s ease-in;
}

.banner-enter-from,
.banner-leave-to {
  max-height: 0;
  opacity: 0;
}

.banner-enter-to,
.banner-leave-from {
  max-height: 3rem;
  opacity: 1;
}
</style>
```

- [ ] **Step 2: Agregar `<GuestBanner />` en `AppLayout.vue`**

En `frontend/src/components/layout/AppLayout.vue`:

1. Agregar el import: `import GuestBanner from '@/components/sync/GuestBanner.vue'`
2. En el template, agregar `<GuestBanner />` justo después de `<NetworkBanner />`:

```vue
<NetworkBanner />
<GuestBanner />
```

- [ ] **Step 3: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/components/sync/GuestBanner.vue frontend/src/components/layout/AppLayout.vue && git commit -m "feat(auth): add GuestBanner component and integrate into AppLayout"
```

---

### Task 10: Actualizar `SettingsView.vue` — saludo y botón logout

**Files:**
- Modify: `frontend/src/views/settings/SettingsView.vue`

**Contexto:** La vista de Settings necesita dos cambios según el ADD:
1. Al inicio de la página: "Hola, **[nombre]**" (o "Hola, **Invitado**" si `authStore.user` es null)
2. Al final de la página: botón "Cerrar sesión" con un prompt modal que ofrece dos opciones

**Prompt de logout:**
- "Mantener en modo invitado" → limpia auth (logout()), WalletDB intacta
- "Borrar todo" → limpia auth (logout()) + limpia WalletDB completa

Para limpiar WalletDB, usamos `db.delete()` seguido de reinicialización, o `db.tables.forEach(t => t.clear())`. El ADD especifica limpiar WalletDB completa — usaremos `await Promise.all(db.tables.map(t => t.clear()))` para no corromper el schema de Dexie (que necesita las tablas vacías pero existentes).

- [ ] **Step 1: Leer el archivo actual de SettingsView.vue**

Leer `/Users/angelcorredor/Code/Wallet/frontend/src/views/settings/SettingsView.vue`.

- [ ] **Step 2: Actualizar el `<script setup>` — agregar imports y lógica de logout**

Agregar al principio del script (junto con los imports existentes):

```typescript
import { ref, watch } from 'vue'              // ya existe
import { useSettingsStore } from '@/stores/settings'  // ya existe
import { useSyncStore } from '@/stores/sync'          // ya existe
import { syncManager } from '@/offline/sync-manager'  // ya existe
// NUEVO:
import { useAuthStore } from '@/stores/auth'
import { db } from '@/offline/db'
import { useRouter } from 'vue-router'
```

Agregar después de las declaraciones existentes de stores:

```typescript
const authStore = useAuthStore()
const router = useRouter()

// Estado del modal de logout
const showLogoutModal = ref(false)
const isLoggingOut = ref(false)

// Nombre a mostrar en el saludo
const displayName = computed(() => authStore.user?.name ?? 'Invitado')

async function handleLogoutKeepData(): Promise<void> {
  isLoggingOut.value = true
  try {
    await authStore.logout()
    showLogoutModal.value = false
    // El GuestBanner aparecerá automáticamente al quedar !isAuthenticated
  } finally {
    isLoggingOut.value = false
  }
}

async function handleLogoutDeleteAll(): Promise<void> {
  isLoggingOut.value = true
  try {
    await authStore.logout()
    // Limpiar WalletDB — borrar el contenido de todas las tablas
    // (no usamos db.delete() porque recrearía el schema en la siguiente apertura
    //  y podría causar race conditions con el SyncManager activo)
    await Promise.all(db.tables.map(t => t.clear()))
    showLogoutModal.value = false
    // Navegar al home — la app queda en modo invitado vacío
    await router.push('/')
  } finally {
    isLoggingOut.value = false
  }
}
```

- [ ] **Step 3: Actualizar el `<template>` — agregar saludo al inicio y botón al final**

Al inicio del template (antes del primer `<div class="space-y-6">`), agregar un bloque de saludo. Al final (después de la sección de Sincronización), agregar el botón de logout y el modal.

Saludo al inicio:

```vue
<!-- Saludo de usuario -->
<div class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 p-4">
  <p class="text-base text-dark-text-secondary">
    Hola,
    <span class="font-bold text-dark-text-primary">{{ displayName }}</span>
  </p>
  <p v-if="!authStore.isAuthenticated" class="mt-1 text-xs text-dark-text-secondary">
    Estás en modo invitado. Tus datos se guardan localmente.
  </p>
</div>
```

Botón de logout al final (después de la sección de Sincronización, dentro del `<div class="space-y-6">`):

```vue
<!-- Cerrar sesión -->
<div class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 p-4 space-y-4">
  <div>
    <h2 class="text-base font-semibold text-dark-text-primary">Sesión</h2>
    <p class="mt-0.5 text-sm text-dark-text-secondary leading-relaxed">
      {{ authStore.isAuthenticated ? 'Sesión activa con Google.' : 'Modo invitado activo.' }}
    </p>
  </div>
  <div class="border-t border-dark-bg-tertiary/50" />
  <button
    v-if="authStore.isAuthenticated"
    @click="showLogoutModal = true"
    class="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg
           text-sm font-medium transition-colors min-h-[44px]
           border border-dark-bg-tertiary/50"
    style="background-color: transparent; color: #ef4444;"
    aria-label="Cerrar sesión de la cuenta de Google"
  >
    Cerrar sesión
  </button>
  <p v-else class="text-sm text-dark-text-secondary">
    <button
      @click="$router.push('/login')"
      class="underline transition-colors duration-150 min-h-[44px] inline-flex items-center"
      style="color: #3b82f6;"
    >
      Iniciar sesión con Google
    </button>
    para sincronizar tus datos.
  </p>
</div>
```

Modal de logout:

```vue
<!-- Modal de confirmación de logout -->
<Teleport to="body">
  <Transition name="fade">
    <div
      v-if="showLogoutModal"
      class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
      style="background-color: rgba(0,0,0,0.6);"
      @click.self="showLogoutModal = false"
      role="dialog"
      aria-modal="true"
      aria-labelledby="logout-modal-title"
    >
      <div
        class="w-full max-w-sm rounded-2xl p-6 space-y-4"
        style="background-color: #1e293b; border: 1px solid rgba(51,65,85,0.5);"
      >
        <h3
          id="logout-modal-title"
          class="text-base font-bold text-dark-text-primary"
        >
          Cerrar sesión
        </h3>
        <p class="text-sm text-dark-text-secondary leading-relaxed">
          ¿Qué quieres hacer con tus datos locales?
        </p>

        <div class="space-y-3">
          <!-- Mantener datos -->
          <button
            @click="handleLogoutKeepData"
            :disabled="isLoggingOut"
            class="w-full px-4 py-3 rounded-xl text-sm font-medium text-left
                   transition-colors duration-150 min-h-[44px]
                   disabled:opacity-50 disabled:cursor-not-allowed"
            style="background-color: #334155; color: #f1f5f9;"
          >
            <span class="block font-semibold">Mantener en modo invitado</span>
            <span class="block text-xs mt-0.5" style="color: #94a3b8;">
              Tus datos locales se conservan. Podrás seguir usando la app.
            </span>
          </button>

          <!-- Borrar todo -->
          <button
            @click="handleLogoutDeleteAll"
            :disabled="isLoggingOut"
            class="w-full px-4 py-3 rounded-xl text-sm font-medium text-left
                   transition-colors duration-150 min-h-[44px]
                   disabled:opacity-50 disabled:cursor-not-allowed"
            style="background-color: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.2);"
          >
            <span class="block font-semibold">Borrar todo</span>
            <span class="block text-xs mt-0.5" style="color: #f87171;">
              Se eliminan todos los datos locales. Esta acción no se puede deshacer.
            </span>
          </button>

          <!-- Cancelar -->
          <button
            @click="showLogoutModal = false"
            :disabled="isLoggingOut"
            class="w-full px-4 py-2 rounded-xl text-sm text-dark-text-secondary
                   transition-colors duration-150 min-h-[44px]
                   disabled:opacity-50"
          >
            Cancelar
          </button>
        </div>

        <!-- Spinner mientras se procesa -->
        <p v-if="isLoggingOut" class="text-center text-xs text-dark-text-secondary">
          Cerrando sesión...
        </p>
      </div>
    </div>
  </Transition>
</Teleport>
```

- [ ] **Step 4: Agregar `computed` al import de vue**

Asegurarse que `computed` está importado en el `import { ref, watch } from 'vue'` — cambiarlo a `import { ref, computed, watch } from 'vue'`.

- [ ] **Step 5: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

Expected: sin errores en `SettingsView.vue`.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/views/settings/SettingsView.vue && git commit -m "feat(auth): update SettingsView with user greeting and logout flow with data options"
```

---

## Chunk 5: Boot, SyncManager 401 y lógica post-login

### Task 11: Actualizar `main.ts` — boot refresh silencioso

**Files:**
- Modify: `frontend/src/main.ts`

**Contexto:** Al iniciar la app, intentar renovar silenciosamente el accessToken usando el refresh_token guardado en AuthDB. Si exitoso → el usuario está autenticado sin intervención. Si falla → modo invitado con `syncStore.setGuest(true)`. El sync solo debe correr si hay sesión activa (o si queremos permitir sync en modo invitado, que el ADD no especifica — lo dejamos solo para autenticados).

- [ ] **Step 1: Leer el archivo actual de `main.ts`**

Leer `/Users/angelcorredor/Code/Wallet/frontend/src/main.ts`.

- [ ] **Step 2: Agregar inicialización de authStore y boot refresh**

Después de `app.mount('#app')`, al inicio del bloque de importaciones de la Phase 4 (justo antes de `import { syncManager }`), agregar:

```typescript
import { useAuthStore } from '@/stores/auth'
```

Y dentro del bloque de inicialización async (o crear uno con IIFE), agregar la lógica de boot:

```typescript
/**
 * Phase 6 — Auth boot: intentar refresh silencioso al iniciar la app.
 *
 * Por qué aquí y no en un componente?
 * El refresh silencioso es una operación de bootstrap a nivel de app, no de UI.
 * Igual que settingsStore.loadSettings(), debe correr antes de que cualquier
 * componente intente acceder al estado de auth.
 *
 * Por qué IIFE async?
 * main.ts no puede ser async en su nivel superior (Vite lo rechaza).
 * El IIFE nos permite usar await sin bloquear el resto de la inicialización.
 *
 * Por qué solo correr processQueue si isAuthenticated?
 * El SyncManager requiere JWT para todos los endpoints. Sin autenticación,
 * todos los requests recibirán 401. El sync se activará automáticamente
 * cuando el usuario se autentique (loginWithGoogle → router.push('/') →
 * lógica post-login dispara processQueue).
 */
const authStore = useAuthStore()
const syncStore = useSyncStore()

;(async () => {
  const refreshed = await authStore.refresh()
  if (!refreshed) {
    // Sin sesión válida — modo invitado
    syncStore.setGuest(true)
  } else {
    // Sesión renovada — modo autenticado
    syncStore.setGuest(false)
    // Ejecutar sync inicial si estamos online
    if (isOnline.value) {
      syncManager.processQueue()
    }
  }
})().catch((err) => {
  console.warn('[boot] Auth refresh failed:', err)
  syncStore.setGuest(true)
})
```

**Nota:** El bloque de sync existente que llama `syncManager.processQueue()` al final de main.ts debe condicionarse a que el usuario esté autenticado. Localizar:

```typescript
// Process any mutations queued during a previous offline session.
if (isOnline.value) {
  syncManager.processQueue()
}
```

Y reemplazar con:

```typescript
// Process any mutations queued during a previous offline session.
// Solo si hay sesión activa — sin JWT todos los requests recibirán 401.
// El boot refresh silencioso (arriba) activa el sync cuando la sesión se recupera.
// (El sync se activa desde el IIFE de auth cuando refreshed = true)
```

El `onOnline` que también llama `syncManager.processQueue()` debe mantener la guarda de autenticación:

```typescript
onOnline(() => {
  syncStore.setOnline(true)
  // Solo sincronizar si el usuario está autenticado
  if (authStore.isAuthenticated) {
    syncManager.processQueue()
  }
})
```

Y el listener `wallet:mutation-queued`:

```typescript
window.addEventListener('wallet:mutation-queued', () => {
  if (isOnline.value && authStore.isAuthenticated) {
    syncManager.processQueue()
  }
})
```

Y el intervalo de 30 segundos:

```typescript
setInterval(() => {
  if (isOnline.value && authStore.isAuthenticated) {
    syncManager.processQueue()
  }
}, 30_000)
```

- [ ] **Step 3: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/main.ts && git commit -m "feat(auth): add silent boot refresh and gate sync on authentication in main.ts"
```

---

### Task 12: Agregar interceptor 401 en `SyncManager`

**Files:**
- Modify: `frontend/src/offline/sync-manager.ts`

**Contexto:** El ADD especifica: si el backend responde 401 durante sync → llamar `authStore.refresh()` → si exitoso reemplazar refresh_token en AuthDB y reintentar sync → si falla mostrar banner invitado. Los datos en IndexedDB NUNCA se tocan.

También necesitamos exponer `reset()` en SyncManager para el caso de cambio de usuario (Task 13): limpiar los cursores de sync y el estado interno (`this.processing`, `this.initialSyncComplete`, etc.).

**Estrategia:** El lugar correcto para interceptar 401 es dentro de `handleError()` en SyncManager, ANTES de que el error se trate como permanente. Si el status es 401, intentar refresh y si tiene éxito reiniciar el ciclo de procesamiento.

- [ ] **Step 1: Leer las secciones relevantes de sync-manager.ts**

Leer desde línea 335 (bloque `catch (error: unknown)` en processQueue) hasta ~430 para entender el flujo de manejo de errores.

- [ ] **Step 2: Agregar import lazy de authStore en sync-manager.ts**

Al principio de sync-manager.ts, junto a los otros lazy getters (getSyncStore, getUiStore), agregar:

```typescript
import { useAuthStore } from '@/stores/auth'

/**
 * Lazily resolve the auth store.
 * El mismo patrón que getSyncStore() — nunca llamar en module scope.
 */
function getAuthStore() {
  try {
    return useAuthStore()
  } catch {
    return null
  }
}
```

- [ ] **Step 3: Agregar lógica de refresh en el manejo de 401**

En el método `handleError()` del SyncManager (buscar el método con ese nombre), agregar antes del tratamiento de errores 4xx:

```typescript
// Si el servidor responde 401, intentar refresh del accessToken.
// Invariante: los datos en IndexedDB NO se tocan durante problemas de auth.
if (isApiError(error) && error.status === 401) {
  const authStore = getAuthStore()
  if (authStore) {
    const refreshed = await authStore.refresh()
    if (refreshed) {
      // Refresh exitoso — el interceptor de Axios inyectará el nuevo token
      // en el próximo request. No eliminamos la mutación — se reintentará
      // en el próximo ciclo de processQueue().
      console.log('[SyncManager] 401 → refresh exitoso, reintentando en el próximo ciclo.')
      const syncStore = getSyncStore()
      syncStore?.setGuest(false)
      return // No tratar como error permanente
    } else {
      // Refresh falló — modo invitado. Detener sync sin tocar IndexedDB.
      console.warn('[SyncManager] 401 → refresh falló, activando modo invitado.')
      const syncStore = getSyncStore()
      syncStore?.setGuest(true)
      authStore.clearLocalAuthState()
      // Lanzar un error especial para que processQueue sepa que debe detenerse
      throw new Error('AUTH_FAILED')
    }
  }
}
```

En `processQueue()`, el try/catch externo capturará el `AUTH_FAILED` y deberá detener el loop sin marcar la mutación como error permanente. Para esto, en `processQueue()` agregar detección:

```typescript
} catch (error: unknown) {
  if (error instanceof Error && error.message === 'AUTH_FAILED') {
    console.warn('[SyncManager] Sync detenido por fallo de autenticación irrecuperable.')
    break // Salir del loop de mutaciones sin más procesamiento
  }
  await this.handleError(mutation, error, syncStore)
}
```

- [ ] **Step 4: Agregar método `reset()` al SyncManager**

Al final de la clase SyncManager (antes del cierre `}`), agregar:

```typescript
/**
 * reset — reinicia completamente el estado del SyncManager.
 *
 * Llamado cuando se detecta un cambio de usuario (user_id del JWT distinto
 * al last_user_id en AuthDB). Limpia todos los cursores de sync para que
 * el próximo processQueue() haga un fullReadSync completo con los datos
 * del nuevo usuario.
 *
 * Por qué no limpiar WalletDB aquí?
 * WalletDB la limpia la vista/store que detecta el cambio de usuario.
 * SyncManager solo gestiona el estado de sync (cursores, flags internos).
 * Responsabilidades separadas.
 */
async reset(): Promise<void> {
  this.processing = false
  await this.clearSyncCursors()
  console.log('[SyncManager] Estado reseteado — listo para sync completo.')
}
```

- [ ] **Step 5: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

Expected: sin errores.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/offline/sync-manager.ts && git commit -m "feat(auth): add 401 refresh-retry interceptor and reset() to SyncManager"
```

---

## Chunk 6: Lógica post-login, cambio de usuario y onboarding

### Task 13: Lógica post-login — detección de datos guest, cambio de usuario, onboarding

**Files:**
- Create: `frontend/src/composables/usePostLoginFlow.ts`

**Contexto:** El ADD especifica 4 escenarios post-login con lógica compleja. En lugar de saturar un componente o store existente, extraemos esta lógica a un composable dedicado `usePostLoginFlow`. Este composable:

1. Detecta cambio de usuario (user_id del JWT ≠ last_user_id en AuthDB) → limpia WalletDB + resetea SyncManager
2. Verifica si hay datos guest (al menos 1 transacción en WalletDB)
3. Decide qué flujo activar según `is_new_user` y estado de la queue
4. Expone prompts reactivos para que el componente/vista los renderice

El composable es llamado desde `LoginView.vue` después de un login exitoso.

- [ ] **Step 1: Crear el archivo `frontend/src/composables/usePostLoginFlow.ts`**

```typescript
/**
 * usePostLoginFlow — lógica post-login: onboarding, migración de datos guest,
 * cambio de usuario.
 *
 * Por qué un composable y no lógica en el store o la vista?
 * Esta lógica tiene múltiples dependencias (db, authDb, syncManager, mutationQueue,
 * authStore, syncStore, router) y produce estado reactivo (prompts, contadores).
 * Un composable permite aislarla, testearla, y reutilizarla independientemente de
 * la vista que la invoca.
 *
 * FLUJOS IMPLEMENTADOS (del ADD):
 *
 * 1. Cambio de usuario (user_id JWT ≠ last_user_id en AuthDB):
 *    → limpiar WalletDB sin preguntar
 *    → actualizar last_user_id en AuthDB
 *    → resetear SyncManager
 *    → sync completo desde backend
 *
 * 2. is_new_user = true:
 *    → sync pending mutations
 *    → mostrar prompt de onboarding
 *
 * 3. is_new_user = false + queue vacía:
 *    → sync normal
 *
 * 4. is_new_user = false + queue con ítems:
 *    → mostrar prompt con conteo de datos guest
 *    → si acepta: sync pending mutations → sync normal
 *    → si descarta: vaciar queue → sync normal desde backend
 *
 * CRITERIO "datos guest": al menos 1 transacción en WalletDB.
 */

import { ref } from 'vue'
import { db } from '@/offline/db'
import { setLastUserId } from '@/offline/auth-db'
import { mutationQueue } from '@/offline/mutation-queue'
import { syncManager } from '@/offline/sync-manager'
import { postOnboardingSeed } from '@/api/auth'
import { useSyncStore } from '@/stores/sync'
import type { GoogleAuthResponse } from '@/api/auth'

// ---------------------------------------------------------------------------
// Tipos de los prompts
// ---------------------------------------------------------------------------

export type PostLoginStep =
  | 'idle'
  | 'user-change-cleaning'          // Limpiando WalletDB por cambio de usuario
  | 'guest-data-prompt'             // Prompt: ¿qué hacemos con los datos guest?
  | 'onboarding-prompt'             // Prompt: ¿quieres seed data?
  | 'syncing'                       // Ejecutando sync
  | 'done'

export interface GuestDataCounts {
  transactions: number
  accounts: number
  categories: number
}

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export function usePostLoginFlow() {
  const syncStore = useSyncStore()

  // Estado del flujo
  const step = ref<PostLoginStep>('idle')
  const guestCounts = ref<GuestDataCounts>({ transactions: 0, accounts: 0, categories: 0 })
  const isProcessing = ref(false)
  const error = ref<string | null>(null)

  /**
   * run — punto de entrada principal. Llamado inmediatamente después de
   * loginWithGoogle() con la respuesta del servidor.
   *
   * @param response — respuesta de POST /auth/google
   * @param previousUserId — last_user_id que había en AuthDB ANTES del login
   *   (debe leerse ANTES de llamar loginWithGoogle para comparar correctamente)
   */
  async function run(response: GoogleAuthResponse, previousUserId: string | undefined): Promise<void> {
    isProcessing.value = true
    error.value = null

    try {
      // ── Caso 1: Cambio de usuario ───────────────────────────────────────
      const isUserChange = previousUserId !== undefined && previousUserId !== response.user.id

      if (isUserChange) {
        step.value = 'user-change-cleaning'
        await handleUserChange(response.user.id)
        // Después de limpiar, hacer sync completo y terminar
        step.value = 'syncing'
        await syncManager.processQueue()
        step.value = 'done'
        return
      }

      // ── Caso 2: Usuario nuevo ───────────────────────────────────────────
      if (response.is_new_user) {
        // Sync pending mutations (son del nuevo usuario) luego mostrar onboarding
        step.value = 'syncing'
        await syncManager.processQueue()
        step.value = 'onboarding-prompt'
        // El flujo continúa cuando el usuario responde al prompt (via acceptOnboarding/rejectOnboarding)
        return
      }

      // ── Casos 3 y 4: Usuario existente ──────────────────────────────────
      const queueCount = await mutationQueue.count()

      if (queueCount === 0) {
        // Caso 3: queue vacía → sync normal
        step.value = 'syncing'
        await syncManager.processQueue()
        step.value = 'done'
        return
      }

      // Caso 4: queue con ítems → verificar si hay datos guest reales
      const hasGuestData = await checkHasGuestData()

      if (!hasGuestData) {
        // Sin transacciones reales — sync normal sin preguntar
        step.value = 'syncing'
        await syncManager.processQueue()
        step.value = 'done'
        return
      }

      // Hay datos guest con al menos 1 transacción — mostrar prompt con conteo
      const counts = await countGuestData()
      guestCounts.value = counts
      step.value = 'guest-data-prompt'
      // El flujo continúa vía acceptGuestData/rejectGuestData
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Error inesperado en el flujo post-login.'
      console.error('[usePostLoginFlow] Error:', err)
      step.value = 'done'
    } finally {
      if (step.value !== 'onboarding-prompt' && step.value !== 'guest-data-prompt') {
        isProcessing.value = false
      }
    }
  }

  // ── Caso 4a: Usuario acepta migrar datos guest ─────────────────────────────
  async function acceptGuestData(): Promise<void> {
    isProcessing.value = true
    step.value = 'syncing'
    try {
      // Sincronizar pending mutations (datos guest van al servidor)
      await syncManager.processQueue()
      // Después del sync, mostrar onboarding si es necesario (aquí no aplica)
      step.value = 'done'
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Error al sincronizar datos.'
    } finally {
      isProcessing.value = false
    }
  }

  // ── Caso 4b: Usuario descarta datos guest ────────────────────────────────
  async function rejectGuestData(): Promise<void> {
    isProcessing.value = true
    step.value = 'syncing'
    try {
      // Vaciar la queue sin enviar nada al servidor
      const allMutations = await mutationQueue.getAll()
      await Promise.all(allMutations.map(m => mutationQueue.remove(m.id!)))
      // Limpiar WalletDB para que el sync cargue solo datos del servidor
      await Promise.all(db.tables.map(t => t.clear()))
      // Sync completo desde backend
      await syncManager.processQueue()
      step.value = 'done'
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Error al descartar datos.'
    } finally {
      isProcessing.value = false
    }
  }

  // ── Onboarding: usuario acepta seed data ─────────────────────────────────
  async function acceptOnboarding(): Promise<void> {
    isProcessing.value = true
    step.value = 'syncing'
    try {
      await postOnboardingSeed()
      // Sync para traer el seed data al IndexedDB local
      await syncManager.processQueue()
      step.value = 'done'
    } catch (err: unknown) {
      // 409 = ya tiene datos (llamada duplicada) — no es un error crítico
      console.warn('[usePostLoginFlow] onboarding/seed:', err)
      await syncManager.processQueue()
      step.value = 'done'
    } finally {
      isProcessing.value = false
    }
  }

  // ── Onboarding: usuario rechaza seed data ────────────────────────────────
  async function rejectOnboarding(): Promise<void> {
    // Nada que hacer — sync ya corrió antes del prompt
    step.value = 'done'
    isProcessing.value = false
  }

  // ── Helpers privados ──────────────────────────────────────────────────────

  async function handleUserChange(newUserId: string): Promise<void> {
    // Limpiar WalletDB sin preguntar (datos del usuario anterior)
    await Promise.all(db.tables.map(t => t.clear()))
    // Actualizar last_user_id en AuthDB
    await setLastUserId(newUserId)
    // Resetear SyncManager (cursores, retry counters, initialSyncComplete)
    await syncManager.reset()
    syncStore.setInitialSyncComplete(false)
    console.log('[usePostLoginFlow] Cambio de usuario detectado — WalletDB limpiada.')
  }

  /**
   * Criterio: al menos 1 transacción en WalletDB.
   * Los settings existen por defecto y no se consideran datos del usuario.
   */
  async function checkHasGuestData(): Promise<boolean> {
    const transactionCount = await db.transactions.count()
    return transactionCount > 0
  }

  async function countGuestData(): Promise<GuestDataCounts> {
    const [transactions, accounts, categories] = await Promise.all([
      db.transactions.count(),
      db.accounts.count(),
      db.categories.count(),
    ])
    return { transactions, accounts, categories }
  }

  return {
    // Estado
    step,
    guestCounts,
    isProcessing,
    error,
    // Acciones
    run,
    acceptGuestData,
    rejectGuestData,
    acceptOnboarding,
    rejectOnboarding,
  }
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

Expected: sin errores en `usePostLoginFlow.ts`.

- [ ] **Step 3: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/composables/usePostLoginFlow.ts && git commit -m "feat(auth): add usePostLoginFlow composable for post-login scenarios"
```

---

### Task 14: Integrar `usePostLoginFlow` en `LoginView.vue`

**Files:**
- Modify: `frontend/src/views/LoginView.vue`

**Contexto:** LoginView necesita integrar el composable post-login. Después de `authStore.loginWithGoogle()`, leemos `previousUserId` de AuthDB ANTES del login (para detectar cambio de usuario), luego llamamos `postLoginFlow.run()`. Los prompts se renderizan en el mismo componente como modales superpuestos al contenido de login.

- [ ] **Step 1: Leer el archivo actual `LoginView.vue`**

Leer `/Users/angelcorredor/Code/Wallet/frontend/src/views/LoginView.vue`.

- [ ] **Step 2: Actualizar el `<script setup>` de LoginView.vue**

Agregar al `<script setup>`:

```typescript
import { getLastUserId } from '@/offline/auth-db'
import { usePostLoginFlow } from '@/composables/usePostLoginFlow'

const postLoginFlow = usePostLoginFlow()
```

Modificar `handleGoogleCallback` para integrar el flujo:

```typescript
async function handleGoogleCallback(response: { credential: string }): Promise<void> {
  isLoading.value = true
  error.value = null

  try {
    // Leer el last_user_id ANTES del login para detectar cambio de usuario
    const previousUserId = await getLastUserId()

    const loginResponse = await authStore.loginWithGoogle(response.credential)

    // Iniciar lógica post-login (onboarding, migración, cambio de usuario)
    await postLoginFlow.run(loginResponse, previousUserId)

    // Si no hay prompts pendientes, navegar al home inmediatamente
    if (postLoginFlow.step.value === 'done') {
      await router.push('/')
    }
    // Si hay prompts (onboarding-prompt o guest-data-prompt), el template
    // los renderiza — la navegación ocurre cuando el usuario responde.
  } catch (err: unknown) {
    error.value = err instanceof Error
      ? err.message
      : 'Error al iniciar sesión con Google. Inténtalo de nuevo.'
    console.error('[LoginView] Error en loginWithGoogle:', err)
  } finally {
    isLoading.value = false
  }
}

// Manejadores de los prompts post-login
async function onAcceptGuestData(): Promise<void> {
  await postLoginFlow.acceptGuestData()
  if (postLoginFlow.step.value === 'done') await router.push('/')
}

async function onRejectGuestData(): Promise<void> {
  await postLoginFlow.rejectGuestData()
  if (postLoginFlow.step.value === 'done') await router.push('/')
}

async function onAcceptOnboarding(): Promise<void> {
  await postLoginFlow.acceptOnboarding()
  if (postLoginFlow.step.value === 'done') await router.push('/')
}

async function onRejectOnboarding(): Promise<void> {
  postLoginFlow.rejectOnboarding()
  await router.push('/')
}
```

- [ ] **Step 3: Agregar modales de prompts al template de LoginView.vue**

Antes del cierre `</template>`, agregar (usando Teleport para los modales):

```vue
<!-- Modal: prompt de datos guest (Caso 4) -->
<Teleport to="body">
  <Transition name="fade">
    <div
      v-if="postLoginFlow.step.value === 'guest-data-prompt'"
      class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
      style="background-color: rgba(0,0,0,0.7);"
      role="dialog"
      aria-modal="true"
      aria-labelledby="guest-data-title"
    >
      <div
        class="w-full max-w-sm rounded-2xl p-6 space-y-4"
        style="background-color: #1e293b; border: 1px solid rgba(51,65,85,0.5);"
      >
        <h3 id="guest-data-title" class="text-base font-bold" style="color: #f1f5f9;">
          Encontramos datos sin cuenta
        </h3>
        <p class="text-sm leading-relaxed" style="color: #cbd5e1;">
          Encontramos
          <strong>{{ postLoginFlow.guestCounts.value.accounts }} cuenta(s)</strong>,
          <strong>{{ postLoginFlow.guestCounts.value.transactions }} transacción(es)</strong>
          y
          <strong>{{ postLoginFlow.guestCounts.value.categories }} categoría(s)</strong>
          creados sin cuenta.
          ¿Las agregamos a tu perfil o las descartamos?
        </p>
        <div class="space-y-3">
          <button
            @click="onAcceptGuestData"
            :disabled="postLoginFlow.isProcessing.value"
            class="w-full px-4 py-3 rounded-xl text-sm font-semibold min-h-[44px]
                   transition-colors duration-150 disabled:opacity-50"
            style="background-color: #3b82f6; color: #ffffff;"
          >
            Agregar a mi perfil
          </button>
          <button
            @click="onRejectGuestData"
            :disabled="postLoginFlow.isProcessing.value"
            class="w-full px-4 py-3 rounded-xl text-sm font-medium min-h-[44px]
                   transition-colors duration-150 disabled:opacity-50"
            style="background-color: #334155; color: #f1f5f9;"
          >
            Descartar datos locales
          </button>
        </div>
        <p v-if="postLoginFlow.isProcessing.value" class="text-center text-xs" style="color: #94a3b8;">
          Procesando...
        </p>
      </div>
    </div>
  </Transition>
</Teleport>

<!-- Modal: prompt de onboarding (Caso 2 — usuario nuevo) -->
<Teleport to="body">
  <Transition name="fade">
    <div
      v-if="postLoginFlow.step.value === 'onboarding-prompt'"
      class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
      style="background-color: rgba(0,0,0,0.7);"
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
    >
      <div
        class="w-full max-w-sm rounded-2xl p-6 space-y-4"
        style="background-color: #1e293b; border: 1px solid rgba(51,65,85,0.5);"
      >
        <h3 id="onboarding-title" class="text-base font-bold" style="color: #f1f5f9;">
          Bienvenido a Wallet
        </h3>
        <p class="text-sm leading-relaxed" style="color: #cbd5e1;">
          ¿Quieres empezar con cuentas y categorías de ejemplo, o prefieres empezar desde cero?
        </p>
        <div class="space-y-3">
          <button
            @click="onAcceptOnboarding"
            :disabled="postLoginFlow.isProcessing.value"
            class="w-full px-4 py-3 rounded-xl text-sm font-semibold min-h-[44px]
                   transition-colors duration-150 disabled:opacity-50"
            style="background-color: #3b82f6; color: #ffffff;"
          >
            Empezar con ejemplos
          </button>
          <button
            @click="onRejectOnboarding"
            :disabled="postLoginFlow.isProcessing.value"
            class="w-full px-4 py-3 rounded-xl text-sm font-medium min-h-[44px]
                   transition-colors duration-150 disabled:opacity-50"
            style="background-color: #334155; color: #f1f5f9;"
          >
            Empezar desde cero
          </button>
        </div>
        <p v-if="postLoginFlow.isProcessing.value" class="text-center text-xs" style="color: #94a3b8;">
          Configurando...
        </p>
      </div>
    </div>
  </Transition>
</Teleport>
```

- [ ] **Step 4: Verificar TypeScript**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

Expected: sin errores.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelcorredor/Code/Wallet && git add frontend/src/views/LoginView.vue && git commit -m "feat(auth): integrate post-login flow into LoginView with onboarding and guest data prompts"
```

---

## Chunk 7: Verificación final y lint

### Task 15: Verificación completa del plan

- [ ] **Step 1: Ejecutar type-check completo**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run type-check 2>&1
```

Expected: 0 errores. Si hay errores, corregirlos antes de continuar.

- [ ] **Step 2: Ejecutar lint**

```bash
cd /Users/angelcorredor/Code/Wallet/frontend && npm run lint 2>&1
```

Expected: 0 errores, 0 advertencias críticas.

- [ ] **Step 3: Verificar que SyncBadge/SyncIndicator manejan el estado `guest`**

```bash
cd /Users/angelcorredor/Code/Wallet && grep -r "syncStatus\|syncStore" frontend/src/components/sync/ --include="*.vue" -l
```

Para cada archivo encontrado, verificar que el caso `'guest'` está manejado (texto, color, icono apropiados).

- [ ] **Step 4: Verificar que no hay referencias a `localStorage` para tokens**

```bash
cd /Users/angelcorredor/Code/Wallet && grep -r "localStorage" frontend/src --include="*.ts" --include="*.vue" | grep -i "token\|auth\|refresh"
```

Expected: sin resultados. El token solo vive en memoria (store Pinia) y AuthDB.

- [ ] **Step 5: Verificar que `user_id` no se guarda en WalletDB**

```bash
cd /Users/angelcorredor/Code/Wallet && grep -r "user_id" frontend/src/offline/db.ts
```

Expected: sin resultados (WalletDB v6 sin `user_id` en schemas).

- [ ] **Step 6: Verificar que `VITE_GOOGLE_CLIENT_ID` está en el archivo `.env.example` o documentado**

```bash
ls /Users/angelcorredor/Code/Wallet/frontend/.env* 2>/dev/null || echo "no .env files found"
```

Si existe un `.env.example` o `.env.local`, agregar `VITE_GOOGLE_CLIENT_ID=` a él.

- [ ] **Step 7: Commit final de lint fixes**

```bash
cd /Users/angelcorredor/Code/Wallet && git add -p && git commit -m "fix(auth): apply lint fixes and handle 'guest' syncStatus in sync components"
```

---

## Resumen de archivos

### Nuevos
| Archivo | Task |
|---------|------|
| `frontend/src/offline/auth-db.ts` | Task 1 |
| `frontend/src/api/auth.ts` | Task 2 |
| `frontend/src/stores/auth.ts` | Task 3 |
| `frontend/src/types/google-gsi.d.ts` | Task 4 |
| `frontend/src/views/LoginView.vue` | Task 5 |
| `frontend/src/components/sync/GuestBanner.vue` | Task 9 |
| `frontend/src/composables/usePostLoginFlow.ts` | Task 13 |

### Modificados
| Archivo | Task |
|---------|------|
| `frontend/index.html` | Task 4 |
| `frontend/src/router/index.ts` | Task 5 |
| `frontend/src/App.vue` | Task 5 |
| `frontend/src/api/index.ts` | Task 6 |
| `frontend/src/api/sync-client.ts` | Task 7 |
| `frontend/src/stores/sync.ts` | Task 8 |
| `frontend/src/components/layout/AppLayout.vue` | Task 9 |
| `frontend/src/views/settings/SettingsView.vue` | Task 10 |
| `frontend/src/main.ts` | Task 11 |
| `frontend/src/offline/sync-manager.ts` | Task 12 |

---

## Verificación de completitud por sub-tarea del ADD

### Ticket 1 — AuthDB, useAuthStore, vista /login
- [x] `src/offline/auth-db.ts` con tabla `{ key, value }` y helpers tipados (Task 1)
- [x] `useAuthStore` con `loginWithGoogle`, `refresh`, `logout`, decodificación JWT (Task 3)
- [x] Lectura de `VITE_GOOGLE_CLIENT_ID` (Task 5, `LoginView.vue`)
- [x] Vista `/login` con botón único "Continuar con Google" (Task 5)
- [x] Google Sign-In SDK cargado (Task 4)

### Ticket 2 — Settings, banner invitado, interceptores Axios
- [x] Settings con "Hola, [nombre]" / "Hola, Invitado" (Task 10)
- [x] Botón "Cerrar sesión" con prompt "Mantener" / "Borrar todo" (Task 10)
- [x] Banner modo invitado `GuestBanner.vue` (Task 9)
- [x] Estado `guest` en `syncStatus` (Task 8)
- [x] Interceptor Authorization en `apiClient` (Task 6)
- [x] Interceptor Authorization en `syncClient` (Task 7)

### Ticket 3 — Lógica post-login, onboarding, cambio de usuario
- [x] Interceptor 401 en SyncManager con refresh → retry (Task 12)
- [x] `is_new_user = true` → sync + onboarding prompt (Task 13/14)
- [x] `is_new_user = false + queue vacía` → sync normal (Task 13)
- [x] `is_new_user = false + queue con ítems` → prompt con conteo (Task 13/14)
- [x] Cambio de usuario → limpiar WalletDB + resetear SyncManager (Task 13)
- [x] Criterio datos guest: al menos 1 transacción (Task 13)
- [x] Prompt onboarding → `POST /api/v1/onboarding/seed` (Task 13/14)
- [x] Boot refresh silencioso en `main.ts` (Task 11)
- [x] SyncManager `reset()` expuesto (Task 12)
