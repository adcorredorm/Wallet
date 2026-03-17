<script setup lang="ts">
interface Props {
  currentPage: number
  totalPages: number
  pageSize: number
}

const props = defineProps<Props>()
const emit = defineEmits<{ 'page-change': [page: number] }>()

function prev() {
  if (props.currentPage > 1) emit('page-change', props.currentPage - 1)
}
function next() {
  if (props.currentPage < props.totalPages) emit('page-change', props.currentPage + 1)
}
</script>

<template>
  <div
    v-if="totalPages > 1"
    class="flex items-center justify-between gap-4 py-4"
    role="navigation"
    aria-label="Paginación"
  >
    <button
      data-testid="pagination-prev"
      :disabled="currentPage <= 1"
      class="min-h-11 px-4 py-2 rounded-lg text-sm font-medium transition-colors
             bg-dark-bg-secondary text-dark-text-secondary
             disabled:opacity-40 disabled:cursor-not-allowed
             enabled:hover:bg-dark-bg-tertiary enabled:hover:text-dark-text-primary
             active:scale-95"
      aria-label="Página anterior"
      @click="prev"
    >
      Anterior
    </button>

    <span class="text-sm text-dark-text-secondary select-none">
      Página <span class="font-semibold text-dark-text-primary">{{ currentPage }}</span>
      de
      <span class="font-semibold text-dark-text-primary">{{ totalPages }}</span>
    </span>

    <button
      data-testid="pagination-next"
      :disabled="currentPage >= totalPages"
      class="min-h-11 px-4 py-2 rounded-lg text-sm font-medium transition-colors
             bg-dark-bg-secondary text-dark-text-secondary
             disabled:opacity-40 disabled:cursor-not-allowed
             enabled:hover:bg-dark-bg-tertiary enabled:hover:text-dark-text-primary
             active:scale-95"
      aria-label="Página siguiente"
      @click="next"
    >
      Siguiente
    </button>
  </div>
</template>
