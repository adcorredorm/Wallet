<script setup lang="ts">
/**
 * Accounts Overview Component
 *
 * Shows all accounts with their balances in dashboard
 */

import { computed } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import { formatAccountType } from '@/utils/formatters'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import type { Account } from '@/types'

const exchangeRatesStore = useExchangeRatesStore()
const settingsStore = useSettingsStore()

interface AccountWithBalance extends Account {
  balance: number
}

interface Props {
  accounts: AccountWithBalance[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  'account-click': [account: Account]
}>()

const accountIcon = (type: string) => {
  const icons: Record<string, string> = {
    debit: '💳',
    credit: '💳',
    cash: '💵'
  }
  return icons[type] || '💰'
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold">Tus Cuentas</h2>
      <router-link
        to="/accounts"
        class="text-sm text-accent-blue hover:underline"
      >
        Ver todas
      </router-link>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-8">
      <div class="spinner w-8 h-8"></div>
    </div>

    <!-- Accounts list -->
    <div v-else-if="accounts.length > 0" class="space-y-3">
      <BaseCard
        v-for="account in accounts"
        :key="account.id"
        clickable
        @click="emit('account-click', account)"
      >
        <div class="flex items-center justify-between">
          <!-- Icon and name -->
          <div class="flex items-center gap-3">
            <span class="text-2xl">{{ accountIcon(account.type) }}</span>
            <div>
              <p class="font-medium">{{ account.name }}</p>
              <p class="text-sm text-dark-text-secondary">{{ formatAccountType(account.type) }} · {{ account.currency }}</p>
            </div>
          </div>

          <!-- Balance: native + converted -->
          <div class="text-right">
            <CurrencyDisplay
              :amount="account.balance || 0"
              :currency="account.currency"
              size="md"
              compact
            />
            <div
              v-if="account.currency !== settingsStore.primaryCurrency && exchangeRatesStore.rates.length > 0"
              class="text-xs text-dark-text-secondary mt-0.5"
            >
              ≈ <CurrencyDisplay
                :amount="exchangeRatesStore.convert(account.balance || 0, account.currency, settingsStore.primaryCurrency)"
                :currency="settingsStore.primaryCurrency"
                size="sm"
                compact
              />
            </div>
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- Empty state -->
    <BaseCard v-else>
      <div class="text-center py-6">
        <p class="text-4xl mb-2">💳</p>
        <p class="text-dark-text-secondary">No tienes cuentas aún</p>
        <router-link
          to="/accounts/new"
          class="inline-block mt-4 btn-primary"
        >
          Crear primera cuenta
        </router-link>
      </div>
    </BaseCard>
  </div>
</template>
