<script setup lang="ts">
/**
 * Net Worth Card Component
 *
 * Displays total net worth (patrimonio neto)
 * Sum of all account balances
 */

import BaseCard from '@/components/ui/BaseCard.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'

interface Props {
  netWorth: number
  currency?: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  currency: 'USD',
  loading: false
})
</script>

<template>
  <BaseCard padding="lg">
    <div class="text-center">
      <!-- Label -->
      <p class="text-sm text-dark-text-secondary mb-2">
        Patrimonio Neto
      </p>

      <!-- Amount -->
      <div v-if="loading" class="flex justify-center">
        <div class="spinner w-8 h-8"></div>
      </div>
      <CurrencyDisplay
        v-else
        :amount="netWorth"
        :currency="currency"
        size="xl"
      />

      <!-- Emoji indicator -->
      <p class="text-4xl mt-4">
        {{ netWorth >= 0 ? '📈' : '📉' }}
      </p>
    </div>
  </BaseCard>
</template>
