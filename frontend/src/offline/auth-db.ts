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
  key: string   // 'refresh_token' | 'last_user_id' | 'last_user'
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

// ---------------------------------------------------------------------------
// last_user — full user identity object ({ id, email, name })
//
// Stored as JSON so we can restore the user in memory on reload before the
// refresh() call completes. This lets the app show the user's Dexie data
// immediately (offline-capable) even while the access token is being fetched.
// ---------------------------------------------------------------------------

export interface StoredUser {
  id: string
  email: string
  name: string
}

export async function getLastUser(): Promise<StoredUser | undefined> {
  const entry = await authDb.auth.get('last_user')
  if (!entry) return undefined
  try {
    return JSON.parse(entry.value) as StoredUser
  } catch {
    return undefined
  }
}

export async function setLastUser(user: StoredUser): Promise<void> {
  await authDb.auth.put({ key: 'last_user', value: JSON.stringify(user) })
}

export async function deleteLastUser(): Promise<void> {
  await authDb.auth.delete('last_user')
}

/**
 * Limpiar completamente AuthDB — llamado en logout.
 * Elimina refresh_token, last_user_id, y last_user.
 */
export async function clearAuthDb(): Promise<void> {
  await authDb.auth.clear()
}

// ---------------------------------------------------------------------------
// sync_enabled — user preference for cloud sync (device-local, never synced)
//
// Why store as string in AuthDB instead of boolean?
// AuthDB's AuthEntry interface stores value: string. The typed helpers
// abstract the string<>boolean conversion away from callers.
//
// Default: true (sync is enabled unless the user explicitly disables it).
// ---------------------------------------------------------------------------

export async function getSyncEnabled(): Promise<boolean> {
  const entry = await authDb.auth.get('sync_enabled')
  if (!entry) return true // default: sync enabled
  return entry.value === 'true'
}

export async function setSyncEnabled(enabled: boolean): Promise<void> {
  await authDb.auth.put({ key: 'sync_enabled', value: String(enabled) })
}
