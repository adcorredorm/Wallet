<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRecurringRulesStore } from '@/stores/recurringRules'
import { useAccountsStore } from '@/stores/accounts'
import { useCategoriesStore } from '@/stores/categories'
import { useUiStore } from '@/stores'
import RecurringRuleForm from '@/components/recurring/RecurringRuleForm.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import type { UpdateRecurringRuleDto } from '@/types/recurring-rule'

const route = useRoute()
const router = useRouter()
const rulesStore = useRecurringRulesStore()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const ruleId = route.params.id as string
const loading = ref(false)
const initialLoading = ref(true)

const rule = computed(() => rulesStore.rules.find(r => r.id === ruleId))

onMounted(async () => {
  try {
    await Promise.all([
      rulesStore.loadRules(),
      accountsStore.fetchAccounts(),
      categoriesStore.fetchCategories(),
    ])
  } finally {
    initialLoading.value = false
  }
})

async function handleSubmit(data: UpdateRecurringRuleDto) {
  loading.value = true
  try {
    await rulesStore.updateRule(ruleId, data)
    router.push(`/recurring/${ruleId}`)
  } catch (err: any) {
    uiStore.showError(err.message || 'Error al guardar cambios')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold">Editar regla recurrente</h1>

    <BaseSpinner v-if="initialLoading" centered />

    <div v-else-if="!rule" class="text-center py-12 text-dark-text-secondary">
      Regla no encontrada
    </div>

    <RecurringRuleForm
      v-else
      :rule="rule"
      :accounts="accountsStore.accounts"
      :categories="categoriesStore.categories"
      :loading="loading"
      @submit="handleSubmit"
      @cancel="router.push(`/recurring/${ruleId}`)"
    />
  </div>
</template>
