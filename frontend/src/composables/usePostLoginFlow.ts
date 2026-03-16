/**
 * usePostLoginFlow — handles the 4 post-login scenarios defined in the ADD.
 *
 * Called from LoginView after a successful Google OAuth login.
 * Never touches IndexedDB for destructive reasons without user consent,
 * preserving the core invariant: data is never lost due to auth issues.
 */

import { db } from '@/offline/db'
import { mutationQueue } from '@/offline/mutation-queue'
import { getLastUserId, setLastUserId } from '@/offline/auth-db'
import { syncManager } from '@/offline/sync-manager'
import { postOnboardingSeed } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

export function usePostLoginFlow() {
  const authStore = useAuthStore()
  const uiStore = useUiStore()

  async function handlePostLogin(isNewUser: boolean): Promise<void> {
    const currentUserId = authStore.user?.id

    if (isNewUser) {
      await handleNewUser()
      if (currentUserId) await setLastUserId(currentUserId)
      return
    }

    const lastUserId = await getLastUserId()
    const pendingCount = await db.pendingMutations.count()

    // Scenario 4: user switch — different user logged in on this device
    if (lastUserId && currentUserId && lastUserId !== currentUserId) {
      await handleUserSwitch(currentUserId)
      return
    }

    // Scenario 2: existing user, nothing pending
    if (pendingCount === 0) {
      syncManager.processQueue()
      if (currentUserId) await setLastUserId(currentUserId)
      return
    }

    // Scenario 3 / same user refresh expired: has pending data
    const txCount = await db.transactions.count()
    if (txCount > 0) {
      await handleSameUserWithPendingData()
    } else {
      syncManager.processQueue()
    }

    if (currentUserId) await setLastUserId(currentUserId)
  }

  async function handleNewUser(): Promise<void> {
    // Sync any guest mutations first (they belong to this new user)
    syncManager.processQueue()

    const accepted = await uiStore.showConfirm({
      title: '¿Cómo quieres empezar?',
      message: '¿Quieres empezar con cuentas y categorías de ejemplo o prefieres empezar desde cero?',
      confirmLabel: 'Usar ejemplos',
      cancelLabel: 'Empezar desde cero',
    })

    if (accepted) {
      try {
        await postOnboardingSeed()
        syncManager.processQueue()
      } catch {
        // 409 = already seeded, or network error — both are safe to ignore
      }
    }
  }

  async function handleUserSwitch(newUserId: string): Promise<void> {
    // Clear all local data — belongs to previous user
    await db.delete()
    await db.open()
    await setLastUserId(newUserId)
    // Force full page reload to clear all in-memory Pinia store state.
    // Without this, stores still hold the previous user's data even after
    // IndexedDB is cleared. The reload starts fresh and triggers a full sync.
    window.location.replace('/')
  }

  async function handleSameUserWithPendingData(): Promise<void> {
    const [accountCount, txCount, categoryCount] = await Promise.all([
      db.accounts.count(),
      db.transactions.count(),
      db.categories.count(),
    ])

    const accepted = await uiStore.showConfirm({
      title: 'Datos locales encontrados',
      message: `Encontramos ${accountCount} cuentas, ${txCount} transacciones y ${categoryCount} categorías creadas sin cuenta. ¿Las agregamos a tu perfil o las descartamos?`,
      confirmLabel: 'Agregar a mi perfil',
      cancelLabel: 'Descartar',
    })

    if (accepted) {
      syncManager.processQueue()
    } else {
      await mutationQueue.clear()
      syncManager.processQueue()
    }
  }

  return { handlePostLogin }
}
