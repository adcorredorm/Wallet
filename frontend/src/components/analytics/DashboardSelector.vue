<script setup lang="ts">
import { useDashboardsStore } from '@/stores/dashboards'

const store = useDashboardsStore()

async function selectDashboard(id: string) {
  await store.fetchDashboard(id)
}
</script>

<template>
  <div class="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
    <button
      v-for="dashboard in store.dashboards"
      :key="dashboard.id"
      class="flex-shrink-0 px-3 py-1.5 text-sm rounded-full transition-colors"
      :class="store.currentDashboard?.id === dashboard.id
        ? 'bg-indigo-500 text-white'
        : 'bg-dark-bg-tertiary text-dark-text-secondary hover:bg-dark-bg-secondary'"
      @click="selectDashboard(dashboard.id)"
    >
      {{ dashboard.name }}
    </button>
  </div>
</template>
