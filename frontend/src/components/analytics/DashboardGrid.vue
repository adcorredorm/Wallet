<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDashboardsStore } from '@/stores/dashboards'
import WidgetRenderer from '@/components/analytics/WidgetRenderer.vue'
import WidgetActions from '@/components/analytics/WidgetActions.vue'
import WidgetConfigModal from '@/components/analytics/WidgetConfigModal.vue'
import type { DashboardWidget } from '@/types/dashboard'

const store = useDashboardsStore()
const dashboard = computed(() => store.currentDashboard)

// Widget being edited via WidgetConfigModal.
// null means no editing is in progress (modal closed).
const editingWidget = ref<DashboardWidget | null>(null)

// Controls the "Agregar widget" flow — opens WidgetConfigModal in create mode.
const addingWidget = ref(false)

/**
 * Returns the inline CSS grid placement styles for a widget.
 * These are applied as inline styles on every widget item. On mobile the
 * scoped CSS resets grid-column and grid-row to `auto` so items stack
 * naturally. On md+ the CSS reset is lifted and the inline placement takes
 * effect, positioning each widget at position_x/position_y spanning
 * width/height columns/rows in the dashboard's multi-column grid.
 *
 * Why inline styles for grid placement?
 * The position values (position_x, position_y, width, height) are runtime data
 * from the API. Tailwind JIT cannot generate classes like `col-start-3` for
 * values it has never seen at build time. Inline styles are the correct tool
 * for truly dynamic CSS Grid placement.
 */
function gridStyle(w: { position_x: number; position_y: number; width: number; height: number }) {
  return {
    gridColumn: `${w.position_x + 1} / span ${w.width}`,
    gridRow: `${w.position_y + 1} / span ${w.height}`,
    minHeight: `${w.height * 160}px`,
  }
}

function closeConfigModal() {
  addingWidget.value = false
  editingWidget.value = null
}
</script>

<template>
  <div v-if="dashboard">
    <!--
      The grid container uses --grid-cols to set grid-template-columns on md+.
      On mobile it is a single-column stack (grid-cols-1 from Tailwind).
      The CSS custom property carries layout_columns from the dashboard config
      into the scoped @media rule below.
    -->
    <div
      class="grid gap-3 grid-cols-1"
      :style="{ '--grid-cols': dashboard.layout_columns }"
    >
      <!--
        Each widget cell is position: relative so WidgetActions can use
        position: absolute to overlay the full cell. The `group` Tailwind class
        enables the CSS sibling/parent hover trick: on desktop we use
        `.widget-item:hover .widget-actions` to reveal the overlay without JS.
      -->
      <div
        v-for="widget in dashboard.widgets"
        :key="widget.id"
        class="widget-item rounded-lg overflow-hidden relative"
        :style="gridStyle(widget)"
      >
        <WidgetRenderer
          :widget="widget"
          :display-currency="dashboard.display_currency"
        />
        <WidgetActions
          :widget="widget"
          :dashboard-id="dashboard.id"
          @edit="editingWidget = widget"
        />
      </div>
    </div>

    <!-- Empty state: no widgets -->
    <div v-if="dashboard.widgets.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
      <p class="text-dark-text-secondary text-sm">Este dashboard no tiene widgets aún.</p>
    </div>

    <!--
      "Agregar widget" button.
      Full-width on mobile to maximise the tap target. min-height 44px per
      touch target requirement. Dashed border communicates an additive action
      (same convention as Notion, Figma, Linear) without a heavy filled button
      that would compete visually with the widgets above.
    -->
    <button
      class="add-widget-btn mt-3"
      @click="addingWidget = true"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
      </svg>
      Agregar widget
    </button>

    <!-- WidgetConfigModal: shared for both create (addingWidget) and edit (editingWidget).
         The `widget` prop being null puts the modal in create mode.
         The `widget` prop being set puts it in edit mode (pre-populated form). -->
    <WidgetConfigModal
      :open="addingWidget || editingWidget !== null"
      :dashboard-id="dashboard.id"
      :widget="editingWidget"
      @close="closeConfigModal"
    />
  </div>
</template>

<style scoped>
/*
 * Mobile-first CSS Grid strategy:
 *
 * Base (mobile): reset inline grid-column/grid-row placement to `auto` so
 * widgets stack top-to-bottom in a single column regardless of position_x/y.
 * This provides a clean, readable layout on narrow screens where a multi-column
 * grid would make each widget too narrow to read comfortably.
 *
 * md+ (768px): lift the reset so the inline gridColumn/gridRow styles (set via
 * gridStyle()) take effect. Also activate the multi-column grid via
 * grid-template-columns using the --grid-cols CSS custom property that carries
 * layout_columns from the dashboard config.
 */

.widget-item {
  grid-column: auto !important;
  grid-row: auto !important;
}

@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(var(--grid-cols, 2), minmax(0, 1fr));
  }

  .widget-item {
    grid-column: unset !important;
    grid-row: unset !important;
  }

  /*
   * Desktop hover reveal for WidgetActions overlay.
   * When the mouse enters the widget cell (.widget-item), we reveal the
   * .widget-actions child by setting its opacity and pointer-events.
   * This is a pure CSS approach — no JS involved on desktop.
   * The trigger button (three dots) inside WidgetActions also triggers the
   * same reveal via its own .is-visible class for mobile touch.
   */
  .widget-item:hover :deep(.widget-actions) {
    opacity: 1;
    pointer-events: auto;
  }
}

/*
 * "Agregar widget" button.
 * Full width, dashed border, minimum 44px height.
 * Text + icon centred for clear affordance.
 */
.add-widget-btn {
  width: 100%;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-radius: 0.75rem;
  border: 1.5px dashed #334155;
  background-color: transparent;
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background-color 0.15s ease;
  padding: 0.5rem 1rem;
}

.add-widget-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background-color: rgba(59, 130, 246, 0.05);
}
</style>
