<script setup lang="ts">
import { ref } from 'vue'
import PendingDropdown from './PendingDropdown.vue'

const props = defineProps<{
  count: number
}>()

const isOpen = ref(false)

function toggle() {
  isOpen.value = !isOpen.value
}

function close() {
  isOpen.value = false
}
</script>

<template>
  <div class="relative">
    <button
      class="relative p-2 hover:bg-dark-bg-tertiary rounded-lg transition-colors"
      style="min-width: 44px; min-height: 44px; display: flex; align-items: center; justify-content: center;"
      aria-label="Transacciones pendientes"
      @click="toggle"
    >
      <!-- Bell icon (Heroicons outline: bell) -->
      <svg class="w-6 h-6 text-dark-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>

      <!-- Red badge — only visible when count > 0 -->
      <span
        v-if="props.count > 0"
        class="absolute top-1 right-1 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center px-1 leading-none"
        style="min-width: 18px; height: 18px;"
      >
        {{ props.count > 99 ? '99+' : props.count }}
      </span>
    </button>

    <!-- Click-outside overlay (renders below dropdown) -->
    <div
      v-if="isOpen"
      class="fixed inset-0 z-30"
      @click="close"
    />

    <!-- Dropdown panel -->
    <PendingDropdown
      v-if="isOpen"
      @close="close"
    />
  </div>
</template>
