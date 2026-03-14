<script setup lang="ts">
/**
 * Account List Component
 *
 * Displays list of accounts with loading and empty states
 */

import { computed } from 'vue'
import AccountCard from './AccountCard.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import type { Account } from '@/types'

interface Props {
  accounts: Account[]
  balances: Map<string, number>
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  'account-click': [account: Account]
  'create-click': []
}>()

const hasAccounts = computed(() => props.accounts.length > 0)

function getBalance(accountId: string): number {
  return props.balances.get(accountId) || 0
}
</script>

<template>
  <div>
    <!-- Loading state -->
    <BaseSpinner v-if="loading" centered />

    <!-- Empty state -->
    <EmptyState
      v-else-if="!hasAccounts"
      title="No tienes cuentas"
      message="Crea tu primera cuenta para comenzar a registrar tus movimientos financieros"
      icon="💳"
      action-text="Crear cuenta"
      @action="emit('create-click')"
    />

    <!-- Account list -->
    <div v-else class="space-y-3">
      <div
        v-for="account in accounts"
        :key="account.id"
        class="relative"
        :class="{ 'opacity-50': account.active === false }"
      >
        <AccountCard
          :account="account"
          :balance="getBalance(account.id)"
          @click="emit('account-click', account)"
        />
      </div>
    </div>
  </div>
</template>
