<script setup lang="ts">
/**
 * DashboardSettingsModal — Edit an existing dashboard and optionally delete it.
 *
 * Why does this component read store.currentDashboard instead of receiving
 * the full dashboard object as a prop?
 * The dashboard is already in the Pinia store (loaded by AnalyticsView).
 * Passing it again as a prop would create a second source of truth that must
 * stay in sync. Reading the store directly is simpler and always up-to-date.
 *
 * Why a separate ConfirmDialog for deletion instead of a window.confirm()?
 * window.confirm is blocked in many PWA contexts and gives zero control over
 * styling or i18n. ConfirmDialog is consistent with the rest of the app.
 *
 * Mobile-first decisions:
 * - Delete button is separated visually (red danger zone section) so it is not
 *   accidentally tapped while filling in the form fields above it.
 * - Bottom-sheet modal on mobile keeps the user oriented in the app.
 * - Segmented column picker matches DashboardCreateModal for consistency.
 */

import { reactive, ref, watch } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import { useDashboardsStore } from '@/stores/dashboards'

// ---------------------------------------------------------------------------
// Props & emits
// ---------------------------------------------------------------------------

const props = defineProps<{
  open: boolean
  dashboardId: string
}>()

const emit = defineEmits<{
  close: []
}>()

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

const store = useDashboardsStore()

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

const saving = ref(false)
const deleting = ref(false)
const showDeleteConfirm = ref(false)
const nameError = ref('')

const form = reactive({
  name: '',
  description: '',
  display_currency: 'USD',
  layout_columns: 2,
  is_default: false,
})

// Currency options — same list as DashboardCreateModal.
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

// ---------------------------------------------------------------------------
// Populate form when the modal opens (or the current dashboard changes)
// ---------------------------------------------------------------------------

watch(
  () => [props.open, store.currentDashboard] as const,
  ([isOpen, dashboard]) => {
    if (!isOpen || !dashboard) return
    form.name = dashboard.name
    form.description = dashboard.description ?? ''
    form.display_currency = dashboard.display_currency
    form.layout_columns = dashboard.layout_columns
    form.is_default = dashboard.is_default

    // Ensure the dashboard's currency is in the list.
    if (!currencyOptions.find(o => o.value === dashboard.display_currency)) {
      currencyOptions.unshift({ value: dashboard.display_currency, label: dashboard.display_currency })
    }
  },
  { immediate: true }
)

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

async function onSave() {
  nameError.value = ''
  if (!form.name.trim()) {
    nameError.value = 'El nombre es requerido.'
    return
  }

  saving.value = true
  try {
    await store.updateDashboard(props.dashboardId, {
      name: form.name.trim(),
      description: form.description.trim() || null,
      display_currency: form.display_currency,
      layout_columns: form.layout_columns,
      is_default: form.is_default,
    })
    emit('close')
  } catch (e) {
    console.error('Error updating dashboard:', e)
  } finally {
    saving.value = false
  }
}

async function onConfirmDelete() {
  deleting.value = true
  try {
    await store.deleteDashboard(props.dashboardId)
    showDeleteConfirm.value = false
    emit('close')
  } catch (e) {
    console.error('Error deleting dashboard:', e)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <BaseModal
    :show="open"
    title="Configuración del dashboard"
    size="md"
    @close="emit('close')"
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

      <!-- Mark as default — checkbox row -->
      <label class="flex items-center gap-3 cursor-pointer select-none py-1">
        <input
          v-model="form.is_default"
          type="checkbox"
          class="w-5 h-5 rounded accent-blue-500"
        />
        <span class="text-sm text-dark-text-secondary">Marcar como predeterminado</span>
      </label>

      <!-- Danger zone: delete -->
      <div class="pt-2 border-t border-dark-border">
        <button
          type="button"
          class="delete-btn"
          @click="showDeleteConfirm = true"
        >
          Eliminar dashboard
        </button>
      </div>

    </div>

    <!-- Footer -->
    <template #footer>
      <div class="flex gap-3 justify-end">
        <BaseButton
          variant="ghost"
          :disabled="saving"
          @click="emit('close')"
        >
          Cancelar
        </BaseButton>
        <BaseButton
          variant="primary"
          :loading="saving"
          :disabled="!form.name.trim()"
          @click="onSave"
        >
          Guardar
        </BaseButton>
      </div>
    </template>
  </BaseModal>

  <!-- Delete confirmation dialog — rendered outside the main modal to avoid
       z-index stacking issues. Both use Teleport to body so z-index is clean. -->
  <ConfirmDialog
    :show="showDeleteConfirm"
    title="Eliminar dashboard"
    message="¿Eliminar este dashboard y todos sus widgets?"
    confirm-text="Eliminar"
    :loading="deleting"
    variant="danger"
    @confirm="onConfirmDelete"
    @cancel="showDeleteConfirm = false"
  />
</template>

<style scoped>
/*
 * Segmented column-count picker — same style as DashboardCreateModal
 * for visual consistency. min-height 44px = mobile touch target.
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

/*
 * Danger-zone delete button.
 * Full width for easier tapping on mobile. Red text on dark background
 * communicates destructive intent without a heavy filled button style —
 * that weight is reserved for the ConfirmDialog confirmation button.
 */
.delete-btn {
  width: 100%;
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #ef4444;
  background-color: transparent;
  border: 1px solid #ef444440;
  transition: background-color 0.15s ease;
  cursor: pointer;
  text-align: left;
}

.delete-btn:hover {
  background-color: #ef444415;
}
</style>
