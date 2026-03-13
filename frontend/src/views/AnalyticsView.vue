<script setup lang="ts">
import { onMounted } from 'vue'
import { useDashboardsStore } from '@/stores/dashboards'
import DashboardSelector from '@/components/analytics/DashboardSelector.vue'
import DashboardGrid from '@/components/analytics/DashboardGrid.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'

const store = useDashboardsStore()

onMounted(async () => {
  await store.ensureStarterDashboard()
  if (store.dashboards.length > 0 && !store.currentDashboard) {
    const defaultDash = store.dashboards.find(d => d.is_default) ?? store.dashboards[0]
    await store.fetchDashboard(defaultDash.id)
  }
})
</script>

<template>
  <div class="flex flex-col h-full bg-dark-bg-primary">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-dark-border">
      <h1 class="text-lg font-semibold text-dark-text-primary">Analytics</h1>
    </div>

    <!-- Dashboard Selector -->
    <DashboardSelector class="px-4 py-2" />

    <!-- Loading state -->
    <div v-if="store.loading && !store.currentDashboard" class="flex-1 flex items-center justify-center">
      <BaseSpinner />
    </div>

    <!-- Empty state (while ensureStarterDashboard runs) -->
    <div v-else-if="!store.currentDashboard" class="flex-1 flex items-center justify-center">
      <BaseSpinner />
    </div>

    <!-- Grid -->
    <DashboardGrid v-else class="flex-1 overflow-auto p-4" />
  </div>
</template>
