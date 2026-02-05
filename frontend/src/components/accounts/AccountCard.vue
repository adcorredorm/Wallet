<script setup lang="ts">
/**
 * Account Card Component
 *
 * Displays account summary with balance
 * Mobile-optimized card layout
 */

import { computed } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { formatAccountType } from '@/utils/formatters'
import type { Account } from '@/types'

interface Props {
  account: Account
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

const accountTypeLabel = computed(() => formatAccountType(props.account.tipo))

// Icon for account type
const accountIcon = computed(() => {
  const icons: Record<string, string> = {
    debito: '💳',
    credito: '💳',
    efectivo: '💵'
  }
  return icons[props.account.tipo] || '💰'
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
          <h3 class="font-semibold truncate">
            {{ account.nombre }}
          </h3>
          <p class="text-sm text-dark-text-secondary">
            {{ accountTypeLabel }} • {{ account.divisa }}
          </p>
        </div>
      </div>

      <!-- Right: Balance -->
      <div class="flex-shrink-0 text-right ml-3">
        <CurrencyDisplay
          :amount="balance"
          :currency="account.divisa"
          size="lg"
          compact
        />
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
