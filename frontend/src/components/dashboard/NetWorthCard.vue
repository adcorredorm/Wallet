<script setup lang="ts">
/**
 * Net Worth Card Component
 *
 * Multi-currency net worth display.
 *
 * Why does this component own the store connections instead of receiving
 * netWorth as a prop?
 * The parent (DashboardView) used to pass a naive sum of all account balances
 * in mixed currencies. That number is meaningless when accounts hold different
 * currencies. The conversion logic (exchange rates, primary currency) belongs
 * here, not scattered across every caller.
 *
 * Headline strategy:
 *   - convertedNetWorth is null  → rates not available yet; show breakdown only.
 *   - convertedNetWorth is a number → show as the main headline in primaryCurrency.
 *
 * Per-currency breakdown:
 *   Always shown below the headline (or alone when no rates are available).
 *   Format: "USD: $1,200 · EUR: €800 · COP: $5,000,000"
 *   A ⚠ icon is shown next to any currency whose rate is missing, with a
 *   tooltip "Tasa de cambio no disponible".
 *
 * Reactivity:
 *   All three computed properties depend on accountsStore.accountsWithBalances,
 *   exchangeRatesStore.rates, and settingsStore.primaryCurrency. Vue tracks
 *   these dependencies automatically — no manual watchers needed.
 */

import { computed } from 'vue'
import { useAccountsStore } from '@/stores/accounts'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import BaseCard from '@/components/ui/BaseCard.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { EyeIcon, EyeSlashIcon } from '@heroicons/vue/24/outline'

// ── Props ──────────────────────────────────────────────────────────────────
// Why keep loading as a prop?
// The parent (DashboardView) orchestrates the fetch lifecycle and sets loading
// during the initial IndexedDB read. The component does not call fetchAccounts
// itself, so it cannot know when that async work starts or ends.
interface Props {
  loading?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: false
})

// ── Stores ─────────────────────────────────────────────────────────────────
const accountsStore = useAccountsStore()
const exchangeRatesStore = useExchangeRatesStore()
const settingsStore = useSettingsStore()

// ── Computed: balances grouped by currency ─────────────────────────────────
// Why Map<string, number> instead of a plain object?
// Map guarantees insertion-order iteration, which produces a stable breakdown
// list order in the template. It also avoids the prototype-pollution risk
// of using plain objects as dictionaries.
const balancesByCurrency = computed(() => {
  const map = new Map<string, number>()
  for (const account of accountsStore.accountsWithBalances) {
    const curr = account.currency
    if (!curr) continue
    map.set(curr, (map.get(curr) ?? 0) + account.balance)
  }
  return map
})

// ── Computed: total net worth converted to primary currency ────────────────
// Returns null when no rates are cached at all (first cold start with no
// network). In that case the breakdown list is the only thing we can show.
// Returns a number (possibly 0 or negative) once at least one rate exists.
//
// Why check rates.length === 0 as the null-guard?
// exchangeRatesStore.convert() degrades gracefully (returns the original
// amount) when a rate is missing. If rates is completely empty we cannot
// convert any amount reliably, so null signals "unavailable" to the template.
const convertedNetWorth = computed<number | null>(() => {
  if (exchangeRatesStore.rates.length === 0) return null
  let total = 0
  for (const [currency, balance] of balancesByCurrency.value) {
    total += exchangeRatesStore.convert(balance, currency, settingsStore.primaryCurrency)
  }
  return total
})

</script>

<template>
  <BaseCard padding="lg">
    <div class="text-center">
      <!-- Label with privacy toggle -->
      <div class="flex items-center justify-center gap-1.5 mb-2">
        <p class="text-sm text-dark-text-secondary">
          Patrimonio Neto
        </p>
        <button
          class="text-dark-text-tertiary hover:text-dark-text-secondary transition-colors"
          aria-label="Ocultar saldos"
          @click="settingsStore.toggleHideBalances()"
        >
          <EyeSlashIcon v-if="settingsStore.hideBalances" class="w-4 h-4" />
          <EyeIcon v-else class="w-4 h-4" />
        </button>
      </div>

      <!-- Loading spinner -->
      <div v-if="loading" class="flex justify-center">
        <div class="spinner w-8 h-8"></div>
      </div>

      <template v-else>
        <!-- Hidden state: masked placeholder -->
        <p
          v-if="settingsStore.hideBalances"
          class="text-2xl font-bold text-dark-text-tertiary tracking-widest"
        >
          &bull; &bull; &bull; &bull; &bull;
        </p>

        <!-- Visible state: converted total in primary currency -->
        <CurrencyDisplay
          v-else-if="convertedNetWorth !== null"
          :amount="convertedNetWorth"
          :currency="settingsStore.primaryCurrency"
          size="xl"
          :colorize="true"
        />

        <!-- No-rates notice -->
        <p
          v-if="!settingsStore.hideBalances && convertedNetWorth === null && balancesByCurrency.size > 1"
          class="mt-2 text-xs text-dark-text-secondary italic"
        >
          Total sin convertir — tasas no disponibles
        </p>
      </template>
    </div>
  </BaseCard>
</template>
