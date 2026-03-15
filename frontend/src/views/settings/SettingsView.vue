<script setup lang="ts">
/**
 * Settings View
 *
 * Why a dedicated settings page instead of a modal?
 * - A page has a stable URL (/settings), making it bookmarkable and
 *   navigable via the back button — consistent with mobile app conventions.
 * - Modals are better for transient, context-scoped actions (e.g., confirming
 *   a deletion). Settings are a first-class destination, not an interruption.
 * - The AppLayout header already provides a back-navigation affordance via
 *   the hamburger/back button, so no extra dismiss UI is needed.
 *
 * Why a writable computed is NOT used here for selectedCurrency?
 * - `setPrimaryCurrency()` in the settings store is async (writes to IndexedDB
 *   and enqueues a mutation). A computed setter runs synchronously — you cannot
 *   await inside it. Using `watch` instead lets us call the async action and
 *   then show a transient success indicator only after it resolves, without
 *   blocking the reactive update.
 * - The store already performs an optimistic update (Step 2 in setPrimaryCurrency),
 *   so the UI reflects the new value immediately. The watch just triggers the
 *   success flash after the IndexedDB write completes.
 *
 * Success indicator approach:
 * - A `ref<boolean>` (`saved`) flips to true after a successful write and
 *   returns to false after 2 000 ms via setTimeout.
 * - This avoids a full toast (overkill for a single-field change) while still
 *   giving the user clear reactive feedback without a page reload.
 *
 * Mobile-first considerations:
 * - Single-column card layout on mobile (320px+).
 * - BaseSelect uses the native <select> element — the browser's built-in
 *   picker is ideal on mobile (system fonts, touch-optimised scroll, no JS).
 * - Touch targets: the select is min-h-[44px] via the shared `select` class
 *   in the global stylesheet.
 * - Vertical spacing uses space-y-6 to give comfortable room on small screens.
 */

import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useSyncStore } from '@/stores/sync'
import { useAuthStore } from '@/stores/auth'
import { syncManager } from '@/offline/sync-manager'
import { SUPPORTED_CURRENCIES } from '@/utils/constants'
import BaseSelect from '@/components/ui/BaseSelect.vue'

const settingsStore = useSettingsStore()
const syncStore = useSyncStore()
const authStore = useAuthStore()
const router = useRouter()

// ---------------------------------------------------------------------------
// Logout modal state
//
// Why a local ref instead of a Pinia-based modal system?
// The logout modal is specific to this view and has no cross-component usage.
// A local ref is the simplest, most direct solution. If a global modal
// system is added in the future, this can be migrated then.
// ---------------------------------------------------------------------------
const showLogoutModal = ref(false)

function openLogoutModal(): void {
  showLogoutModal.value = true
}

function closeLogoutModal(): void {
  showLogoutModal.value = false
}

/**
 * Handle logout with the "keep data" option.
 *
 * Why logout(false)?
 * The user wants to leave the authenticated session but keep their local
 * IndexedDB data intact. They will continue in guest mode with all their
 * existing data available offline.
 */
async function handleLogoutKeepData(): Promise<void> {
  closeLogoutModal()
  await authStore.logout(false)
  await router.push('/')
}

/**
 * Handle logout with the "delete all data" option.
 *
 * Why logout(true)?
 * The user explicitly wants to clear all local data — typically because
 * they are handing the device to someone else or switching accounts.
 * authStore.logout(true) deletes WalletDB and re-creates it empty.
 */
async function handleLogoutDeleteAll(): Promise<void> {
  closeLogoutModal()
  await authStore.logout(true)
  await router.push('/')
}

async function handleForceSync(): Promise<void> {
  await syncManager.forceFullSync()
}

// ---------------------------------------------------------------------------
// Currency options — shaped for BaseSelect's { value, label } contract.
// We derive this from SUPPORTED_CURRENCIES so the two sources of truth stay
// in sync: adding a currency to constants.ts automatically surfaces it here.
// ---------------------------------------------------------------------------
const currencyOptions = SUPPORTED_CURRENCIES.map(c => ({
  value: c.code,
  label: `${c.name} (${c.code})`
}))

// ---------------------------------------------------------------------------
// Local selected value — initialised from the store's current primary currency.
// Why a local ref instead of binding directly to settingsStore.primaryCurrency?
// BaseSelect emits 'update:modelValue' synchronously on every change. If we
// bound directly to the store, we'd need the store setter to be synchronous
// or risk a brief mismatch. The local ref acts as an immediate-response
// bridge: the UI updates instantly, and the watch flushes the async store
// write in the background.
// ---------------------------------------------------------------------------
const selectedCurrency = ref(settingsStore.primaryCurrency)

// ---------------------------------------------------------------------------
// Success / error UI state
// ---------------------------------------------------------------------------
const saved = ref(false)
const saveError = ref<string | null>(null)
let savedTimer: ReturnType<typeof setTimeout> | null = null

// ---------------------------------------------------------------------------
// Watch the local selected value and propagate to the store asynchronously.
//
// Why `{ immediate: false }`?
// We only want to react to user-initiated changes, not the initial mount where
// selectedCurrency already equals the store value.
//
// Why not debounce?
// The dropdown is a discrete selection (not a text field). The user picks one
// option and the change fires exactly once. Debouncing would add latency
// without any benefit.
// ---------------------------------------------------------------------------
watch(selectedCurrency, async (newCode) => {
  saved.value = false
  saveError.value = null

  try {
    await settingsStore.setPrimaryCurrency(newCode)
    saved.value = true

    // Clear any previous timer so rapid changes don't stack up.
    if (savedTimer) clearTimeout(savedTimer)
    savedTimer = setTimeout(() => {
      saved.value = false
    }, 2000)
  } catch (err: unknown) {
    saveError.value = err instanceof Error ? err.message : 'Error al guardar'
  }
})

// ---------------------------------------------------------------------------
// Derived: full currency object for the "Moneda actual" display line.
// Using SUPPORTED_CURRENCIES.find() is cheap (9 items max) and avoids
// duplicating name/symbol data inside this component.
// ---------------------------------------------------------------------------
function currentCurrencyLabel(): string {
  const match = SUPPORTED_CURRENCIES.find(c => c.code === settingsStore.primaryCurrency)
  return match ? `${match.name} (${match.code})` : settingsStore.primaryCurrency
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page heading with greeting -->
    <div>
      <h1 class="text-2xl font-bold text-dark-text-primary">Configuración</h1>
      <!--
        Greeting — shows the authenticated user's name or "Invitado".

        Why display the name here instead of in the header?
        Settings is the natural place for user identity — it's where you go
        to manage your account. The header is better reserved for navigation
        context (page title, back button). Placing it here keeps the header
        clean and groups identity with account management.

        Why font-medium on the name?
        Visually distinguishes the name from the surrounding text without
        requiring a color change. Matches the pattern used throughout the
        app for "label: value" pairs (e.g., "Moneda actual: USD").
      -->
      <p class="mt-1 text-sm text-dark-text-secondary">
        Hola,
        <span class="font-medium text-dark-text-primary">
          {{ authStore.user ? authStore.user.name : 'Invitado' }}
        </span>
      </p>
    </div>

    <!--
      Primary currency section
      Why a card (bg-dark-bg-secondary)?
      Groups related controls visually using the same card pattern used
      throughout the app (CategoriesListView, AccountsListView, etc.).
    -->
    <div class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 p-4 space-y-4">

      <!-- Section header -->
      <div>
        <h2 class="text-base font-semibold text-dark-text-primary">
          Moneda principal
        </h2>
        <p class="mt-0.5 text-sm text-dark-text-secondary leading-relaxed">
          La moneda en la que se mostrarán los balances convertidos en toda la aplicación.
        </p>
      </div>

      <!-- Divider -->
      <div class="border-t border-dark-bg-tertiary/50" />

      <!-- Currency selector -->
      <BaseSelect
        v-model="selectedCurrency"
        :options="currencyOptions"
        label="Seleccionar moneda"
        :disabled="settingsStore.loading"
      />

      <!--
        Status row: shows the active currency name + transient feedback.
        Why keep success/error inline rather than a toast?
        The setting change is local to this card — inline feedback is spatially
        closer to the control that triggered it, which reduces cognitive load on
        mobile where the toast appears far from the interaction point.
      -->
      <div class="flex items-center justify-between gap-2 min-h-[1.25rem]">
        <!-- Current value label -->
        <p class="text-sm text-dark-text-secondary">
          Moneda actual:
          <span class="font-medium text-dark-text-primary">
            {{ currentCurrencyLabel() }}
          </span>
        </p>

        <!--
          Transient success indicator.
          Why v-show instead of v-if?
          v-show keeps the element in the DOM so the Transition can animate
          both entering and leaving. v-if would destroy the element immediately
          on the leave phase, cutting the transition short.
        -->
        <Transition name="fade">
          <span
            v-show="saved"
            class="flex items-center gap-1 text-xs font-medium text-accent-green"
            aria-live="polite"
          >
            <!-- Checkmark icon (Heroicons outline, 16px) -->
            <svg
              class="w-4 h-4 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            Guardado
          </span>
        </Transition>

        <!-- Inline error (only shown on failure) -->
        <span
          v-if="saveError"
          class="text-xs text-accent-red"
          aria-live="assertive"
        >
          {{ saveError }}
        </span>
      </div>

    </div>

    <!-- Sincronización -->
    <div class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 p-4 space-y-4">
      <div>
        <h2 class="text-base font-semibold text-dark-text-primary">
          Sincronización
        </h2>
        <p class="mt-0.5 text-sm text-dark-text-secondary leading-relaxed">
          Descarga todos los datos nuevamente desde el servidor. Útil si los datos locales parecen incompletos.
        </p>
      </div>

      <div class="border-t border-dark-bg-tertiary/50" />

      <button
        @click="handleForceSync"
        :disabled="syncStore.isSyncing"
        class="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg
               bg-blue-600 text-white text-sm font-medium
               hover:bg-blue-700
               disabled:opacity-50 disabled:cursor-not-allowed
               transition-colors min-h-[44px]"
        aria-label="Forzar sincronización completa con el servidor"
      >
        <span v-if="syncStore.isSyncing">Sincronizando...</span>
        <span v-else>Forzar sincronización completa</span>
      </button>
    </div>

    <!--
      Cerrar sesión section — only rendered when authenticated.

      Why v-if="authStore.isAuthenticated" instead of v-show?
      The button should not exist at all in guest mode — it's semantically
      meaningless to "log out" when you are not logged in. v-if is correct
      here: we want to remove the element from the DOM entirely, not just
      hide it, to avoid any possibility of focus or keyboard access.
    -->
    <div
      v-if="authStore.isAuthenticated"
      class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50 p-4 space-y-4"
    >
      <div>
        <h2 class="text-base font-semibold text-dark-text-primary">
          Cuenta
        </h2>
        <p class="mt-0.5 text-sm text-dark-text-secondary leading-relaxed">
          Gestiona tu sesión y los datos locales del dispositivo.
        </p>
      </div>

      <div class="border-t border-dark-bg-tertiary/50" />

      <!--
        "Cerrar sesión" button.

        Why a dedicated section (card) instead of a floating button?
        Groups the destructive action with its context ("Cuenta") following
        the same card pattern used throughout the app. A floating button
        at the bottom of the page would be visually orphaned and might be
        mistaken for a FAB.

        Why text-red-400 but not bg-red?
        Red background buttons are for immediately destructive actions with
        no undo (e.g., "Eliminar cuenta permanentemente"). Logout is
        recoverable — the user can log back in. Red text on a neutral
        background communicates "caution" without "danger".
      -->
      <button
        @click="openLogoutModal"
        class="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg
               border border-red-500/30 text-red-400 text-sm font-medium
               hover:bg-red-500/10
               transition-colors min-h-[44px]"
        aria-label="Cerrar sesión de tu cuenta"
      >
        <!-- Logout icon (Heroicons outline) -->
        <svg
          class="w-4 h-4 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
          />
        </svg>
        Cerrar sesión
      </button>
    </div>

    <!--
      Logout modal / dialog

      Why a custom modal instead of the browser's confirm() dialog?
      1. confirm() is synchronous and blocks the UI — bad for mobile.
      2. confirm() doesn't support custom styling or multiple buttons.
      3. We need TWO options (keep data vs. delete all), which confirm()
         cannot provide.

      Why not Teleport to <body>?
      The modal uses a fixed overlay that covers the entire viewport.
      Teleporting to <body> is cleaner for z-index stacking in complex
      layouts, but this app uses a simple flex layout where a fixed overlay
      works correctly without Teleport. We avoid the complexity for now.

      Why backdrop-blur?
      Adds depth to the dark overlay without making it fully opaque. The
      user can see they are still in the app while the modal is open,
      which reduces disorientation.
    -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div
          v-if="showLogoutModal"
          class="fixed inset-0 z-50 flex items-end justify-center sm:items-center px-4 pb-6 sm:pb-0"
          style="background-color: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px);"
          role="dialog"
          aria-modal="true"
          aria-labelledby="logout-modal-title"
          @click.self="closeLogoutModal"
        >
          <!--
            Modal content card.

            Why items-end on mobile (sm:items-center on larger)?
            "Bottom sheet" pattern: on mobile, modals that require user
            choice feel more natural when they slide up from the bottom
            (one-thumb reachability). On tablet/desktop, center alignment
            is the expected convention.
          -->
          <div
            class="w-full max-w-sm rounded-2xl p-6 space-y-5"
            style="background-color: #1e293b; border: 1px solid rgba(51, 65, 85, 0.8);"
          >
            <!-- Modal heading -->
            <div class="space-y-2">
              <h2
                id="logout-modal-title"
                class="text-lg font-semibold text-dark-text-primary"
              >
                Cerrar sesión
              </h2>
              <p class="text-sm text-dark-text-secondary leading-relaxed">
                ¿Qué quieres hacer con tus datos locales?
              </p>
            </div>

            <!-- Option buttons -->
            <div class="space-y-3">
              <!--
                "Mantener en modo invitado" — logout(false)
                The user keeps their IndexedDB data and continues as a guest.
                Primary action: uses the accent-blue style to signal it's
                the "safer" / recommended choice.
              -->
              <button
                @click="handleLogoutKeepData"
                class="w-full flex flex-col items-start gap-0.5 px-4 py-3 rounded-xl
                       text-left transition-colors min-h-[60px]
                       hover:opacity-90"
                style="background-color: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #93c5fd;"
              >
                <span class="font-medium text-sm">Mantener en modo invitado</span>
                <span class="text-xs opacity-75">Tus datos permanecen en este dispositivo</span>
              </button>

              <!--
                "Borrar todo" — logout(true)
                Destructive: deletes WalletDB entirely. Uses red styling to
                signal this is irreversible. Placed second (below the safe
                option) to make it harder to accidentally tap.
              -->
              <button
                @click="handleLogoutDeleteAll"
                class="w-full flex flex-col items-start gap-0.5 px-4 py-3 rounded-xl
                       text-left transition-colors min-h-[60px]
                       hover:opacity-90"
                style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #fca5a5;"
              >
                <span class="font-medium text-sm">Borrar todo</span>
                <span class="text-xs opacity-75">Elimina todos los datos locales de este dispositivo</span>
              </button>

              <!-- Cancel -->
              <button
                @click="closeLogoutModal"
                class="w-full px-4 py-3 rounded-xl text-sm text-dark-text-secondary
                       hover:text-dark-text-primary transition-colors min-h-[44px]"
                style="background-color: rgba(51, 65, 85, 0.3);"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/**
 * Fade transition for the "Guardado" success indicator.
 *
 * Why 200ms?
 * Fast enough to feel snappy on mobile without being jarring.
 * Matches the general 200–300 ms animation budget used in the app.
 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 200ms ease-in-out;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/**
 * Modal overlay fade + slight scale for the bottom-sheet entrance.
 *
 * Why opacity + transform together?
 * Fading alone makes the modal appear/disappear flatly. Adding a subtle
 * scale (0.95 → 1.0) gives the modal a "pop" that feels more native on
 * mobile, matching the micro-interaction conventions of iOS/Android modals.
 *
 * Why 250ms?
 * Slightly slower than the 200ms fade for inline elements. Modals are
 * more visually significant — a tiny extra duration prevents them from
 * feeling too abrupt while still being fast enough for mobile.
 */
.modal-fade-enter-active {
  transition: opacity 250ms ease-out, transform 250ms ease-out;
}

.modal-fade-leave-active {
  transition: opacity 200ms ease-in, transform 200ms ease-in;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.modal-fade-enter-to,
.modal-fade-leave-from {
  opacity: 1;
  transform: scale(1);
}
</style>
