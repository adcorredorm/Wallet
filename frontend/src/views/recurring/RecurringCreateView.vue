<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRecurringRulesStore } from '@/stores/recurringRules'
import { useAccountsStore } from '@/stores/accounts'
import { useCategoriesStore } from '@/stores/categories'
import { useUiStore } from '@/stores'
import RecurringRuleForm from '@/components/recurring/RecurringRuleForm.vue'
import type { CreateRecurringRuleDto, UpdateRecurringRuleDto } from '@/types/recurring-rule'

const router = useRouter()
const rulesStore = useRecurringRulesStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const loading = ref(false)

onMounted(async () => {
  await Promise.all([
    accountsStore.fetchAccounts(),
    categoriesStore.fetchCategories(),
  ])
})

async function handleSubmit(data: CreateRecurringRuleDto | UpdateRecurringRuleDto) {
  loading.value = true
  try {
    await rulesStore.createRule(data as CreateRecurringRuleDto)
    router.push('/recurring')
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al crear regla')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold">Nueva regla recurrente</h1>
    <RecurringRuleForm
      :accounts="accountsStore.accounts"
      :categories="categoriesStore.categories"
      :loading="loading"
      @submit="handleSubmit"
      @cancel="router.push('/recurring')"
    />
  </div>
</template>
