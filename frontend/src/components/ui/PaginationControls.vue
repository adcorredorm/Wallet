<script lang="ts">
import { defineComponent, h } from 'vue'

export default defineComponent({
  name: 'PaginationControls',

  props: {
    currentPage: {
      type: Number,
      required: true,
    },
    totalPages: {
      type: Number,
      required: true,
    },
    pageSize: {
      type: Number,
      required: true,
    },
  },

  emits: ['page-change'],

  setup(props, { emit }) {
    function prev() {
      if (props.currentPage > 1) emit('page-change', props.currentPage - 1)
    }
    function next() {
      if (props.currentPage < props.totalPages) emit('page-change', props.currentPage + 1)
    }

    return () => {
      if (props.totalPages <= 1) return null

      return h(
        'div',
        {
          class: 'flex items-center justify-between gap-4 py-4',
          role: 'navigation',
          'aria-label': 'Paginación',
        },
        [
          h(
            'button',
            {
              'data-testid': 'pagination-prev',
              disabled: props.currentPage <= 1,
              class: [
                'min-h-11 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                'bg-dark-bg-secondary text-dark-text-secondary',
                'disabled:opacity-40 disabled:cursor-not-allowed',
                'enabled:hover:bg-dark-bg-tertiary enabled:hover:text-dark-text-primary',
                'active:scale-95',
              ].join(' '),
              'aria-label': 'Página anterior',
              onClick: prev,
            },
            'Anterior',
          ),

          h('span', { class: 'text-sm text-dark-text-secondary select-none' }, [
            'Página ',
            h('span', { class: 'font-semibold text-dark-text-primary' }, String(props.currentPage)),
            ' de ',
            h('span', { class: 'font-semibold text-dark-text-primary' }, String(props.totalPages)),
          ]),

          h(
            'button',
            {
              'data-testid': 'pagination-next',
              disabled: props.currentPage >= props.totalPages,
              class: [
                'min-h-11 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                'bg-dark-bg-secondary text-dark-text-secondary',
                'disabled:opacity-40 disabled:cursor-not-allowed',
                'enabled:hover:bg-dark-bg-tertiary enabled:hover:text-dark-text-primary',
                'active:scale-95',
              ].join(' '),
              'aria-label': 'Página siguiente',
              onClick: next,
            },
            'Siguiente',
          ),
        ],
      )
    }
  },
})
</script>
