<script setup lang="ts">
/**
 * Account Detail View
 *
 * Shows account details and transactions
 */

import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAccountsStore, useTransactionsStore, useUiStore } from '@/stores'
import { useExchangeRatesStore } from '@/stores/exchangeRates'
import { useSettingsStore } from '@/stores/settings'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import CurrencyDisplay from '@/components/shared/CurrencyDisplay.vue'
import TransactionList from '@/components/transactions/TransactionList.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import { formatAccountType } from '@/utils/formatters'

const route = useRoute()
const router = useRouter()
const accountsStore = useAccountsStore()
const transactionsStore = useTransactionsStore()
const uiStore = useUiStore()
const exchangeRatesStore = useExchangeRatesStore()
const settingsStore = useSettingsStore()

const accountId = route.params.id as string
const showDeleteDialog = ref(false)
const deleting = ref(false)

const account = computed(() =>
  accountsStore.accounts.find(a => a.id === accountId)
)

const balance = computed(() =>
  accountsStore.getAccountBalance(accountId)
)

const transactions = computed(() =>
  transactionsStore.getTransactionsByAccount(accountId)
)

onMounted(async () => {
  try {
    await Promise.all([
      accountsStore.fetchAccountById(accountId),
      transactionsStore.fetchByAccount(accountId)
    ])
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al cargar cuenta')
    router.push('/accounts')
  }
})

function editAccount() {
  router.push(`/accounts/${accountId}/edit`)
}

async function confirmDelete() {
  deleting.value = true
  try {
    await accountsStore.deleteAccount(accountId)
    uiStore.showSuccess('Cuenta eliminada exitosamente')
    router.push('/accounts')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al eliminar cuenta')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}

function goToTransaction(transaction: any) {
  router.push(`/transactions/${transaction.id}/edit`)
}
</script>

<template>
  <div v-if="account" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">{{ account.name }}</h1>
      <div class="flex gap-2">
        <BaseButton variant="secondary" size="sm" @click="editAccount">
          Editar
        </BaseButton>
        <BaseButton variant="danger" size="sm" @click="showDeleteDialog = true">
          Eliminar
        </BaseButton>
      </div>
    </div>

    <!-- Account Info Card -->
    <BaseCard>
      <div class="space-y-4">
        <!-- Balance -->
        <div class="text-center py-4">
          <p class="text-sm text-dark-text-secondary mb-2">Balance actual</p>
          <CurrencyDisplay
            :amount="balance"
            :currency="account.currency"
            size="xl"
          />
          <div
            v-if="account.currency !== settingsStore.primaryCurrency && exchangeRatesStore.rates.length > 0"
            class="text-sm text-dark-text-secondary mt-1"
          >
            ≈ <CurrencyDisplay
              :amount="exchangeRatesStore.convert(balance, account.currency, settingsStore.primaryCurrency)"
              :currency="settingsStore.primaryCurrency"
              size="md"
              compact
            />
          </div>
        </div>

        <div class="divider"></div>

        <!-- Details -->
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-dark-text-secondary">Tipo</p>
            <p class="font-medium">{{ formatAccountType(account.type) }}</p>
          </div>
          <div>
            <p class="text-dark-text-secondary">Divisa</p>
            <p class="font-medium">{{ account.currency }}</p>
          </div>
        </div>

        <!-- Description -->
        <div v-if="account.description" class="text-sm">
          <p class="text-dark-text-secondary">Descripción</p>
          <p>{{ account.description }}</p>
        </div>

        <!-- Tags -->
        <div v-if="account.tags && account.tags.length > 0">
          <p class="text-sm text-dark-text-secondary mb-2">Etiquetas</p>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="tag in account.tags"
              :key="tag"
              class="badge badge-primary"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- Transactions -->
    <div>
      <h2 class="text-lg font-semibold mb-4">Transacciones</h2>
      <TransactionList
        :transactions="transactions"
        :loading="transactionsStore.loading"
        :show-account="false"
        @transaction-click="goToTransaction"
      />
    </div>

    <!-- Delete confirmation dialog -->
    <ConfirmDialog
      :show="showDeleteDialog"
      title="Eliminar cuenta"
      :message="`¿Estás seguro de que deseas eliminar la cuenta '${account.name}'? Esta acción no se puede deshacer.`"
      confirm-text="Eliminar"
      :loading="deleting"
      @confirm="confirmDelete"
      @cancel="showDeleteDialog = false"
    />
  </div>

  <!-- Loading state -->
  <BaseSpinner v-else centered />
</template>
