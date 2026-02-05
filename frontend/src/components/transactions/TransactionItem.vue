<script setup lang="ts">
/**
 * Transaction Item Component
 *
 * Single transaction display in list
 * Mobile-optimized with touch actions
 */

import { computed } from 'vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { formatDateRelative } from '@/utils/formatters'
import type { Transaction } from '@/types'

interface Props {
  transaction: Transaction
  showAccount?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showAccount: true
})

const emit = defineEmits<{
  click: []
}>()

const isIncome = computed(() => props.transaction.tipo === 'ingreso')

const amountColor = computed(() => {
  return isIncome.value ? 'text-accent-green' : 'text-accent-red'
})

const formattedDate = computed(() => formatDateRelative(props.transaction.fecha))

const categoryIcon = computed(() => props.transaction.categoria?.icono || '📝')
const categoryName = computed(() => props.transaction.categoria?.nombre || 'Sin categoría')
const accountName = computed(() => props.transaction.cuenta?.nombre || 'Cuenta')
const currency = computed(() => props.transaction.cuenta?.divisa || 'USD')
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
      <!-- Title or category name -->
      <h4 class="font-medium truncate">
        {{ transaction.titulo || categoryName }}
      </h4>

      <!-- Account and date -->
      <div class="flex items-center gap-2 text-sm text-dark-text-secondary">
        <span v-if="showAccount">{{ accountName }}</span>
        <span v-if="showAccount">•</span>
        <span>{{ formattedDate }}</span>
      </div>

      <!-- Category (if title exists) -->
      <p v-if="transaction.titulo" class="text-xs text-dark-text-tertiary mt-1">
        {{ categoryName }}
      </p>
    </div>

    <!-- Amount -->
    <div class="flex-shrink-0 text-right">
      <CurrencyDisplay
        :amount="isIncome ? transaction.monto : -transaction.monto"
        :currency="currency"
        size="md"
        show-sign
        :class="amountColor"
      />
    </div>
  </div>
</template>
