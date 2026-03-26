<script setup lang="ts">
/**
 * SyncErrorItem — one row in the SyncErrorSheet error list.
 */

import { computed } from 'vue'

const props = defineProps<{
  entityType: string
  entityId: string
  entityLabel: string
  errorReason: string
  dependentCount: number
  discarding: boolean
}>()

const emit = defineEmits<{
  (e: 'discard'): void
}>()

const typeLabel = computed(() => {
  const map: Record<string, string> = {
    account: 'Cuenta',
    transaction: 'Transacción',
    transfer: 'Transferencia',
    category: 'Categoría',
    dashboard: 'Dashboard',
    dashboard_widget: 'Widget',
    setting: 'Ajuste',
  }
  return map[props.entityType] ?? props.entityType
})
</script>

<template>
  <div class="flex flex-col gap-1 py-3 border-b border-dark-border last:border-0">
    <!-- Entity type + label -->
    <div class="flex items-start justify-between gap-2">
      <div class="flex flex-col gap-0.5 flex-1 min-w-0">
        <span class="text-xs font-medium text-red-400 uppercase tracking-wide">{{ typeLabel }}</span>
        <span class="text-sm text-dark-text-primary truncate">{{ entityLabel }}</span>
        <span class="text-xs text-dark-text-secondary truncate">{{ errorReason }}</span>
        <span v-if="dependentCount > 0" class="text-xs text-amber-400">
          + {{ dependentCount }} registro{{ dependentCount !== 1 ? 's' : '' }} relacionado{{ dependentCount !== 1 ? 's' : '' }}
        </span>
      </div>

      <!-- Discard button -->
      <button
        type="button"
        class="flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors min-h-[36px] min-w-[80px]"
        style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #fca5a5;"
        :disabled="discarding"
        @click="emit('discard')"
      >
        {{ discarding ? '...' : 'Descartar' }}
      </button>
    </div>
  </div>
</template>
