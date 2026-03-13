<script setup lang="ts">
/**
 * WidgetConfigModal — Create or edit a dashboard widget's configuration.
 *
 * Why a dedicated modal instead of inline editing on the grid?
 * Widget configuration has many fields (time range, filters, granularity,
 * aggregation, grouping) that don't fit cleanly in a card-level popover.
 * A modal gives us a scrollable, focused surface with enough space for all
 * fields plus a live preview — without cluttering the dashboard grid itself.
 *
 * Mobile-first decisions:
 * - BaseModal size="lg" gives max-w-2xl on desktop; on mobile the modal
 *   renders as a bottom sheet (items-end, rounded-t-2xl) per BaseModal's
 *   built-in mobile behavior.
 * - All form rows are stacked vertically (flex-col) on mobile and move to
 *   a two-column grid on tablet+ only where it saves vertical space.
 * - The preview section collapses to a fixed-height box to avoid taking
 *   over the viewport on small screens.
 * - Minimum 44px touch targets on all interactive controls.
 *
 * Why does form.tx_type use '' as the "all" sentinel instead of undefined?
 * BaseSelect emits strings and reactive() requires a consistent type. An
 * empty string is a safe falsy sentinel that avoids type narrowing issues
 * when building the filter config.
 *
 * account_ids, category_ids, and category_groups are TODO — the multi-select
 * pickers require significant additional UI work outside the scope of NF-B6.
 */

import { reactive, ref, computed, watch } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import WidgetRenderer from '@/components/analytics/WidgetRenderer.vue'
import { useDashboardsStore } from '@/stores/dashboards'
import type {
  DashboardWidget,
  WidgetConfig,
  WidgetType,
  DynamicTimeRange,
  AnalyticsGranularity,
  GroupBy,
  Aggregation
} from '@/types/dashboard'

// ---------------------------------------------------------------------------
// Props & emits
// ---------------------------------------------------------------------------

const props = defineProps<{
  dashboardId: string
  widget?: DashboardWidget | null
  open: boolean
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

const form = reactive({
  title: '',
  widget_type: 'bar' as WidgetType,
  time_range_type: 'dynamic' as 'dynamic' | 'static',
  dynamic_preset: 'this_month' as DynamicTimeRange,
  static_from: '',
  static_to: '',
  account_ids: [] as string[],
  category_ids: [] as string[],
  tx_type: '' as '' | 'income' | 'expense',
  amount_min: null as number | null,
  amount_max: null as number | null,
  granularity: 'month' as AnalyticsGranularity,
  group_by: 'none' as GroupBy,
  aggregation: 'sum' as Aggregation,
  category_groups: {} as Record<string, string[]>
})

// ---------------------------------------------------------------------------
// Watch widget prop — populate form when editing, reset when creating
// ---------------------------------------------------------------------------

watch(
  () => props.widget,
  (w) => {
    if (!w) {
      Object.assign(form, {
        title: '',
        widget_type: 'bar' as WidgetType,
        time_range_type: 'dynamic',
        dynamic_preset: 'this_month' as DynamicTimeRange,
        static_from: '',
        static_to: '',
        account_ids: [],
        category_ids: [],
        tx_type: '',
        amount_min: null,
        amount_max: null,
        granularity: 'month' as AnalyticsGranularity,
        group_by: 'none' as GroupBy,
        aggregation: 'sum' as Aggregation,
        category_groups: {}
      })
      return
    }

    form.title = w.title
    form.widget_type = w.widget_type
    form.time_range_type = w.config.time_range.type
    form.dynamic_preset =
      w.config.time_range.type === 'dynamic' ? w.config.time_range.value : 'this_month'
    form.static_from =
      w.config.time_range.type === 'static' ? w.config.time_range.value.from : ''
    form.static_to =
      w.config.time_range.type === 'static' ? w.config.time_range.value.to : ''
    form.account_ids = [...(w.config.filters.account_ids ?? [])]
    form.category_ids = [...(w.config.filters.category_ids ?? [])]
    form.tx_type = (w.config.filters.type ?? '') as '' | 'income' | 'expense'
    form.amount_min = w.config.filters.amount_min ?? null
    form.amount_max = w.config.filters.amount_max ?? null
    form.granularity = w.config.granularity
    form.group_by = w.config.group_by
    form.aggregation = w.config.aggregation
    form.category_groups = { ...(w.config.category_groups ?? {}) }
  },
  { immediate: true }
)

// ---------------------------------------------------------------------------
// Derived config from form
// ---------------------------------------------------------------------------

const builtConfig = computed<WidgetConfig>(() => ({
  time_range:
    form.time_range_type === 'dynamic'
      ? { type: 'dynamic', value: form.dynamic_preset }
      : { type: 'static', value: { from: form.static_from, to: form.static_to } },
  filters: {
    ...(form.account_ids.length ? { account_ids: form.account_ids } : {}),
    ...(form.category_ids.length ? { category_ids: form.category_ids } : {}),
    ...(form.tx_type ? { type: form.tx_type as 'income' | 'expense' } : {}),
    ...(form.amount_min != null ? { amount_min: form.amount_min } : {}),
    ...(form.amount_max != null ? { amount_max: form.amount_max } : {})
  },
  granularity: form.granularity,
  group_by: form.group_by,
  aggregation: form.aggregation,
  ...(Object.keys(form.category_groups).length
    ? { category_groups: form.category_groups }
    : {})
}))

// ---------------------------------------------------------------------------
// Live preview widget
// ---------------------------------------------------------------------------

const previewWidget = computed<DashboardWidget>(() => ({
  id: 'preview',
  dashboard_id: props.dashboardId,
  widget_type: form.widget_type,
  title: form.title || 'Vista previa',
  position_x: 0,
  position_y: 0,
  width: 2,
  height: 1,
  created_at: '',
  updated_at: '',
  config: builtConfig.value
}))

// ---------------------------------------------------------------------------
// Select options
// ---------------------------------------------------------------------------

const widgetTypeOptions = [
  { value: 'bar', label: 'Barras' },
  { value: 'line', label: 'Línea' },
  { value: 'pie', label: 'Torta' },
  { value: 'stacked_bar', label: 'Barras apiladas' },
  { value: 'number', label: 'Número' }
]

const dynamicPresetOptions = [
  { value: 'last_7_days', label: 'Últimos 7 días' },
  { value: 'last_30_days', label: 'Últimos 30 días' },
  { value: 'last_90_days', label: 'Últimos 90 días' },
  { value: 'this_month', label: 'Este mes' },
  { value: 'last_month', label: 'Mes pasado' },
  { value: 'this_quarter', label: 'Este trimestre' },
  { value: 'this_year', label: 'Este año' },
  { value: 'last_year', label: 'Año pasado' },
  { value: 'all_time', label: 'Todo el tiempo' }
]

const granularityOptions = [
  { value: 'day', label: 'Día' },
  { value: 'week', label: 'Semana' },
  { value: 'month', label: 'Mes' },
  { value: 'quarter', label: 'Trimestre' },
  { value: 'semester', label: 'Semestre' },
  { value: 'year', label: 'Año' }
]

const groupByOptions = [
  { value: 'none', label: 'Sin agrupación' },
  { value: 'category', label: 'Categoría' },
  { value: 'account', label: 'Cuenta' },
  { value: 'type', label: 'Tipo' },
  { value: 'day_of_week', label: 'Día de la semana' }
]

const aggregationOptions = [
  { value: 'sum', label: 'Suma' },
  { value: 'avg', label: 'Promedio' },
  { value: 'count', label: 'Cantidad' },
  { value: 'min', label: 'Mínimo' },
  { value: 'max', label: 'Máximo' }
]

// ---------------------------------------------------------------------------
// Save handler
// ---------------------------------------------------------------------------

async function onSave() {
  if (!form.title.trim()) return
  saving.value = true
  try {
    const dto = {
      widget_type: form.widget_type,
      title: form.title.trim(),
      config: builtConfig.value
    }
    if (props.widget) {
      await store.updateWidget(props.dashboardId, props.widget.id, dto)
    } else {
      await store.createWidget(props.dashboardId, dto)
    }
    emit('close')
  } catch (e) {
    console.error('Error saving widget:', e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <BaseModal
    :show="open"
    :title="widget ? 'Editar widget' : 'Nuevo widget'"
    size="lg"
    @close="emit('close')"
  >
    <!-- ------------------------------------------------------------------ -->
    <!-- Form body                                                           -->
    <!-- ------------------------------------------------------------------ -->
    <div class="space-y-5">

      <!-- 1. Title -->
      <BaseInput
        v-model="form.title"
        label="Título"
        placeholder="Ej: Gastos del mes"
        required
      />

      <!-- 2. Widget type -->
      <BaseSelect
        v-model="form.widget_type"
        label="Tipo de widget"
        :options="widgetTypeOptions"
      />

      <!-- 3. Time range -->
      <div class="space-y-3">
        <span class="label">Rango de tiempo</span>

        <!-- Toggle: dynamic / static -->
        <div class="flex gap-2">
          <button
            type="button"
            :class="[
              'toggle-btn',
              form.time_range_type === 'dynamic' ? 'toggle-btn--active' : 'toggle-btn--inactive'
            ]"
            @click="form.time_range_type = 'dynamic'"
          >
            Dinámico
          </button>
          <button
            type="button"
            :class="[
              'toggle-btn',
              form.time_range_type === 'static' ? 'toggle-btn--active' : 'toggle-btn--inactive'
            ]"
            @click="form.time_range_type = 'static'"
          >
            Estático
          </button>
        </div>

        <!-- Dynamic preset select -->
        <BaseSelect
          v-if="form.time_range_type === 'dynamic'"
          v-model="form.dynamic_preset"
          :options="dynamicPresetOptions"
          placeholder="Seleccionar período"
        />

        <!-- Static date pickers -->
        <div v-else class="grid grid-cols-2 gap-3">
          <BaseInput
            v-model="form.static_from"
            type="date"
            label="Desde"
          />
          <BaseInput
            v-model="form.static_to"
            type="date"
            label="Hasta"
          />
        </div>
      </div>

      <!-- 4. Transaction type -->
      <div class="space-y-2">
        <span class="label">Tipo de transacción</span>
        <div class="flex gap-2">
          <button
            type="button"
            :class="[
              'toggle-btn flex-1',
              form.tx_type === '' ? 'toggle-btn--active' : 'toggle-btn--inactive'
            ]"
            @click="form.tx_type = ''"
          >
            Todos
          </button>
          <button
            type="button"
            :class="[
              'toggle-btn flex-1',
              form.tx_type === 'income' ? 'toggle-btn--active' : 'toggle-btn--inactive'
            ]"
            @click="form.tx_type = 'income'"
          >
            Ingresos
          </button>
          <button
            type="button"
            :class="[
              'toggle-btn flex-1',
              form.tx_type === 'expense' ? 'toggle-btn--active' : 'toggle-btn--inactive'
            ]"
            @click="form.tx_type = 'expense'"
          >
            Gastos
          </button>
        </div>
      </div>

      <!-- 5–7: Granularity, Group by, Aggregation — two-column on tablet+ -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <BaseSelect
          v-model="form.granularity"
          label="Granularidad"
          :options="granularityOptions"
        />
        <BaseSelect
          v-model="form.group_by"
          label="Agrupar por"
          :options="groupByOptions"
        />
        <BaseSelect
          v-model="form.aggregation"
          label="Agregación"
          :options="aggregationOptions"
        />
      </div>

      <!-- 8. Live preview -->
      <div v-if="store.currentDashboard" class="space-y-2">
        <span class="label">Vista previa</span>
        <div class="preview-box">
          <WidgetRenderer
            :widget="previewWidget"
            :display-currency="store.currentDashboard.display_currency"
          />
        </div>
      </div>

    </div>

    <!-- ------------------------------------------------------------------ -->
    <!-- Footer                                                              -->
    <!-- ------------------------------------------------------------------ -->
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
          :disabled="!form.title.trim()"
          @click="onSave"
        >
          {{ widget ? 'Guardar cambios' : 'Crear widget' }}
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
/* Toggle button base — used for dynamic/static and tx_type selectors.
   44px min-height ensures touch-friendliness per mobile-first requirements. */
.toggle-btn {
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background-color 0.15s ease, color 0.15s ease;
  cursor: pointer;
  border: 1px solid transparent;
}

.toggle-btn--active {
  background-color: #3b82f6;
  color: #f1f5f9;
  border-color: #3b82f6;
}

.toggle-btn--inactive {
  background-color: #334155;
  color: #cbd5e1;
  border-color: #334155;
}

.toggle-btn--inactive:hover {
  background-color: #475569;
  color: #f1f5f9;
}

/* Preview box — fixed height to avoid the chart taking over the
   modal on small screens. 220px is enough to render all chart types
   legibly without requiring the user to scroll past it. */
.preview-box {
  height: 220px;
  border-radius: 0.75rem;
  overflow: hidden;
  background-color: #1e293b;
  border: 1px solid #334155;
}

@media (min-width: 768px) {
  .preview-box {
    height: 260px;
  }
}
</style>
