<script setup lang="ts">
/**
 * Categories List View
 *
 * Shows all categories in a collapsible grouped layout.
 * Groups with children display as collapsible sections;
 * standalone categories appear in a flat grid at the bottom.
 *
 * A "Mostrar archivadas" toggle appends a flat list of archived categories
 * (both parent and child) below the active tree.
 */

import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoriesStore, useUiStore } from '@/stores'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import SimpleFab from '@/components/ui/SimpleFab.vue'
import { formatCategoryType } from '@/utils/formatters'

const router = useRouter()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

/** Tracks which parent groups are expanded (by parent id). Empty = all collapsed. */
const expandedGroups = ref<Set<string>>(new Set())

/** When true, archived categories are shown below the active tree. */
const showArchived = ref<boolean>(false)

function toggleGroup(parentId: string) {
  if (expandedGroups.value.has(parentId)) {
    expandedGroups.value.delete(parentId)
  } else {
    expandedGroups.value.add(parentId)
  }
}

onMounted(async () => {
  try {
    await categoriesStore.fetchCategories()
  } catch (error: any) {
    console.error('Error loading categories in CategoriesListView:', error)
    uiStore.showError(error.message || 'Error al cargar categorías')
  }
})

function goToCategory(id: string) {
  router.push(`/categories/${id}/edit`)
}

function createCategory() {
  router.push('/categories/new')
}

/** Groups that have children (collapsible sections) */
const groupsWithChildren = () =>
  categoriesStore.categoryTree.filter(g => g.children.length > 0)

/** Standalone categories (no children) */
const standaloneGroups = () =>
  categoriesStore.categoryTree.filter(g => g.children.length === 0)

/** Archived categories pre-enriched with their parent name (one lookup per item,
 *  not two). Looks in all categories including archived so an archived child
 *  correctly shows its archived parent. */
const archivedCategoriesWithParent = computed(() =>
  categoriesStore.archivedCategories.map(cat => ({
    ...cat,
    parentName: cat.parent_category_id
      ? (categoriesStore.categories.find(c => c.id === cat.parent_category_id)?.name ?? null)
      : null
  }))
)
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Categorías</h1>

      <!-- Mostrar archivadas toggle — only shown when there are archived categories -->
      <button
        v-if="categoriesStore.archivedCategories.length > 0"
        class="flex items-center gap-2 text-sm px-3 py-2 rounded-lg transition-colors min-h-[44px]"
        :class="showArchived
          ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
          : 'bg-dark-bg-secondary text-dark-text-secondary border border-dark-bg-tertiary/50 hover:bg-dark-bg-tertiary/50'"
        :aria-pressed="showArchived"
        aria-label="Mostrar categorías archivadas"
        @click="showArchived = !showArchived"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8l1 12a2 2 0 002 2h8a2 2 0 002-2L19 8M10 12v4m4-4v4" />
        </svg>
        Mostrar archivadas
      </button>
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
      v-else-if="categoriesStore.categories.length === 0"
      title="No hay categorías"
      message="Las categorías ayudan a organizar tus ingresos y gastos"
      icon="🏷️"
      action-text="Nueva categoría"
      @action="createCategory"
    />

    <!-- Grouped category list -->
    <div v-else class="space-y-4">

      <!-- Collapsible groups (parents with children) -->
      <div
        v-for="group in groupsWithChildren()"
        :key="group.parent.id"
        class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50"
      >
        <!-- Group header -->
        <div class="flex items-center justify-between px-4 py-3">
          <!-- Left side: clickable to edit parent -->
          <div
            class="flex items-center gap-3 flex-1 min-w-0 cursor-pointer"
            @click="goToCategory(group.parent.id)"
          >
            <!-- Color dot -->
            <div
              v-if="group.parent.color"
              class="w-3 h-3 rounded-full flex-shrink-0"
              :style="{ backgroundColor: group.parent.color }"
            ></div>

            <!-- Icon -->
            <span class="text-xl flex-shrink-0">{{ group.parent.icon || '📁' }}</span>

            <!-- Name -->
            <span class="font-medium truncate">{{ group.parent.name }}</span>

            <!-- Tipo badge -->
            <span class="text-xs px-2 py-0.5 rounded-full bg-dark-bg-tertiary text-dark-text-secondary flex-shrink-0">
              {{ formatCategoryType(group.parent.type) }}
            </span>
          </div>

          <!-- Right side: subcategory count + chevron -->
          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-xs text-dark-text-secondary">
              {{ group.children.length }} {{ group.children.length === 1 ? 'subcategoría' : 'subcategorías' }}
            </span>
            <button
              class="p-2 -mr-2 rounded-lg hover:bg-dark-bg-tertiary transition-colors"
              aria-label="Expandir subcategorías"
              @click.stop="toggleGroup(group.parent.id)"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="w-5 h-5 text-dark-text-secondary transition-transform duration-200"
                :class="{ 'rotate-180': expandedGroups.has(group.parent.id) }"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Children (expanded) -->
        <div
          v-if="expandedGroups.has(group.parent.id)"
          class="px-4 pb-3"
        >
          <div class="grid grid-cols-2 gap-3 mt-2 ml-6">
            <div
              v-for="child in group.children"
              :key="child.id"
              class="rounded-lg bg-dark-bg-tertiary/50 p-3 cursor-pointer
                     hover:bg-dark-bg-tertiary transition-colors
                     border-l-2"
              :style="{ borderLeftColor: group.parent.color || '#3b82f6' }"
              @click="goToCategory(child.id)"
            >
              <div class="flex items-center gap-2">
                <span class="text-lg flex-shrink-0">{{ child.icon || '📁' }}</span>
                <div class="min-w-0">
                  <p class="text-sm font-medium truncate">{{ child.name }}</p>
                  <p class="text-xs text-dark-text-secondary">
                    {{ formatCategoryType(child.type) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Standalone categories (no children) — same full-width style as group headers -->
      <div
        v-for="group in standaloneGroups()"
        :key="group.parent.id"
        class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50
               flex items-center px-4 py-3 gap-3 cursor-pointer
               hover:bg-dark-bg-tertiary/30 transition-colors"
        @click="goToCategory(group.parent.id)"
      >
        <!-- Color dot -->
        <div
          v-if="group.parent.color"
          class="w-3 h-3 rounded-full flex-shrink-0"
          :style="{ backgroundColor: group.parent.color }"
        ></div>

        <!-- Icon -->
        <span class="text-xl flex-shrink-0">{{ group.parent.icon || '📁' }}</span>

        <!-- Name -->
        <span class="font-medium truncate flex-1 min-w-0">{{ group.parent.name }}</span>

        <!-- Tipo badge -->
        <span class="text-xs px-2 py-0.5 rounded-full bg-dark-bg-tertiary text-dark-text-secondary flex-shrink-0">
          {{ formatCategoryType(group.parent.type) }}
        </span>
      </div>
    </div>

    <!-- Archived categories section (shown when toggle is active) -->
    <div v-if="showArchived && categoriesStore.archivedCategories.length > 0" class="space-y-2">
      <h2 class="text-sm font-medium text-dark-text-secondary uppercase tracking-wide px-1">
        Archivadas ({{ categoriesStore.archivedCategories.length }})
      </h2>
      <div
        v-for="category in archivedCategoriesWithParent"
        :key="category.id"
        class="rounded-xl bg-dark-bg-secondary border border-dark-bg-tertiary/50
               flex items-center px-4 py-3 gap-3 cursor-pointer opacity-50
               hover:opacity-75 transition-opacity"
        @click="goToCategory(category.id)"
      >
        <!-- Color dot -->
        <div
          v-if="category.color"
          class="w-3 h-3 rounded-full flex-shrink-0"
          :style="{ backgroundColor: category.color }"
        ></div>

        <!-- Icon -->
        <span class="text-xl flex-shrink-0">{{ category.icon || '📁' }}</span>

        <!-- Name + parent + Archivada badge -->
        <span class="font-medium truncate flex-1 min-w-0">
          {{ category.name }}
          <span
            v-if="category.parentName"
            class="text-xs text-dark-text-tertiary ml-1 mr-1"
          >· {{ category.parentName }}</span>
          <span class="text-xs text-gray-400 dark:text-gray-500 ml-1">Archivada</span>
        </span>

        <!-- Tipo badge -->
        <span class="text-xs px-2 py-0.5 rounded-full bg-dark-bg-tertiary text-dark-text-secondary flex-shrink-0">
          {{ formatCategoryType(category.type) }}
        </span>
      </div>
    </div>

    <!-- Floating Action Button -->
    <SimpleFab
      aria-label="Crear nueva categoría"
      @click="createCategory"
    />
  </div>
</template>
