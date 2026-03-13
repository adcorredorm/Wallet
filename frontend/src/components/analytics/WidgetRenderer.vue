<script setup lang="ts">
/**
 * WidgetRenderer — Routes a DashboardWidget to the correct chart component.
 *
 * Why a routing component instead of v-if in the parent?
 * Keeping the routing logic here (the "which component to use" decision) out of
 * parent components means each dashboard layout only needs to pass widget +
 * displayCurrency and never needs to know the full widget_type enum. Adding a
 * new widget type in the future only requires a change here, not in every layout.
 *
 * Why does displayCurrency come from the parent (Dashboard) instead of widget config?
 * Per the architectural decision in NF-B1: display_currency is a Dashboard-level
 * property that applies uniformly to all widgets. Putting it in WidgetConfig would
 * allow per-widget currencies which creates an inconsistent reading experience on
 * a single dashboard.
 *
 * showActions is reserved for NF-B6 (WidgetActions overlay — edit/delete buttons).
 * It is optional (default false) so WidgetRenderer is usable before that feature
 * is implemented without any prop changes.
 */

import type { DashboardWidget } from '@/types/dashboard'
import LineWidget from './widgets/LineWidget.vue'
import BarWidget from './widgets/BarWidget.vue'
import PieWidget from './widgets/PieWidget.vue'
import StackedBarWidget from './widgets/StackedBarWidget.vue'
import NumberWidget from './widgets/NumberWidget.vue'

const props = defineProps<{
  widget: DashboardWidget
  displayCurrency: string
  showActions?: boolean
}>()
</script>

<template>
  <div class="relative h-full w-full">
    <LineWidget
      v-if="props.widget.widget_type === 'line'"
      :widget="props.widget"
      :display-currency="props.displayCurrency"
    />
    <BarWidget
      v-else-if="props.widget.widget_type === 'bar'"
      :widget="props.widget"
      :display-currency="props.displayCurrency"
    />
    <PieWidget
      v-else-if="props.widget.widget_type === 'pie'"
      :widget="props.widget"
      :display-currency="props.displayCurrency"
    />
    <StackedBarWidget
      v-else-if="props.widget.widget_type === 'stacked_bar'"
      :widget="props.widget"
      :display-currency="props.displayCurrency"
    />
    <NumberWidget
      v-else-if="props.widget.widget_type === 'number'"
      :widget="props.widget"
      :display-currency="props.displayCurrency"
    />
    <div
      v-else
      class="flex items-center justify-center h-full text-sm text-dark-text-tertiary"
    >
      Tipo de widget desconocido: {{ props.widget.widget_type }}
    </div>
  </div>
</template>
