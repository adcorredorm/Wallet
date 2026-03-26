<script setup lang="ts">
/**
 * SyncIndicator — header sync status icon.
 *
 * For all states except 'error': tapping shows a status label tooltip.
 * For 'error': tapping shows an inline prompt with a "Revisar" link that
 * opens SyncErrorSheet.
 */

import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useSyncStatus } from '@/composables/useSyncStatus'
import { useSyncStore } from '@/stores/sync'

const { statusLabel, statusColor } = useSyncStatus()
const syncStore = useSyncStore()

const tooltipVisible = ref(false)

const isErrorState = computed(() => syncStore.syncStatus === 'error')

function toggleTooltip(): void {
  tooltipVisible.value = !tooltipVisible.value
}

function openErrorSheet(): void {
  tooltipVisible.value = false
  syncStore.setSyncErrorSheetOpen(true)
}

const containerRef = ref<HTMLElement | null>(null)

function handleOutsideClick(event: MouseEvent): void {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    tooltipVisible.value = false
  }
}

onMounted(() => { document.addEventListener('click', handleOutsideClick) })
onUnmounted(() => { document.removeEventListener('click', handleOutsideClick) })
</script>

<template>
  <div ref="containerRef" class="relative">
    <button
      type="button"
      class="flex items-center justify-center min-h-touch min-w-touch p-2 rounded-lg transition-colors hover:bg-dark-bg-tertiary"
      :aria-label="`Estado de sincronización: ${statusLabel}`"
      :aria-expanded="tooltipVisible"
      @click.stop="toggleTooltip"
    >
      <!-- SYNCED: green cloud with check -->
      <svg v-if="syncStore.syncStatus === 'synced'" class="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4" />
      </svg>

      <!-- SYNCING: blue rotating arrows -->
      <svg v-else-if="syncStore.syncStatus === 'syncing'" class="w-6 h-6 text-blue-400 syncing-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>

      <!-- PENDING: amber cloud with clock dot -->
      <svg v-else-if="syncStore.syncStatus === 'pending'" class="w-6 h-6 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 13V11m0 2h.01" />
      </svg>

      <!-- ERROR: red cloud with exclamation -->
      <svg v-else-if="syncStore.syncStatus === 'error'" class="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 11v2m0 2h.01" />
      </svg>

      <!-- OFFLINE / GUEST: gray cloud with slash -->
      <svg v-else class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l6 6" />
      </svg>
    </button>

    <Transition name="tooltip">
      <div
        v-if="tooltipVisible && !isErrorState"
        class="absolute top-full right-0 mt-1 z-40 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap pointer-events-none"
        :class="[statusColor, 'bg-dark-bg-secondary border border-dark-border shadow-lg']"
        role="tooltip"
      >
        {{ statusLabel }}
      </div>

      <!-- Error-state prompt: subtle two-line message with Revisar link -->
      <div
        v-else-if="tooltipVisible && isErrorState"
        class="absolute top-full right-0 mt-1 z-40 px-3 py-2 rounded-md text-xs bg-dark-bg-secondary border border-red-500/30 shadow-lg"
        role="tooltip"
      >
        <p class="text-dark-text-secondary mb-1 whitespace-nowrap">
          Hay {{ syncStore.errorCount }} error{{ syncStore.errorCount !== 1 ? 'es' : '' }} de sincronización.
        </p>
        <button
          type="button"
          class="text-red-400 hover:text-red-300 underline text-xs font-medium pointer-events-auto"
          @click.stop="openErrorSheet"
        >
          Revisar
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.syncing-spin {
  animation: spin 1s linear infinite;
  transform-origin: center;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-4px);
}
</style>
