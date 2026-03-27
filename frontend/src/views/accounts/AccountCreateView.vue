<script setup lang="ts">
/**
 * Account Create View
 *
 * Form to create a new account.
 *
 * Redirect: goes to /accounts on success, except during onboarding
 * (no accounts OR no categories yet) where it redirects to / so the
 * setup checklist guides the user to the next prerequisite.
 */

import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountsStore, useCategoriesStore, useUiStore } from '@/stores'
import AccountForm from '@/components/accounts/AccountForm.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { CreateAccountDto, UpdateAccountDto } from '@/types'

const router = useRouter()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const submitting = ref(false)

async function handleSubmit(data: CreateAccountDto | UpdateAccountDto) {
  submitting.value = true
  try {
    const isOnboarding = accountsStore.activeAccounts.length === 0 || categoriesStore.activeCategories.length === 0
    await accountsStore.createAccount(data as CreateAccountDto)
    uiStore.showSuccess('Cuenta creada exitosamente')
    router.push(isOnboarding ? '/' : '/accounts')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al crear cuenta')
  } finally {
    submitting.value = false
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
        :loading="submitting"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />
    </BaseCard>
  </div>
</template>
