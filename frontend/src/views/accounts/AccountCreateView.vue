<script setup lang="ts">
/**
 * Account Create View
 *
 * Form to create a new account
 */

import { useRouter } from 'vue-router'
import { useAccountsStore, useUiStore } from '@/stores'
import AccountForm from '@/components/accounts/AccountForm.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { CreateAccountDto } from '@/types'

const router = useRouter()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

async function handleSubmit(data: CreateAccountDto) {
  try {
    await accountsStore.createAccount(data)
    uiStore.showSuccess('Cuenta creada exitosamente')
    router.push('/accounts')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al crear cuenta')
  }
}

function handleCancel() {
  router.back()
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold">Nueva Cuenta</h1>

    <BaseCard>
      <AccountForm
        :loading="accountsStore.loading"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
    </BaseCard>
  </div>
</template>
