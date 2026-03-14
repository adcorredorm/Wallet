<script setup lang="ts">
/**
 * Account Detail View
 *
 * Shows account details and transactions.
 * Archive/hard-delete/restore pattern replaces the previous single Eliminar button.
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
import { db } from '@/offline'

const route = useRoute()
const router = useRouter()
const accountsStore = useAccountsStore()
const transactionsStore = useTransactionsStore()
const uiStore = useUiStore()
const exchangeRatesStore = useExchangeRatesStore()
const settingsStore = useSettingsStore()

const accountId = route.params.id as string

// Dialog visibility refs — one per action type
const showArchiveDialog = ref(false)
const showDeleteDialog = ref(false)

// Loading refs — tracked independently so each button shows its own spinner
const archiving = ref(false)
const deleting = ref(false)

// Whether this account has any transactions or transfers.
// Computed async on mount; hard-delete is disabled until this resolves (false by default
// keeps the button disabled until we know it is safe to enable).
const hasMovements = ref(true)

const account = computed(() =>
  accountsStore.accounts.find(a => a.id === accountId)
)

const isArchived = computed(() => account.value?.active === false)

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
    return
  }

  // Check for movements so we can enable/disable the hard-delete button.
  // We query IndexedDB directly — same approach the store's hardDeleteAccount uses —
  // so the check is consistent with the guard inside the store action.
  try {
    const txCount = await db.transactions.where('account_id').equals(accountId).count()
    const transferFromCount = await db.transfers.where('source_account_id').equals(accountId).count()
    const transferToCount = await db.transfers.where('destination_account_id').equals(accountId).count()
    hasMovements.value = txCount + transferFromCount + transferToCount > 0
  } catch {
    // On error leave hasMovements = true so the button stays disabled (safe default)
  }
})

function editAccount() {
  router.push(`/accounts/${accountId}/edit`)
}

async function confirmArchive() {
  archiving.value = true
  try {
    await accountsStore.archiveAccount(accountId)
    uiStore.showSuccess('Cuenta archivada exitosamente')
    router.push('/accounts')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al archivar cuenta')
  } finally {
    archiving.value = false
    showArchiveDialog.value = false
  }
}

async function confirmHardDelete() {
  deleting.value = true
  try {
    await accountsStore.hardDeleteAccount(accountId)
    uiStore.showSuccess('Cuenta eliminada permanentemente')
    router.push('/accounts')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al eliminar cuenta')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}

async function restoreAccount() {
  try {
    await accountsStore.restoreAccount(accountId)
    uiStore.showSuccess('Cuenta activada exitosamente')
    // Stay on the page — the account becomes active again, the badge disappears
    // and the archive/delete buttons reappear.
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al activar cuenta')
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
      <div class="flex items-center gap-2 min-w-0">
        <h1 class="text-2xl font-bold truncate">{{ account.name }}</h1>
        <!-- Archived badge — visible only when account is archived -->
        <span
          v-if="isArchived"
          class="text-xs text-gray-400 dark:text-gray-500 shrink-0"
        >
          Archivada
        </span>
      </div>

      <div class="flex gap-2 shrink-0">
        <!-- Edit button — always visible -->
        <BaseButton variant="secondary" size="sm" @click="editAccount">
          Editar
        </BaseButton>

        <!-- Active account: show Archive + Hard Delete buttons -->
        <template v-if="!isArchived">
          <!-- Archive button — always enabled for active accounts -->
          <BaseButton
            variant="secondary"
            size="sm"
            :loading="archiving"
            @click="showArchiveDialog = true"
          >
            Archivar
          </BaseButton>

          <!-- Hard delete: wrap in a span to show tooltip even when button is disabled.
               Why a wrapper span? The HTML spec prevents pointer events (including hover
               that triggers title tooltips) on disabled buttons. A wrapper span
               re-enables the hover surface for the tooltip without re-enabling the button. -->
          <span
            v-if="hasMovements"
            :title="'No se puede borrar una cuenta con movimientos. Usa Archivar.'"
            class="inline-flex"
          >
            <BaseButton
              variant="danger"
              size="sm"
              :disabled="true"
              class="opacity-50 cursor-not-allowed"
            >
              Borrar permanentemente
            </BaseButton>
          </span>
          <BaseButton
            v-else
            variant="danger"
            size="sm"
            :loading="deleting"
            @click="showDeleteDialog = true"
          >
            Borrar permanentemente
          </BaseButton>
        </template>

        <!-- Archived account: show single Activar button -->
        <BaseButton
          v-else
          variant="primary"
          size="sm"
          :loading="accountsStore.loading"
          @click="restoreAccount"
        >
          Activar
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

    <!-- Archive confirmation dialog -->
    <ConfirmDialog
      :show="showArchiveDialog"
      variant="warning"
      title="Archivar cuenta"
      message="¿Archivar esta cuenta? La cuenta dejará de aparecer en tus balances y en el dashboard, pero todos tus movimientos anteriores (transacciones y transferencias) se conservarán intactos en el historial."
      confirm-text="Archivar"
      :loading="archiving"
      @confirm="confirmArchive"
      @cancel="showArchiveDialog = false"
    />

    <!-- Hard delete confirmation dialog -->
    <ConfirmDialog
      :show="showDeleteDialog"
      variant="danger"
      title="Borrar permanentemente"
      message="¿Borrar esta cuenta permanentemente? Esta acción no se puede deshacer."
      confirm-text="Borrar"
      :loading="deleting"
      @confirm="confirmHardDelete"
      @cancel="showDeleteDialog = false"
    />
  </div>

  <!-- Loading state -->
  <BaseSpinner v-else centered />
</template>
