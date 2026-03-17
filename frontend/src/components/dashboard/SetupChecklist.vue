<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountsStore, useCategoriesStore } from '@/stores'

const router = useRouter()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()

const hasAccounts = computed(() => accountsStore.activeAccounts.length > 0)
const hasCategories = computed(() => categoriesStore.activeCategories.length > 0)
const bothDone = computed(() => hasAccounts.value && hasCategories.value)

const title = computed(() =>
  !hasAccounts.value && !hasCategories.value
    ? 'Configura tu wallet'
    : 'Un paso más'
)
</script>

<template>
  <div class="bg-dark-bg-secondary rounded-xl p-4">
    <div class="text-center mb-4">
      <div class="text-3xl mb-2">🚀</div>
      <h3 class="text-base font-semibold text-dark-text-primary">{{ title }}</h3>
      <p class="text-xs text-dark-text-secondary mt-1">
        {{ bothDone ? 'Listo para crear transacciones' : 'Completa estos pasos para comenzar' }}
      </p>
    </div>

    <!-- Account row -->
    <div
      class="bg-dark-bg-primary rounded-lg px-3 py-2.5 mb-2 flex items-center gap-3"
      :class="{ 'opacity-50': hasAccounts }"
    >
      <div
        class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-sm"
        :class="hasAccounts ? 'bg-accent-green text-white' : 'border-2 border-dark-border text-dark-text-secondary'"
      >
        <span v-if="hasAccounts" data-testid="account-done">✓</span>
        <span v-else>💳</span>
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium" :class="hasAccounts ? 'line-through text-dark-text-secondary' : 'text-dark-text-primary'">
          Crea tu primera cuenta
        </p>
        <p v-if="!hasAccounts" class="text-xs text-dark-text-secondary">Bancaria, tarjeta o efectivo</p>
      </div>
      <button
        v-if="!hasAccounts"
        data-testid="account-create-btn"
        class="btn-primary text-xs px-3 py-1.5 flex-shrink-0"
        @click="router.push('/accounts/new')"
      >
        Crear →
      </button>
    </div>

    <!-- Category row -->
    <div
      class="bg-dark-bg-primary rounded-lg px-3 py-2.5 flex items-center gap-3"
      :class="{ 'opacity-50': hasCategories }"
    >
      <div
        class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-sm"
        :class="hasCategories ? 'bg-accent-green text-white' : 'border-2 border-dark-border text-dark-text-secondary'"
      >
        <span v-if="hasCategories" data-testid="category-done">✓</span>
        <span v-else>🏷️</span>
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium" :class="hasCategories ? 'line-through text-dark-text-secondary' : 'text-dark-text-primary'">
          Crea tu primera categoría
        </p>
        <p v-if="!hasCategories" class="text-xs text-dark-text-secondary">Para organizar tus gastos e ingresos</p>
      </div>
      <button
        v-if="!hasCategories"
        data-testid="category-create-btn"
        class="btn-primary text-xs px-3 py-1.5 flex-shrink-0"
        @click="router.push('/categories/new')"
      >
        Crear →
      </button>
    </div>
  </div>
</template>
