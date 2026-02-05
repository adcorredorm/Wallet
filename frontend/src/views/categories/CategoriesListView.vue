<script setup lang="ts">
/**
 * Categories List View
 *
 * Shows all categories for management
 */

import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoriesStore, useUiStore } from '@/stores'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'
import { formatCategoryType } from '@/utils/formatters'

const router = useRouter()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const categories = computed(() => categoriesStore.categories)

onMounted(async () => {
  // Always try to fetch categories when mounting this view
  // Even if App.vue already fetched them, we want fresh data
  try {
    await categoriesStore.fetchCategories()
  } catch (error: any) {
    console.error('Error loading categories in CategoriesListView:', error)
    uiStore.showError(error.message || 'Error al cargar categorías')
  }
})

function goToCategory(category: any) {
  router.push(`/categories/${category.id}/edit`)
}

function createCategory() {
  router.push('/categories/new')
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold">Categorías</h1>
    </div>

    <!-- Loading -->
    <BaseSpinner v-if="categoriesStore.loading" centered />

    <!-- Error state -->
    <EmptyState
      v-else-if="categoriesStore.error"
      title="Error al cargar"
      :message="categoriesStore.error"
      icon="⚠️"
      action-text="Reintentar"
      @action="() => categoriesStore.fetchCategories()"
    />

    <!-- Empty state -->
    <EmptyState
      v-else-if="categories.length === 0"
      title="No hay categorías"
      message="Las categorías ayudan a organizar tus ingresos y gastos"
      icon="🏷️"
      action-text="Nueva categoría"
      @action="createCategory"
    />

    <!-- Category list -->
    <div v-else class="grid gap-3 md:grid-cols-2">
      <BaseCard
        v-for="category in categories"
        :key="category.id"
        clickable
        @click="goToCategory(category)"
      >
        <div class="flex items-center gap-3">
          <!-- Icon -->
          <div class="text-2xl flex-shrink-0">
            {{ category.icono || '📁' }}
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <h4 class="font-medium truncate">{{ category.nombre }}</h4>
            <p class="text-sm text-dark-text-secondary">
              {{ formatCategoryType(category.tipo) }}
            </p>
          </div>

          <!-- Color indicator -->
          <div
            v-if="category.color"
            class="w-6 h-6 rounded-full flex-shrink-0"
            :style="{ backgroundColor: category.color }"
          ></div>
        </div>
      </BaseCard>
    </div>

    <!-- Floating Action Button -->
    <SimpleFab
      aria-label="Crear nueva categoría"
      @click="createCategory"
    />
  </div>
</template>
