<script setup lang="ts">
/**
 * Category Edit View
 *
 * Form to edit existing category.
 * Archive/hard-delete/restore pattern replaces the previous single Eliminar button.
 */

import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCategoriesStore, useUiStore } from '@/stores'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import { CATEGORY_TYPES, CATEGORY_ICONS, CATEGORY_COLORS } from '@/utils/constants'
import { required, minLength, maxLength } from '@/utils/validators'
import type { UpdateCategoryDto, CategoryType } from '@/types'
import { db } from '@/offline'

const route = useRoute()
const router = useRouter()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const categoryId = route.params.id as string

// Dialog visibility refs
const showArchiveDialog = ref(false)
const showDeleteDialog = ref(false)

// Loading refs per action
const archiving = ref(false)
const deleting = ref(false)

// Whether this category has any transactions — resolved async on mount.
// Default true keeps the hard-delete button disabled until we confirm it is safe.
const hasTransactions = ref(true)

const category = computed(() =>
  categoriesStore.categories.find(c => c.id === categoryId)
)

const isArchived = computed(() => category.value?.active === false)

const form = reactive({
  name: '',
  type: '' as CategoryType,
  icon: '',
  color: '#3b82f6',
  parent_category_id: '' as string
})

const errors = reactive({
  name: '',
  type: ''
})

// Active subcategories — getSubcategories now only returns active ones after the store fix.
// Why computed instead of ref + onMounted?
// categoriesStore.categories is reactive: if the user archives a subcategory in
// another tab / via another action the count updates automatically without a
// page reload. A computed over a reactive store ref is the idiomatic approach.
const activeSubcategoryCount = computed(() =>
  categoriesStore.getSubcategories(categoryId).length
)

// Whether this category has children (used to disable the parent selector)
const hasChildren = computed(() => activeSubcategoryCount.value > 0)

// Whether the hard-delete button should be disabled
const hardDeleteDisabled = computed(
  () => hasTransactions.value || activeSubcategoryCount.value > 0
)

// Tooltip for disabled hard-delete button
const hardDeleteTooltip = computed(() => {
  if (hasTransactions.value) {
    return 'No se puede borrar una categoría con transacciones. Usa Archivar.'
  }
  if (activeSubcategoryCount.value > 0) {
    return 'No se puede borrar una categoría con subcategorías activas. Usa Archivar.'
  }
  return ''
})

// Archive dialog message — varies depending on whether there are active subcategories
const archiveDialogMessage = computed(() => {
  if (activeSubcategoryCount.value > 0) {
    return `Archivar esta categoría también archivará sus ${activeSubcategoryCount.value} subcategoría${activeSubcategoryCount.value > 1 ? 's' : ''}. ¿Continuar?`
  }
  return '¿Archivar esta categoría? Dejará de aparecer en los formularios, pero todas las transacciones asociadas se conservarán intactas en el historial.'
})

// Eligible parent categories for the current type, excluding self and own children
const parentOptions = computed(() => {
  if (!form.type) return []
  return categoriesStore.compatibleParentCategories(form.type as CategoryType, categoryId)
    .map(cat => ({
      value: cat.id,
      label: `${cat.icon ?? ''} ${cat.name}`.trim()
    }))
})

// Reset parent when type changes
watch(() => form.type, () => {
  form.parent_category_id = ''
})

onMounted(async () => {
  if (!category.value) {
    try {
      await categoriesStore.fetchCategoryById(categoryId)
    } catch (error: any) {
      uiStore.showError(error.message || 'Error al cargar categoría')
      router.push('/categories')
      return
    }
  }

  if (category.value) {
    form.name = category.value.name
    form.type = category.value.type
    form.icon = category.value.icon || ''
    form.color = category.value.color || '#3b82f6'
    form.parent_category_id = category.value.parent_category_id ?? ''
  }

  // Async transaction count — determines whether hard-delete is available.
  // We query IndexedDB directly to mirror the guard inside hardDeleteCategory.
  try {
    const txCount = await db.transactions.where('category_id').equals(categoryId).count()
    hasTransactions.value = txCount > 0
  } catch {
    // On error leave hasTransactions = true so hard-delete stays disabled (safe default)
  }
})

function validateForm(): boolean {
  let isValid = true

  const nameValidation = required(form.name) && minLength(2)(form.name) && maxLength(50)(form.name)
  if (nameValidation !== true) {
    errors.name = nameValidation as string
    isValid = false
  } else {
    errors.name = ''
  }

  if (!form.type) {
    errors.type = 'Debes seleccionar un tipo'
    isValid = false
  } else {
    errors.type = ''
  }

  return isValid
}

async function handleSubmit() {
  if (!validateForm()) return

  try {
    const data: UpdateCategoryDto = {
      name: form.name.trim(),
      type: form.type,
      icon: form.icon || undefined,
      color: form.color || undefined,
      parent_category_id: form.parent_category_id || undefined
    }
    if (!form.parent_category_id && category.value?.parent_category_id) {
      (data as Record<string, unknown>).parent_category_id = ''
    }

    await categoriesStore.updateCategory(categoryId, data)
    uiStore.showSuccess('Categoría actualizada exitosamente')
    router.push('/categories')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al actualizar categoría')
  }
}

function handleCancel() {
  router.back()
}

async function confirmArchive() {
  archiving.value = true
  try {
    await categoriesStore.archiveCategory(categoryId)
    uiStore.showSuccess('Categoría archivada exitosamente')
    router.push('/categories')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al archivar categoría')
  } finally {
    archiving.value = false
    showArchiveDialog.value = false
  }
}

async function confirmHardDelete() {
  deleting.value = true
  try {
    await categoriesStore.hardDeleteCategory(categoryId)
    uiStore.showSuccess('Categoría eliminada permanentemente')
    router.push('/categories')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al eliminar categoría')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}

async function restoreCategory() {
  try {
    await categoriesStore.restoreCategory(categoryId)
    uiStore.showSuccess('Categoría activada exitosamente')
    // Stay on the page — category becomes active again
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al activar categoría')
  }
}
</script>

<template>
  <div v-if="category" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2 min-w-0">
        <h1 class="text-2xl font-bold truncate">Editar Categoría</h1>
        <!-- Archived badge — visible only when category is archived -->
        <span
          v-if="isArchived"
          class="text-xs text-gray-400 dark:text-gray-500 shrink-0"
        >
          Archivada
        </span>
      </div>

      <div class="flex gap-2 shrink-0">
        <!-- Active category: show Archive + Hard Delete buttons -->
        <template v-if="!isArchived">
          <!-- Archive button — always enabled for active categories -->
          <BaseButton
            variant="secondary"
            size="sm"
            :loading="archiving"
            @click="showArchiveDialog = true"
          >
            Archivar
          </BaseButton>

          <!-- Hard delete: wrap in span to show tooltip even when disabled.
               disabled attribute suppresses hover events (and therefore title tooltips)
               on <button>. A wrapping <span> keeps the hover surface alive. -->
          <span
            v-if="hardDeleteDisabled"
            :title="hardDeleteTooltip"
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

        <!-- Archived category: show single Activar button -->
        <BaseButton
          v-else
          variant="primary"
          size="sm"
          :loading="categoriesStore.loading"
          @click="restoreCategory"
        >
          Activar
        </BaseButton>
      </div>
    </div>

    <BaseCard>
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Nombre -->
        <BaseInput
          v-model="form.name"
          label="Nombre"
          placeholder="Ej: Alimentación"
          :error="errors.name"
          required
        />

        <!-- Tipo -->
        <BaseSelect
          v-model="form.type"
          label="Tipo"
          :options="CATEGORY_TYPES"
          :error="errors.type"
          required
        />

        <!-- Categoría padre -->
        <div>
          <BaseSelect
            v-model="form.parent_category_id"
            label="Categoría padre (opcional)"
            :options="[
              { value: '', label: 'Ninguna (categoría raíz)' },
              ...parentOptions
            ]"
            :disabled="!form.type || hasChildren"
          />
          <p v-if="!form.type" class="mt-1 text-xs text-dark-text-secondary">
            Selecciona un tipo primero
          </p>
          <p v-else-if="hasChildren" class="mt-1 text-xs text-dark-text-secondary">
            Esta categoría tiene subcategorías y no puede convertirse en subcategoría
          </p>
        </div>

        <!-- Icono -->
        <div>
          <label class="label">Icono (opcional)</label>
          <div class="grid grid-cols-8 gap-2">
            <button
              v-for="icon in CATEGORY_ICONS"
              :key="icon"
              type="button"
              :class="[
                'p-2 rounded-lg text-2xl hover:bg-dark-bg-tertiary transition-colors',
                form.icon === icon ? 'bg-dark-bg-tertiary ring-2 ring-accent-blue' : ''
              ]"
              @click="form.icon = icon"
            >
              {{ icon }}
            </button>
          </div>
        </div>

        <!-- Color -->
        <div>
          <label class="label">Color (opcional)</label>
          <div class="flex gap-2 flex-wrap">
            <button
              v-for="color in CATEGORY_COLORS"
              :key="color"
              type="button"
              :class="[
                'w-10 h-10 rounded-lg transition-transform',
                form.color === color ? 'ring-2 ring-white scale-110' : ''
              ]"
              :style="{ backgroundColor: color }"
              @click="form.color = color"
            ></button>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 pt-4 flex-col md:flex-row">
          <BaseButton
            type="submit"
            variant="primary"
            :loading="categoriesStore.loading"
            full-width
          >
            Actualizar categoría
          </BaseButton>
          <BaseButton
            type="button"
            variant="ghost"
            :disabled="categoriesStore.loading"
            full-width
            @click="handleCancel"
          >
            Cancelar
          </BaseButton>
        </div>
      </form>
    </BaseCard>

    <!-- Archive confirmation dialog -->
    <ConfirmDialog
      :show="showArchiveDialog"
      variant="warning"
      title="Archivar categoría"
      :message="archiveDialogMessage"
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
      message="¿Borrar esta categoría permanentemente? Esta acción no se puede deshacer."
      confirm-text="Borrar"
      :loading="deleting"
      @confirm="confirmHardDelete"
      @cancel="showDeleteDialog = false"
    />
  </div>

  <BaseSpinner v-else centered />
</template>
