<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDashboardsStore } from '@/stores/dashboards'
import { useSettingsStore } from '@/stores/settings'
import DashboardSelector from '@/components/analytics/DashboardSelector.vue'
import DashboardGrid from '@/components/analytics/DashboardGrid.vue'
import DashboardCreateModal from '@/components/analytics/DashboardCreateModal.vue'
import DashboardSettingsModal from '@/components/analytics/DashboardSettingsModal.vue'
import BaseSpinner from '@/components/ui/BaseSpinner.vue'

const store = useDashboardsStore()
const settingsStore = useSettingsStore()

const showCreate = ref(false)
const showSettings = ref(false)

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
      <div class="flex items-center gap-2">
        <h1 class="text-lg font-semibold text-dark-text-primary">Analytics</h1>

        <!-- Settings icon: opens DashboardSettingsModal for the current dashboard.
             Only shown when a dashboard is loaded. Placed next to the title so
             the user can associate it with the current dashboard context.
             aria-label provides screen reader context for the icon-only button. -->
        <button
          v-if="store.currentDashboard"
          class="header-icon-btn"
          aria-label="Configuración del dashboard"
          @click="showSettings = true"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>

      <!-- "+" button: opens DashboardCreateModal.
           Placed in the trailing edge of the header — the conventional location
           for primary create actions on mobile (thumb-friendly far right). -->
      <button
        class="header-icon-btn"
        aria-label="Crear nuevo dashboard"
        @click="showCreate = true"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
      </button>
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

  <!-- Create modal — always mounted to avoid prop reactivity issues on first render -->
  <DashboardCreateModal
    :open="showCreate"
    :primary-currency="settingsStore.primaryCurrency"
    @close="showCreate = false"
  />

  <!-- Settings modal — only mounted when a dashboard is active (dashboardId required) -->
  <DashboardSettingsModal
    v-if="store.currentDashboard"
    :open="showSettings"
    :dashboard-id="store.currentDashboard.id"
    @close="showSettings = false"
  />
</template>

<style scoped>
/*
 * Icon-only header buttons.
 * 44×44px touch target (WCAG 2.5.5 / mobile-first requirement).
 * Subtle dark background on hover for visual feedback without
 * cluttering the minimalist header.
 */
.header-icon-btn {
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  color: #cbd5e1;
  background-color: transparent;
  border: none;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.header-icon-btn:hover {
  background-color: #334155;
  color: #f1f5f9;
}
</style>
