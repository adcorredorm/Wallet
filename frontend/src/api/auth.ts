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
  ?? (API_BASE_URL ?? 'http://localhost:5000').replace(/\/api\/v1\/?$/, '')

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
