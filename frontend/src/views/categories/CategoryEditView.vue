<script setup lang="ts">
/**
 * Category Edit View
 *
 * Form to edit existing category
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

const route = useRoute()
const router = useRouter()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const categoryId = route.params.id as string
const showDeleteDialog = ref(false)
const deleting = ref(false)

const category = computed(() =>
  categoriesStore.categories.find(c => c.id === categoryId)
)

const form = reactive({
  nombre: '',
  tipo: '' as CategoryType,
  icono: '',
  color: '#3b82f6',
  categoria_padre_id: '' as string
})

const errors = reactive({
  nombre: '',
  tipo: ''
})

// Whether this category has subcategories (cannot become a child itself)
const hasChildren = computed(() =>
  categoriesStore.getSubcategories(categoryId).length > 0
)

// Eligible parent categories for the current tipo, excluding self and own children
const parentOptions = computed(() => {
  if (!form.tipo) return []
  return categoriesStore.compatibleParentCategories(form.tipo as CategoryType, categoryId)
    .map(cat => ({
      value: cat.id,
      label: `${cat.icono ?? ''} ${cat.nombre}`.trim()
    }))
})

// Reset parent when tipo changes
watch(() => form.tipo, () => {
  form.categoria_padre_id = ''
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
    form.nombre = category.value.nombre
    form.tipo = category.value.tipo
    form.icono = category.value.icono || ''
    form.color = category.value.color || '#3b82f6'
    form.categoria_padre_id = category.value.categoria_padre_id ?? ''
  }
})

function validateForm(): boolean {
  let isValid = true

  const nombreValidation = required(form.nombre) && minLength(2)(form.nombre) && maxLength(50)(form.nombre)
  if (nombreValidation !== true) {
    errors.nombre = nombreValidation as string
    isValid = false
  } else {
    errors.nombre = ''
  }

  if (!form.tipo) {
    errors.tipo = 'Debes seleccionar un tipo'
    isValid = false
  } else {
    errors.tipo = ''
  }

  return isValid
}

async function handleSubmit() {
  if (!validateForm()) return

  try {
    // For edit: always include categoria_padre_id.
    // Empty string clears the parent (unparents); a value sets it.
    // The store will persist this to IndexedDB and the mutation queue.
    const data: UpdateCategoryDto = {
      nombre: form.nombre.trim(),
      tipo: form.tipo,
      icono: form.icono || undefined,
      color: form.color || undefined,
      categoria_padre_id: form.categoria_padre_id || undefined
    }
    // When user explicitly selected "no parent", we need to clear it
    // in IndexedDB. We pass empty string which the offline layer stores.
    if (!form.categoria_padre_id && category.value?.categoria_padre_id) {
      (data as Record<string, unknown>).categoria_padre_id = ''
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

async function confirmDelete() {
  deleting.value = true
  try {
    await categoriesStore.deleteCategory(categoryId)
    uiStore.showSuccess('Categoría eliminada exitosamente')
    router.push('/categories')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al eliminar categoría')
  } finally {
    deleting.value = false
    showDeleteDialog.value = false
  }
}
</script>

<template>
  <div v-if="category" class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Editar Categoría</h1>
      <BaseButton variant="danger" size="sm" @click="showDeleteDialog = true">
        Eliminar
      </BaseButton>
    </div>

    <BaseCard>
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Nombre -->
        <BaseInput
          v-model="form.nombre"
          label="Nombre"
          placeholder="Ej: Alimentación"
          :error="errors.nombre"
          required
        />

        <!-- Tipo -->
        <BaseSelect
          v-model="form.tipo"
          label="Tipo"
          :options="CATEGORY_TYPES"
          :error="errors.tipo"
          required
        />

        <!-- Categoría padre -->
        <div>
          <BaseSelect
            v-model="form.categoria_padre_id"
            label="Categoría padre (opcional)"
            :options="[
              { value: '', label: 'Ninguna (categoría raíz)' },
              ...parentOptions
            ]"
            :disabled="!form.tipo || hasChildren"
          />
          <p v-if="!form.tipo" class="mt-1 text-xs text-dark-text-secondary">
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
                form.icono === icon ? 'bg-dark-bg-tertiary ring-2 ring-accent-blue' : ''
              ]"
              @click="form.icono = icon"
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

    <!-- Delete confirmation dialog -->
    <ConfirmDialog
      :show="showDeleteDialog"
      title="Eliminar categoría"
      :message="`¿Estás seguro de que deseas eliminar la categoría '${category.nombre}'? Esta acción no se puede deshacer.`"
      confirm-text="Eliminar"
      :loading="deleting"
      @confirm="confirmDelete"
      @cancel="showDeleteDialog = false"
    />
  </div>

  <BaseSpinner v-else centered />
</template>
