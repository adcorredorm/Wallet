<script setup lang="ts">
/**
 * Account Card Component
 *
 * Displays account summary with balance.
 * Mobile-optimized card layout.
 *
 * Phase 4.1 — Dual balance display
 * When an account's currency differs from the user's primary currency, a
 * secondary line is rendered showing the approximate converted amount.
 *
 * Why show the converted balance here and not in the parent?
 * AccountCard is the canonical place where a balance is presented to the
 * user. Centralising the conversion here means every consumer of AccountCard
 * gets the dual-balance behaviour for free without any extra wiring.
 *
 * Guard: if exchangeRatesStore.rates.length === 0 we have no rates cached at
 * all. In that situation convert() would return the original amount unchanged,
 * which would look like a valid converted value but is actually meaningless.
 * We return null to suppress the secondary row rather than mislead the user.
 */

import { computed } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
// Phase 5: SyncBadge shows per-item sync state (pending / error dot)
import SyncBadge from '@/components/sync/SyncBadge.vue'
import { formatAccountType } from '@/utils/formatters'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import type { Account } from '@/types'
import type { LocalAccount } from '@/offline/types'

interface Props {
  /**
   * Why accept LocalAccount | Account?
   * The store exposes LocalAccount[] (extends Account with _sync_status).
   * Downstream consumers that don't use offline mode can still pass a plain
   * Account — the badge simply won't render because _sync_status will be
   * undefined, which the v-if check below handles gracefully.
   */
  account: LocalAccount | Account
  balance?: number
  clickable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  balance: 0,
  clickable: true
})

const emit = defineEmits<{
  click: []
}>()

// ---------------------------------------------------------------------------
// Store access
// ---------------------------------------------------------------------------

const exchangeRatesStore = useExchangeRatesStore()
const settingsStore = useSettingsStore()

// ---------------------------------------------------------------------------
// Account display helpers
// ---------------------------------------------------------------------------

const accountTypeLabel = computed(() => formatAccountType(props.account.type))

// Icon for account type
const accountIcon = computed(() => {
  const icons: Record<string, string> = {
    debit: '💳',
    credit: '💳',
    cash: '💵'
  }
  return icons[props.account.type] || '💰'
})

// ---------------------------------------------------------------------------
// Phase 4.1 — Dual balance (native currency + primary currency conversion)
// ---------------------------------------------------------------------------

/**
 * True when the account's currency differs from the user's primary currency.
 *
 * Why computed instead of an inline v-if expression?
 * Both showConvertedBalance and convertedBalance depend on the same
 * comparison. Hoisting it into a named computed avoids duplicating the logic
 * and makes the template easier to read.
 */
const showConvertedBalance = computed(
  () => props.account.currency !== settingsStore.primaryCurrency
)

/**
 * The balance converted to the user's primary currency, or null when:
 *   - the account currency already IS the primary currency (handled by
 *     showConvertedBalance, but we also short-circuit here for safety), OR
 *   - no exchange rates are cached (rates.length === 0) — in that case
 *     convert() would silently return the original amount, which would
 *     appear as a valid conversion but is actually meaningless. We return
 *     null so the template suppresses the row entirely.
 *
 * Type is explicitly number | null so the template v-if correctly narrows
 * to number before passing to CurrencyDisplay.
 */
const convertedBalance = computed<number | null>(() => {
  if (!showConvertedBalance.value) return null
  if (exchangeRatesStore.rates.length === 0) return null

  return exchangeRatesStore.convert(
    props.balance,
    props.account.currency,
    settingsStore.primaryCurrency
  )
})
</script>

<template>
  <BaseCard :clickable="clickable" @click="emit('click')">
    <div class="flex items-center justify-between">
      <!-- Left: Icon and info -->
      <div class="flex items-center gap-3 flex-1 min-w-0">
        <!-- Icon -->
        <div class="text-3xl flex-shrink-0">
          {{ accountIcon }}
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <!--
            Why flex + items-center on the title row?
            We need the account name and the SyncBadge dot to sit on the same
            baseline. flex + items-center achieves this without a table layout.
            gap-2 (8px) ensures the dot has breathing room from the name text.
          -->
          <div class="flex items-center gap-2">
            <h3 class="font-semibold truncate">
              {{ account.name }}
            </h3>
            <!--
              SyncBadge is only rendered when the account has a _sync_status
              field (i.e. it is a LocalAccount from the offline-first store).
              The 'in' operator checks for the key's existence at runtime.
              This makes AccountCard safe to use with plain Account objects too.
            -->
            <SyncBadge
              v-if="'_sync_status' in account"
              :status="(account as LocalAccount)._sync_status"
            />
          </div>
          <p class="text-sm text-dark-text-secondary">
            {{ accountTypeLabel }} • {{ account.currency }}
          </p>
        </div>
      </div>

      <!-- Right: Balance (native + optional primary-currency conversion) -->
      <div class="flex-shrink-0 text-right ml-3">
        <CurrencyDisplay
          :amount="balance"
          :currency="account.currency"
          size="lg"
          compact
        />
        <!--
          Secondary balance: shown only when the account currency differs from
          the user's primary currency AND exchange rates are cached.

          Why mt-0.5 (2px) instead of mt-1 (4px)?
          The secondary line is visually subordinate — it is explanatory text,
          not a peer element. A 2px gap keeps it visually attached to the
          primary balance above it, making them read as a unit rather than
          two independent lines. 4px would create enough separation that the
          eye reads them as separate rows, which conflicts with the intent.

          Why text-xs + text-gray-400?
          text-xs (12px) clearly communicates lower visual hierarchy than the
          lg-size primary balance. text-gray-400 / dark:text-gray-500 matches
          the muted secondary text convention used throughout this codebase
          (see accountTypeLabel line above) and maintains WCAG AA contrast
          against both the card background (#1e293b) and mobile dark surfaces.
        -->
        <div
          v-if="showConvertedBalance && convertedBalance !== null"
          class="text-xs text-gray-400 dark:text-gray-500 mt-0.5"
        >
          ≈ <CurrencyDisplay
            :amount="convertedBalance"
            :currency="settingsStore.primaryCurrency"
            size="sm"
          />
        </div>
      </div>
    </div>

    <!-- Tags (if any) -->
    <div v-if="account.tags && account.tags.length > 0" class="flex gap-2 mt-3">
      <span
        v-for="tag in account.tags.slice(0, 3)"
        :key="tag"
        class="badge badge-primary text-xs"
      >
        {{ tag }}
      </span>
      <span v-if="account.tags.length > 3" class="text-xs text-dark-text-tertiary">
        +{{ account.tags.length - 3 }}
      </span>
    </div>
  </BaseCard>
</template>
