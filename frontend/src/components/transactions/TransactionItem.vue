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

const isIncome = computed(() => props.transaction.type === 'income')

const amountColor = computed(() => {
  return isIncome.value ? 'text-accent-green' : 'text-accent-red'
})

const formattedDate = computed(() => formatDateRelative(props.transaction.date))

const categoryIcon = computed(() => props.transaction.category?.icon || '📝')
const categoryName = computed(() => props.transaction.category?.name || 'Sin categoría')
const accountName = computed(() => props.transaction.account?.name || 'Cuenta')
const currency = computed(() => props.transaction.account?.currency || 'USD')
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
    </div>
  </div>
</template>
