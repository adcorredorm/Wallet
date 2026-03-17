<script setup lang="ts">
/**
 * Category Create View
 *
 * Form to create a new category
 */

import { reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAccountsStore, useCategoriesStore, useUiStore } from '@/stores'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { CATEGORY_TYPES, CATEGORY_COLORS } from '@/utils/constants'
import EmojiPicker from '@/components/ui/EmojiPicker.vue'
import { required, minLength, maxLength } from '@/utils/validators'
import type { CreateCategoryDto, CategoryType } from '@/types'

const router = useRouter()
const categoriesStore = useCategoriesStore()
const accountsStore = useAccountsStore()
const uiStore = useUiStore()

const form = reactive({
  name: '',
  type: '' as CategoryType,
  icon: '',
  color: '#3b82f6',
  parent_category_id: '' as string
})

// Eligible parent categories based on the selected type
const parentOptions = computed(() => {
  if (!form.type) return []
  return categoriesStore.compatibleParentCategories(form.type as CategoryType)
    .map(cat => ({
      value: cat.id,
      label: `${cat.icon ?? ''} ${cat.name}`.trim()
    }))
})

// Reset parent when type changes (parent compatibility may change)
watch(() => form.type, () => {
  form.parent_category_id = ''
})

const errors = reactive({
  name: '',
  type: ''
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
    const data: CreateCategoryDto = {
      name: form.name.trim(),
      type: form.type,
      icon: form.icon || undefined,
      color: form.color || undefined,
      parent_category_id: form.parent_category_id || undefined
    }

    const isOnboarding = accountsStore.activeAccounts.length === 0 || categoriesStore.activeCategories.length === 0
    await categoriesStore.createCategory(data)
    uiStore.showSuccess('Categoría creada exitosamente')
    router.push(isOnboarding ? '/' : '/categories')
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
          placeholder="Selecciona un tipo"
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
            :disabled="!form.type"
          />
          <p v-if="!form.type" class="mt-1 text-xs text-dark-text-secondary">
            Selecciona un tipo primero
          </p>
        </div>

        <!-- Icono -->
        <div>
          <label class="label">Icono (opcional)</label>
          <EmojiPicker v-model="form.icon" />
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
