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
import { useSettingsStore } from '@/stores/settings'
import { useSyncStore } from '@/stores/sync'
import { syncManager } from '@/offline/sync-manager'
import { SUPPORTED_CURRENCIES } from '@/utils/constants'
import BaseSelect from '@/components/ui/BaseSelect.vue'

const settingsStore = useSettingsStore()
const syncStore = useSyncStore()

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
    <!-- Page heading -->
    <div>
      <h1 class="text-2xl font-bold text-dark-text-primary">Configuración</h1>
      <p class="mt-1 text-sm text-dark-text-secondary">
        Preferencias generales de la aplicación.
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
</style>
