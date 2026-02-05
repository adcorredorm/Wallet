<script setup lang="ts">
/**
 * Account Edit View
 *
 * Form to edit existing account
 */

import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAccountsStore, useUiStore } from '@/stores'
import AccountForm from '@/components/accounts/AccountForm.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import type { UpdateAccountDto } from '@/types'

const route = useRoute()
const router = useRouter()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const accountId = route.params.id as string

const account = computed(() =>
  accountsStore.accounts.find(a => a.id === accountId)
)

onMounted(async () => {
  if (!account.value) {
    try {
      await accountsStore.fetchAccountById(accountId)
    } catch (error: any) {
      uiStore.showError(error.message || 'Error al cargar cuenta')
      router.push('/accounts')
    }
  }
})

async function handleSubmit(data: UpdateAccountDto) {
  try {
    await accountsStore.updateAccount(accountId, data)
    uiStore.showSuccess('Cuenta actualizada exitosamente')
    router.push(`/accounts/${accountId}`)
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al actualizar cuenta')
  }
}

function handleCancel() {
  router.back()
}
</script>

<template>
  <div v-if="account" class="space-y-6">
    <h1 class="text-2xl font-bold">Editar Cuenta</h1>

    <BaseCard>
      <AccountForm
        :account="account"
        :loading="accountsStore.loading"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
    </BaseCard>
  </div>

  <BaseSpinner v-else centered />
</template>
