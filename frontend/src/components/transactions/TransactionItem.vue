<script setup lang="ts">
/**
 * Transaction Item Component
 *
 * Single transaction display in list
 * Mobile-optimized with touch actions
 */

import { computed } from 'vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
// Phase 5: SyncBadge shows per-item sync state (pending / error dot)
import SyncBadge from '@/components/sync/SyncBadge.vue'
import { formatDateRelative } from '@/utils/formatters'
import type { Transaction } from '@/types'
import type { LocalTransaction } from '@/offline/types'
import { useCategoriesStore } from '@/stores/categories'

interface Props {
  /**
   * Accept either the plain server type or the offline-enriched LocalTransaction.
   * The badge only renders when _sync_status is present on the object.
   */
  transaction: LocalTransaction | Transaction
  showAccount?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showAccount: true
})

const emit = defineEmits<{
  click: []
}>()

const categoriesStore = useCategoriesStore()

const isIncome = computed(() => props.transaction.type === 'income')

const amountColor = computed(() => {
  return isIncome.value ? 'text-accent-green' : 'text-accent-red'
})

const formattedDate = computed(() => formatDateRelative(props.transaction.date))

// Transactions synced from server carry a nested category object.
// Pending offline transactions only have category_id — fall back to the
// categories store so newly created transactions display correctly before sync.
const resolvedCategory = computed(() =>
  props.transaction.category
    ?? categoriesStore.categories.find(c => c.id === props.transaction.category_id)
)
const categoryIcon = computed(() => resolvedCategory.value?.icon || '📝')
const categoryName = computed(() => resolvedCategory.value?.name || 'Sin categoría')
const accountName = computed(() => props.transaction.account?.name || 'Cuenta')
const currency = computed(() => props.transaction.account?.currency || 'USD')

/**
 * Whether this transaction carries foreign-currency metadata.
 *
 * Why narrow with 'original_currency' in check?
 * original_currency only exists on LocalTransaction, not on the plain
 * Transaction server type. The `in` operator narrows the union so
 * TypeScript lets us safely read the field without a cast.
 */
const hasForeignCurrency = computed(() => {
  if (!('original_currency' in props.transaction)) return false
  const local = props.transaction as LocalTransaction
  return !!local.original_currency && local.original_currency !== currency.value
})

/**
 * Exchange rate formatted without trailing zeros.
 *
 * Why toFixed(10) then parseFloat then toString?
 * exchange_rate is a floating-point number. toFixed(10) eliminates
 * floating-point noise beyond 10 decimal places, parseFloat strips
 * trailing zeros, and toString() returns a clean human-readable string
 * (e.g. 4000, 1.25, 3850.75) without scientific notation for normal
 * exchange-rate magnitudes.
 */
const formattedExchangeRate = computed(() => {
  if (!('exchange_rate' in props.transaction)) return ''
  const local = props.transaction as LocalTransaction
  if (!local.exchange_rate) return ''
  return parseFloat(Number(local.exchange_rate).toFixed(10)).toString()
})
</script>

<template>
  <div
    class="flex items-center gap-3 p-4 bg-dark-bg-secondary rounded-lg cursor-pointer hover:bg-dark-bg-tertiary transition-colors active:scale-[0.98]"
    @click="emit('click')"
  >
    <!-- Category icon -->
    <div class="flex-shrink-0 text-2xl">
      {{ categoryIcon }}
    </div>

    <!-- Info -->
    <div class="flex-1 min-w-0">
      <!-- Title or category name + sync badge -->
      <div class="flex items-center gap-2">
        <h4 class="font-medium truncate">
          {{ transaction.title || categoryName }}
        </h4>
        <!--
          Same runtime check as AccountCard: only render the badge if this
          transaction came from the offline-first store (has _sync_status).
        -->
        <SyncBadge
          v-if="'_sync_status' in transaction"
          :status="(transaction as LocalTransaction)._sync_status"
        />
      </div>

      <!-- Account and date -->
      <div class="flex items-center gap-2 text-sm text-dark-text-secondary">
        <span v-if="showAccount">{{ accountName }}</span>
        <span v-if="showAccount">•</span>
        <span>{{ formattedDate }}</span>
      </div>

      <!-- Category (if title exists) -->
      <p v-if="transaction.title" class="text-xs text-dark-text-tertiary mt-1">
        {{ categoryName }}
      </p>
    </div>

    <!-- Amount -->
    <div class="flex-shrink-0 text-right">
      <CurrencyDisplay
        :amount="isIncome ? transaction.amount : -transaction.amount"
        :currency="currency"
        size="md"
        show-sign
        :class="amountColor"
      />
      <!--
        Phase 5.5: Foreign-currency metadata line.

        Why only when original_currency !== account currency?
        If they match the conversion is trivial (1:1) and the line
        would be redundant noise. We only surface it when the user
        actually transacted in a different currency.

        Layout: inline-flex keeps the three segments on one line on
        most mobile widths. On very narrow screens (320px) text-xs
        (~12px) plus the compact format from CurrencyDisplay fits
        without wrapping in the vast majority of real exchange-rate
        values.
      -->
      <div
        v-if="hasForeignCurrency"
        class="flex items-center justify-end gap-0.5 text-xs text-gray-400 dark:text-gray-500 mt-0.5"
      >
        <CurrencyDisplay
          :amount="(transaction as LocalTransaction).original_amount!"
          :currency="(transaction as LocalTransaction).original_currency!"
          size="sm"
        />
        <span class="mx-1">@</span>
        <span>{{ formattedExchangeRate }}</span>
      </div>
    </div>
  </div>
</template>
