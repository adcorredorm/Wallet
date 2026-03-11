<script setup lang="ts">
/**
 * Category Create View
 *
 * Form to create a new category
 */

import { reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoriesStore, useUiStore } from '@/stores'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { CATEGORY_TYPES, CATEGORY_ICONS, CATEGORY_COLORS } from '@/utils/constants'
import { required, minLength, maxLength } from '@/utils/validators'
import type { CreateCategoryDto, CategoryType } from '@/types'

const router = useRouter()
const categoriesStore = useCategoriesStore()
const uiStore = useUiStore()

const form = reactive({
  nombre: '',
  tipo: '' as CategoryType,
  icono: '',
  color: '#3b82f6',
  categoria_padre_id: '' as string
})

// Eligible parent categories based on the selected tipo
const parentOptions = computed(() => {
  if (!form.tipo) return []
  return categoriesStore.compatibleParentCategories(form.tipo as CategoryType)
    .map(cat => ({
      value: cat.id,
      label: `${cat.icono ?? ''} ${cat.nombre}`.trim()
    }))
})

// Reset parent when tipo changes (parent compatibility may change)
watch(() => form.tipo, () => {
  form.categoria_padre_id = ''
})

const errors = reactive({
  nombre: '',
  tipo: ''
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
    const data: CreateCategoryDto = {
      nombre: form.nombre.trim(),
      tipo: form.tipo,
      icono: form.icono || undefined,
      color: form.color || undefined,
      categoria_padre_id: form.categoria_padre_id || undefined
    }

    await categoriesStore.createCategory(data)
    uiStore.showSuccess('Categoría creada exitosamente')
    router.push('/categories')
  } catch (error: any) {
    uiStore.showError(error.message || 'Error al crear categoría')
  }
}

function handleCancel() {
  router.back()
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold">Nueva Categoría</h1>

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
          placeholder="Selecciona un tipo"
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
            :disabled="!form.tipo"
          />
          <p v-if="!form.tipo" class="mt-1 text-xs text-dark-text-secondary">
            Selecciona un tipo primero
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
            Crear categoría
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
  </div>
</template>
