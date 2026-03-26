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
import { ref, computed, readonly } from 'vue'
import {
  getRefreshToken,
  setRefreshToken,
  deleteRefreshToken,
  setLastUserId,
  getLastUserId,
  deleteLastUserId,
  getLastUser,
  setLastUser,
  deleteLastUser,
} from '@/offline/auth-db'
import { db } from '@/offline/db'
import {
  postAuthGoogle,
  postAuthRefresh,
  postAuthLogout,
  type GoogleAuthResponse
} from '@/api/auth'
import { useSyncStore } from '@/stores/sync'

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
    // atob() solo entiende base64 estándar — reemplazamos antes de decodificar.
    // Añadimos padding '=' para que atob() no falle con payloads cuyo largo
    // no es múltiplo de 4.
    const base64 = payloadBase64
      .replace(/-/g, '+')
      .replace(/_/g, '/')
      .padEnd(payloadBase64.length + (4 - (payloadBase64.length % 4)) % 4, '=')

    // Convertimos cada carácter del string binario a su byte correspondiente
    // usando Uint8Array + TextDecoder, que maneja correctamente UTF-8
    // (p.ej. nombres con acentos: 'Ángel').
    // La técnica atob() → charCodeAt → Uint8Array → TextDecoder.decode()
    // es el patrón estándar para decodificar base64url con UTF-8 en el browser
    // y en entornos Node/Vitest.
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    const jsonStr = new TextDecoder('utf-8').decode(bytes)
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

  /**
   * isAuthenticated — true when the user has a valid access token in memory.
   * Required for API calls (sync). Becomes false on reload until refresh() completes.
   */
  const isAuthenticated = computed(() => accessToken.value !== null && user.value !== null)

  /**
   * hasSession — true when user identity is known, even without an access token.
   * Used by UI (GuestBanner, SettingsView) to avoid the "flash to guest" problem:
   * on reload, user data is restored from AuthDB before refresh() completes, so
   * the user sees their Dexie data immediately while the access token is fetched.
   *
   * Why keep isAuthenticated separate?
   * SyncManager gates API calls on isAuthenticated (needs the access token).
   * hasSession only says "we know who this user is" — not "we can make API calls".
   */
  const hasSession = computed(() => user.value !== null)

  // ── Acciones ──────────────────────────────────────────────────────────────

  /**
   * loginWithGoogle — flujo completo de login OAuth.
   *
   * 1. Llama POST /auth/google con el id_token de Google
   * 2. Guarda accessToken en memoria
   * 3. Extrae user del JWT payload
   * 4. Guarda refresh_token en AuthDB
   * 5. Actualiza last_user_id en AuthDB
   * 6. Retorna la respuesta completa para que el caller maneje el onboarding
   *
   * @param idToken — El id_token de Google proveniente de google.accounts.id callback
   * @returns La respuesta completa de /auth/google (incluye is_new_user)
   */
  async function loginWithGoogle(idToken: string): Promise<GoogleAuthResponse> {
    const response = await postAuthGoogle(idToken)

    // Actualizar estado en memoria
    accessToken.value = response.access_token
    user.value = extractUserFromJwt(response.access_token)

    // Salir del modo invitado — el usuario ya está autenticado
    useSyncStore().setGuest(false)

    // Persistir refresh_token en AuthDB
    await setRefreshToken(response.refresh_token)

    // Persistir identidad del usuario para restauración offline en próximo reload
    if (user.value) await setLastUser(user.value)

    // NOTA: last_user_id se actualiza en handlePostLogin (usePostLoginFlow),
    // DESPUÉS de detectar si hay cambio de usuario. No lo actualizamos aquí
    // porque si lo hacemos antes, handlePostLogin leerá el nuevo ID y nunca
    // detectará que el usuario cambió.

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

      // Actualizar estado en memoria y salir del modo invitado
      accessToken.value = response.access_token
      user.value = extractUserFromJwt(response.access_token)
      useSyncStore().setGuest(false)

      // Rotar refresh_token en AuthDB — el token viejo ya es inválido
      await setRefreshToken(response.refresh_token)

      // Actualizar identidad persistida en AuthDB
      if (user.value) await setLastUser(user.value)

      return true
    } catch (err) {
      // Siempre limpiamos el accessToken en memoria — no se puede hacer sync.
      accessToken.value = null

      // Solo borramos el refresh_token y el user persistido si el servidor lo
      // rechazó explícitamente con 401 (token expirado o revocado). Para errores
      // transitorios conservamos ambos para que el próximo intento pueda usarlos.
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 401) {
        user.value = null
        await deleteRefreshToken()
        await deleteLastUser()
      }
      // For transient errors, leave user.value intact (hasSession stays true)
      // so the UI continues showing the user's Dexie data during retry delays.

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
   * @param clearLocalData — Si true, también borra WalletDB por completo (usado al
   *   cambiar de usuario). Si false, conserva los datos locales (logout simple).
   */
  async function logout(clearLocalData = false): Promise<void> {
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
    await deleteLastUser()
    // Mantenemos last_user_id para detectar cambio de usuario en el próximo login

    // Si se solicita limpiar datos locales (cambio de usuario), borrar WalletDB.
    // db.delete() elimina la base de datos IndexedDB por completo; db.open()
    // la recrea vacía con el schema actual. Esto garantiza que el nuevo usuario
    // no vea datos del usuario anterior.
    if (clearLocalData) {
      try {
        await db.delete()
        await db.open()
      } catch (err) {
        console.warn('[useAuthStore] logout: error al limpiar WalletDB:', err)
      }
    }
  }

  /**
   * initializeFromStorage — restaurar sesión silenciosa al arrancar la app.
   *
   * Se llama desde main.ts antes del primer mount. Lee el refresh_token de
   * AuthDB y, si existe, intenta renovar silenciosamente el accessToken.
   * Si no hay token o el refresh falla, la app arranca en modo invitado — sin error.
   *
   * Por qué aquí y no en un route guard?
   * Un route guard se ejecuta por primera vez DESPUÉS de que Vue Router intenta
   * navegar a la ruta inicial. En ese momento el store ya debería tener el estado
   * de autenticación. Si inicializáramos en el guard, habría un ciclo: el guard
   * llama a refresh(), refresh() actualiza el store, el guard re-evalúa. Hacerlo
   * en main.ts antes del mount es más simple y evita ese ciclo.
   */
  async function initializeFromStorage(): Promise<void> {
    const token = await getRefreshToken()
    if (!token) return  // Never logged in — guest mode from the start

    // Restore user from AuthDB immediately so the UI shows the user's Dexie
    // data before the refresh() call completes (offline-first: data in IndexedDB
    // is visible even without a network round-trip).
    // hasSession becomes true here; isAuthenticated remains false until refresh().
    const savedUser = await getLastUser()
    if (savedUser) {
      user.value = savedUser
    }

    // First refresh attempt — fast path for normal online startup.
    const ok = await refresh()
    if (ok) return

    // 401 path: refresh() clears user.value and deletes the token from AuthDB.
    const remaining = await getRefreshToken()
    if (!remaining) {
      // Session truly expired — user was already cleared by refresh(). Done.
      return
    }

    // Transient failure (network error, cold start): retries run in background
    // so the app can mount immediately. user.value is already set (hasSession=true)
    // so the user sees their Dexie data while retries are in progress.
    const RETRY_DELAYS_MS = [5_000, 10_000, 15_000]

    const retryInBackground = async (): Promise<void> => {
      for (const delayMs of RETRY_DELAYS_MS) {
        const tokenStillPresent = await getRefreshToken()
        if (!tokenStillPresent) return  // 401 already deleted the token — stop

        await new Promise<void>(resolve => setTimeout(resolve, delayMs))

        const success = await refresh()
        if (success) return

        // Check again after refresh — 401 may have deleted the token mid-retry
        const stillPresent = await getRefreshToken()
        if (!stillPresent) return
      }
      // All retries exhausted — user.value stays set (offline data still visible)
      // but accessToken is null so sync won't run.
    }

    // Fire-and-forget: retries update accessToken/user reactively when they succeed
    retryInBackground().catch(() => { /* offline mode — nothing to do */ })
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
    // Estado — readonly para que los consumidores externos no muten directamente.
    // Por qué readonly() y no computed()? readonly() wrappea el ref completo y
    // preserva la reactividad (los watchers siguen funcionando) sin exponer
    // el setter. computed() requeriría un getter explícito por cada campo.
    accessToken: readonly(accessToken),
    user: readonly(user),
    // Computed
    isAuthenticated,
    hasSession,
    // Acciones
    loginWithGoogle,
    refresh,
    logout,
    initializeFromStorage,
    clearLocalAuthState,
    // Helper para SyncManager (acceso directo al last_user_id de AuthDB)
    getLastUserId,
    setLastUserId,
    deleteLastUserId,
  }
})
