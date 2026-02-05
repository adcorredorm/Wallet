<script setup lang="ts">
/**
 * Accounts Overview Component
 *
 * Shows all accounts with their balances in dashboard
 */

import { computed } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import type { Account } from '@/types'

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

const accountIcon = (tipo: string) => {
  const icons: Record<string, string> = {
    debito: '💳',
    credito: '💳',
    efectivo: '💵'
  }
  return icons[tipo] || '💰'
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
            <span class="text-2xl">{{ accountIcon(account.tipo) }}</span>
            <div>
              <p class="font-medium">{{ account.nombre }}</p>
              <p class="text-sm text-dark-text-secondary">{{ account.divisa }} - Balance: {{ account.balance }}</p>
            </div>
          </div>

          <!-- Balance -->
          <CurrencyDisplay
            :amount="account.balance || 0"
            :currency="account.divisa"
            size="md"
            compact
          />
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
