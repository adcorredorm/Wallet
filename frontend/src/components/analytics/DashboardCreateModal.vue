<script setup lang="ts">
/**
 * DashboardCreateModal — Create a new analytics dashboard.
 *
 * Why a dedicated create modal vs reusing DashboardSettingsModal?
 * Create and edit have subtly different UX expectations: create should default
 * sensibly and feel lightweight; edit shows the delete action and pre-populates.
 * Keeping them separate makes each component single-purpose and easier to test.
 *
 * Mobile-first decisions:
 * - BaseModal renders as a bottom sheet on mobile (items-end, rounded-t-2xl).
 * - Form fields are stacked vertically — on mobile that is the only sensible
 *   layout because 320px width leaves no room for side-by-side columns.
 * - layout_columns uses a segmented button group (1–4) instead of a number
 *   input because discrete tapping is faster and clearer on a touch screen.
 * - All interactive elements respect the 44px minimum touch target.
 */

import { reactive, ref } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { useDashboardsStore } from '@/stores/dashboards'

// ---------------------------------------------------------------------------
// Props & emits
// ---------------------------------------------------------------------------

const props = defineProps<{
  open: boolean
  primaryCurrency: string
}>()

const emit = defineEmits<{
  close: []
  created: []
}>()

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

const store = useDashboardsStore()

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

const saving = ref(false)
const nameError = ref('')

const form = reactive({
  name: '',
  description: '',
  display_currency: props.primaryCurrency,
  layout_columns: 2
})

// Currency options: common ISO codes. The user's primaryCurrency is pre-selected.
const currencyOptions = [
  { value: 'USD', label: 'USD — Dólar estadounidense' },
  { value: 'EUR', label: 'EUR — Euro' },
  { value: 'ARS', label: 'ARS — Peso argentino' },
  { value: 'BRL', label: 'BRL — Real brasileño' },
  { value: 'CLP', label: 'CLP — Peso chileno' },
  { value: 'COP', label: 'COP — Peso colombiano' },
  { value: 'MXN', label: 'MXN — Peso mexicano' },
  { value: 'PEN', label: 'PEN — Sol peruano' },
  { value: 'UYU', label: 'UYU — Peso uruguayo' },
  { value: 'GBP', label: 'GBP — Libra esterlina' },
  { value: 'JPY', label: 'JPY — Yen japonés' },
]

// Ensure the primaryCurrency prop is in the list (it may be an uncommon code).
// We add it dynamically so the select always shows the right default value.
if (!currencyOptions.find(o => o.value === props.primaryCurrency)) {
  currencyOptions.unshift({ value: props.primaryCurrency, label: props.primaryCurrency })
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

function resetForm() {
  form.name = ''
  form.description = ''
  form.display_currency = props.primaryCurrency
  form.layout_columns = 2
  nameError.value = ''
}

async function onSave() {
  nameError.value = ''
  if (!form.name.trim()) {
    nameError.value = 'El nombre es requerido.'
    return
  }

  saving.value = true
  try {
    const created = await store.createDashboard({
      name: form.name.trim(),
      description: form.description.trim() || null,
      display_currency: form.display_currency,
      layout_columns: form.layout_columns,
    })

    // Fetch the new dashboard so it becomes currentDashboard
    await store.fetchDashboard(created.id)

    resetForm()
    emit('created')
    emit('close')
  } catch (e) {
    console.error('Error creating dashboard:', e)
  } finally {
    saving.value = false
  }
}

function onClose() {
  resetForm()
  emit('close')
}
</script>

<template>
  <BaseModal
    :show="open"
    title="Nuevo dashboard"
    size="md"
    @close="onClose"
  >
    <div class="space-y-4">

      <!-- Name (required) -->
      <BaseInput
        v-model="form.name"
        label="Nombre"
        placeholder="Ej: Finanzas personales"
        required
        :error="nameError"
      />

      <!-- Description (optional) -->
      <BaseInput
        v-model="form.description"
        label="Descripción"
        placeholder="Ej: Gastos e ingresos del hogar"
      />

      <!-- Display currency -->
      <BaseSelect
        v-model="form.display_currency"
        label="Moneda de visualización"
        :options="currencyOptions"
      />

      <!-- Layout columns — segmented picker (1–4) -->
      <div class="space-y-2">
        <span class="label">Columnas de grilla</span>
        <div class="flex gap-2">
          <button
            v-for="n in [1, 2, 3, 4]"
            :key="n"
            type="button"
            :class="[
              'col-btn',
              form.layout_columns === n ? 'col-btn--active' : 'col-btn--inactive'
            ]"
            @click="form.layout_columns = n"
          >
            {{ n }}
          </button>
        </div>
      </div>

    </div>

    <!-- Footer -->
    <template #footer>
      <div class="flex gap-3 justify-end">
        <BaseButton
          variant="ghost"
          :disabled="saving"
          @click="onClose"
        >
          Cancelar
        </BaseButton>
        <BaseButton
          variant="primary"
          :loading="saving"
          :disabled="!form.name.trim()"
          @click="onSave"
        >
          Crear
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
/*
 * Segmented column-count picker buttons.
 * min-height 44px satisfies the mobile touch target requirement.
 * flex-1 distributes the four buttons equally across the available width.
 */
.col-btn {
  flex: 1;
  min-height: 44px;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  transition: background-color 0.15s ease, color 0.15s ease;
  cursor: pointer;
  border: 1px solid transparent;
}

.col-btn--active {
  background-color: #3b82f6;
  color: #f1f5f9;
  border-color: #3b82f6;
}

.col-btn--inactive {
  background-color: #334155;
  color: #cbd5e1;
  border-color: #334155;
}

.col-btn--inactive:hover {
  background-color: #475569;
  color: #f1f5f9;
}
</style>
