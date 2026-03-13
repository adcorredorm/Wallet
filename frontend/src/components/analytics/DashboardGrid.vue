<script setup lang="ts">
import { computed } from 'vue'
import { useDashboardsStore } from '@/stores/dashboards'
import WidgetRenderer from '@/components/analytics/WidgetRenderer.vue'

const store = useDashboardsStore()
const dashboard = computed(() => store.currentDashboard)

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
      <div
        v-for="widget in dashboard.widgets"
        :key="widget.id"
        class="widget-item rounded-lg overflow-hidden"
        :style="gridStyle(widget)"
      >
        <WidgetRenderer
          :widget="widget"
          :display-currency="dashboard.display_currency"
        />
      </div>
    </div>

    <!-- Empty state: no widgets -->
    <div v-if="dashboard.widgets.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
      <p class="text-dark-text-secondary text-sm">Este dashboard no tiene widgets aún.</p>
    </div>
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
}
</style>
