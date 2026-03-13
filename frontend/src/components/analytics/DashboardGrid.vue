<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useWindowSize } from '@vueuse/core'
import { useDashboardsStore } from '@/stores/dashboards'
import WidgetRenderer from '@/components/analytics/WidgetRenderer.vue'
import WidgetActions from '@/components/analytics/WidgetActions.vue'
import WidgetConfigModal from '@/components/analytics/WidgetConfigModal.vue'
import type { DashboardWidget } from '@/types/dashboard'

const props = defineProps<{
  editMode?: boolean
}>()

const store = useDashboardsStore()
const dashboard = computed(() => store.currentDashboard)

const editingWidget = ref<DashboardWidget | null>(null)
const addingWidget = ref(false)

/**
 * localOrder: array of widget IDs in display order.
 *
 * Why local state instead of relying solely on store?
 * The store updates after an async API call. For instant visual feedback when
 * the user clicks a move arrow, we swap IDs here first. The grid re-renders
 * immediately because this is a reactive ref. The API call persists the new
 * positions in the background.
 */
const localOrder = ref<string[]>([])

// Sync localOrder from the store whenever the dashboard widgets change.
// Sort by position_y * 1000 + position_x so initial order matches the server.
watch(
  () => dashboard.value?.widgets,
  (widgets) => {
    if (widgets) {
      localOrder.value = [...widgets]
        .sort((a, b) => (a.position_y * 1000 + a.position_x) - (b.position_y * 1000 + b.position_x))
        .map(w => w.id)
    }
  },
  { immediate: true }
)

/**
 * sortedWidgets: widgets ordered by localOrder for display.
 * CSS Grid auto-placement puts them left-to-right, top-to-bottom.
 * With 2 columns: widget 3 = row 2 col 1. With 4 columns: widget 3 = col 3.
 */
const sortedWidgets = computed<DashboardWidget[]>(() => {
  const widgets = dashboard.value?.widgets
  if (!widgets) return []
  return localOrder.value
    .map(id => widgets.find(w => w.id === id))
    .filter((w): w is DashboardWidget => !!w)
})

const cols = computed(() => dashboard.value?.layout_columns ?? 2)

// On mobile (< 768px) the grid is always 1 column regardless of layout_columns.
// Use effectiveCols for move step size so ↑/↓ always move by 1 on mobile.
const { width: windowWidth } = useWindowSize()
const effectiveCols = computed(() => windowWidth.value < 768 ? 1 : cols.value)

/**
 * Move a widget by swapping it with a neighbor in localOrder.
 * Local swap is instant; API calls persist in the background.
 */
function moveWidget(widgetId: string, direction: 'up' | 'down' | 'left' | 'right') {
  const order = [...localOrder.value]
  const idx = order.indexOf(widgetId)
  if (idx === -1) return

  let neighborIdx: number
  switch (direction) {
    case 'up':    neighborIdx = idx - effectiveCols.value; break
    case 'down':  neighborIdx = idx + effectiveCols.value; break
    case 'left':  neighborIdx = idx - 1; break
    case 'right': neighborIdx = idx + 1; break
  }

  if (neighborIdx < 0 || neighborIdx >= order.length) return

  const neighborId = order[neighborIdx]

  // Instant local swap — grid re-renders immediately
  order[idx] = neighborId
  order[neighborIdx] = widgetId
  localOrder.value = order

  // Background: swap position_x/y between the two widgets so the server
  // state matches the new visual order on next sync/reload.
  const widgets = dashboard.value?.widgets ?? []
  const movedWidget   = widgets.find(w => w.id === widgetId)
  const neighborWidget = widgets.find(w => w.id === neighborId)

  if (!movedWidget || !neighborWidget || !dashboard.value) return

  const movedPos    = { position_x: movedWidget.position_x,   position_y: movedWidget.position_y   }
  const neighborPos = { position_x: neighborWidget.position_x, position_y: neighborWidget.position_y }

  store.updateWidget(dashboard.value.id, widgetId,   neighborPos).catch(console.error)
  store.updateWidget(dashboard.value.id, neighborId, movedPos   ).catch(console.error)
}

/** Only the span is needed — start position is handled by CSS Grid auto-placement. */
function gridStyle(w: { width: number; height: number }) {
  return {
    gridColumn: `auto / span ${w.width}`,
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
    <div
      class="grid gap-3 grid-cols-1"
      :class="{ 'edit-mode': props.editMode }"
      :style="{ '--grid-cols': dashboard.layout_columns }"
    >
      <div
        v-for="(widget, idx) in sortedWidgets"
        :key="widget.id"
        class="widget-item rounded-lg overflow-hidden relative"
        :style="gridStyle(widget)"
      >
        <WidgetRenderer
          :widget="widget"
          :display-currency="dashboard.display_currency"
        />
        <WidgetActions
          v-if="props.editMode"
          :widget="widget"
          :dashboard-id="dashboard.id"
          :widget-index="idx"
          :total-widgets="sortedWidgets.length"
          :cols="effectiveCols"
          @edit="editingWidget = widget"
          @move="moveWidget(widget.id, $event)"
        />
      </div>
    </div>

    <div v-if="dashboard.widgets.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
      <p class="text-dark-text-secondary text-sm">Este dashboard no tiene widgets aún.</p>
    </div>

    <button
      v-if="props.editMode"
      class="add-widget-btn mt-3"
      @click="addingWidget = true"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
      </svg>
      Agregar widget
    </button>

    <WidgetConfigModal
      :open="addingWidget || editingWidget !== null"
      :dashboard-id="dashboard.id"
      :widget="editingWidget"
      @close="closeConfigModal"
    />
  </div>
</template>

<style scoped>
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

/*
 * In edit mode, WidgetActions overlays are always visible on ALL screen sizes.
 * Rule is outside the @media block so it applies on mobile too.
 */
.edit-mode .widget-item :deep(.widget-actions) {
  opacity: 1;
  pointer-events: auto;
}

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
