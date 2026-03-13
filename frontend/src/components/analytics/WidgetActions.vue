<script setup lang="ts">
/**
 * WidgetActions — Hover/tap overlay that surfaces positional and management
 * actions for a single dashboard widget.
 *
 * Why an overlay instead of a context menu or a separate panel?
 * The grid layout means widget cards are already space-constrained. An overlay
 * that appears only on hover (desktop) or on tap (mobile) adds zero clutter to
 * the default view. It is the same pattern used by Google Slides, Notion, and
 * Miro for item actions.
 *
 * Touch support:
 * On mobile there is no "hover". We use a local `tapped` ref toggled on click
 * of the widget's action trigger area. The overlay stays visible until the user
 * taps elsewhere (handled by a document click listener) or taps an action.
 *
 * Mobile-first touch target sizing:
 * Each icon button is 44x44px minimum. The four arrow buttons and two utility
 * buttons (resize, delete) are arranged in two rows for comfortable thumb reach.
 *
 * Arrow logic:
 * - ↑ decrements position_y (clamped to 0)
 * - ↓ increments position_y
 * - ← decrements position_x (clamped to 0)
 * - → increments position_x
 * Math.max(0, ...) prevents negative positions.
 *
 * Width cycling:
 * (current % 4) + 1 cycles 1→2→3→4→1. This is equivalent to modulo-4
 * arithmetic shifted by 1 so the range is 1–4 not 0–3.
 */

import { ref, onMounted, onUnmounted } from 'vue'
import ConfirmDialog from '@/components/shared/ConfirmDialog.vue'
import { useDashboardsStore } from '@/stores/dashboards'
import type { DashboardWidget } from '@/types/dashboard'

// ---------------------------------------------------------------------------
// Props & emits
// ---------------------------------------------------------------------------

const props = defineProps<{
  widget: DashboardWidget
  dashboardId: string
}>()

const emit = defineEmits<{
  edit: []
}>()

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

const store = useDashboardsStore()

// ---------------------------------------------------------------------------
// Touch-tap visibility state
// ---------------------------------------------------------------------------

// `visible` drives the overlay on mobile where hover doesn't exist.
// On desktop, CSS :hover on the parent widget-item handles visibility.
const visible = ref(false)
const showDeleteConfirm = ref(false)
const deleting = ref(false)
const moving = ref(false)
const resizing = ref(false)

function toggleVisible(e: Event) {
  e.stopPropagation()
  visible.value = !visible.value
}

function hideOverlay() {
  visible.value = false
}

// Close the overlay when the user taps/clicks outside the widget cell.
// We listen at the document level and hide unless the click was inside
// the overlay itself (stopPropagation handles that).
onMounted(() => {
  document.addEventListener('click', hideOverlay)
})

onUnmounted(() => {
  document.removeEventListener('click', hideOverlay)
})

// ---------------------------------------------------------------------------
// Action handlers
// ---------------------------------------------------------------------------

async function move(dx: number, dy: number) {
  moving.value = true
  try {
    await store.updateWidget(props.dashboardId, props.widget.id, {
      position_x: Math.max(0, props.widget.position_x + dx),
      position_y: Math.max(0, props.widget.position_y + dy),
    })
  } catch (e) {
    console.error('Error moving widget:', e)
  } finally {
    moving.value = false
  }
}

async function cycleWidth() {
  resizing.value = true
  try {
    const next = (props.widget.width % 4) + 1
    await store.updateWidget(props.dashboardId, props.widget.id, { width: next })
  } catch (e) {
    console.error('Error resizing widget:', e)
  } finally {
    resizing.value = false
  }
}

async function onConfirmDelete() {
  deleting.value = true
  try {
    await store.deleteWidget(props.dashboardId, props.widget.id)
    showDeleteConfirm.value = false
  } catch (e) {
    console.error('Error deleting widget:', e)
  } finally {
    deleting.value = false
  }
}

function onEdit() {
  visible.value = false
  emit('edit')
}
</script>

<template>
  <!--
    The overlay wrapper occupies the same bounding box as the parent widget cell
    (position: absolute, inset-0). Parent must be position: relative.

    Visibility strategy:
    - CSS class `is-visible` is toggled when `visible` is true (touch tap).
    - On md+ the parent widget-item's :hover in DashboardGrid.vue CSS adds
      the overlay visibility via the `.widget-item:hover .widget-actions` rule
      (see DashboardGrid scoped styles).
    - Both mechanisms use the same `opacity/pointer-events` CSS pair so there
      is no JS duplication.
  -->
  <div
    class="widget-actions"
    :class="{ 'is-visible': visible }"
    @click.stop
  >
    <!-- Tap-to-show trigger (mobile) — a small handle in the top-right corner.
         On desktop this is hidden because :hover on the parent handles reveal. -->
    <button
      class="action-trigger"
      aria-label="Mostrar acciones del widget"
      @click="toggleVisible"
    >
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
        <circle cx="12" cy="5" r="1.5" />
        <circle cx="12" cy="12" r="1.5" />
        <circle cx="12" cy="19" r="1.5" />
      </svg>
    </button>

    <!-- Action buttons panel -->
    <div class="actions-panel">
      <!-- Row 1: directional arrows -->
      <div class="arrow-grid">
        <!-- ↑ Move up -->
        <button
          class="icon-btn"
          :disabled="moving || widget.position_y === 0"
          aria-label="Mover arriba"
          @click="move(0, -1)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
          </svg>
        </button>

        <!-- ← Move left -->
        <button
          class="icon-btn"
          :disabled="moving || widget.position_x === 0"
          aria-label="Mover izquierda"
          @click="move(-1, 0)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <!-- ↓ Move down -->
        <button
          class="icon-btn"
          :disabled="moving"
          aria-label="Mover abajo"
          @click="move(0, 1)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <!-- → Move right -->
        <button
          class="icon-btn"
          :disabled="moving"
          aria-label="Mover derecha"
          @click="move(1, 0)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      <!-- Row 2: utility actions -->
      <div class="utility-row">
        <!-- Resize: cycle width 1→2→3→4→1 -->
        <button
          class="icon-btn"
          :disabled="resizing"
          :aria-label="`Ancho actual: ${widget.width}. Cambiar ancho`"
          @click="cycleWidth"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3" />
          </svg>
          <span class="width-badge">{{ widget.width }}</span>
        </button>

        <!-- Edit: open WidgetConfigModal -->
        <button
          class="icon-btn"
          aria-label="Editar widget"
          @click="onEdit"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>

        <!-- Delete: opens ConfirmDialog -->
        <button
          class="icon-btn icon-btn--danger"
          aria-label="Eliminar widget"
          @click="showDeleteConfirm = true"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  </div>

  <!-- Delete confirmation dialog -->
  <ConfirmDialog
    :show="showDeleteConfirm"
    title="Eliminar widget"
    message="¿Eliminar este widget del dashboard?"
    confirm-text="Eliminar"
    :loading="deleting"
    variant="danger"
    @confirm="onConfirmDelete"
    @cancel="showDeleteConfirm = false"
  />
</template>

<style scoped>
/*
 * Overlay container: absolute, covers the full widget cell.
 * Default: opacity 0 and pointer-events none so it is invisible and
 * non-interactive. The two reveal mechanisms are:
 *   1. .is-visible class (toggled by JS for mobile tap)
 *   2. Parent .widget-item:hover rule in DashboardGrid.vue (desktop)
 *
 * We cannot use :hover here on .widget-actions itself because the mouse
 * must be on the PARENT widget item, not just the overlay.
 */
.widget-actions {
  position: absolute;
  inset: 0;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
  /* Semi-transparent dark scrim so the panel is readable over any chart */
  background: linear-gradient(135deg, rgba(15,23,42,0.6) 0%, rgba(15,23,42,0.3) 100%);
  border-radius: inherit;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 0.375rem;
  gap: 0.25rem;
}

.widget-actions.is-visible {
  opacity: 1;
  pointer-events: auto;
}

/*
 * Tap trigger (the three-dot menu handle visible before the overlay).
 * On mobile it is always visible as a small affordance. On desktop hover
 * makes the whole overlay appear, so the trigger is hidden after reveal.
 */
.action-trigger {
  position: absolute;
  top: 0.375rem;
  right: 0.375rem;
  min-width: 28px;
  min-height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  background-color: rgba(15, 23, 42, 0.75);
  color: #cbd5e1;
  border: none;
  cursor: pointer;
  /* Always visible so mobile users know they can tap for actions */
  opacity: 1;
  pointer-events: auto;
  z-index: 1;
  transition: background-color 0.15s ease;
}

.action-trigger:hover {
  background-color: rgba(51, 65, 85, 0.9);
  color: #f1f5f9;
}

/* Actions panel: the button container */
.actions-panel {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  align-items: flex-end;
}

/*
 * Arrow grid: 2x2 layout using CSS Grid.
 * The four directional arrows map to compass directions.
 * Grid areas: top-center, middle-left, middle-right, bottom-center.
 */
.arrow-grid {
  display: grid;
  grid-template-columns: repeat(3, 44px);
  grid-template-rows: repeat(3, 44px);
  /* Arrows only fill the edge positions, center is empty */
}

/*
 * Arrow placement in the 3×3 grid:
 * Row 1 col 2: ↑ (up)
 * Row 2 col 1: ← (left)
 * Row 2 col 3: → (right)
 * Row 3 col 2: ↓ (down)
 */
.arrow-grid .icon-btn:nth-child(1) { grid-area: 1 / 2; }  /* ↑ */
.arrow-grid .icon-btn:nth-child(2) { grid-area: 2 / 1; }  /* ← */
.arrow-grid .icon-btn:nth-child(3) { grid-area: 3 / 2; }  /* ↓ */
.arrow-grid .icon-btn:nth-child(4) { grid-area: 2 / 3; }  /* → */

/* Utility row: resize, edit, delete side-by-side */
.utility-row {
  display: flex;
  gap: 0.25rem;
}

/*
 * Base icon button.
 * 44×44px guarantees WCAG 2.5.5 touch target size on mobile.
 * Rounded corners and dark semi-transparent background for readability
 * over chart content.
 */
.icon-btn {
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  border-radius: 0.5rem;
  background-color: rgba(30, 41, 59, 0.85);
  color: #cbd5e1;
  border: 1px solid rgba(51, 65, 85, 0.6);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  font-size: 0.7rem;
  position: relative;
}

.icon-btn:hover:not(:disabled) {
  background-color: rgba(51, 65, 85, 0.95);
  color: #f1f5f9;
}

.icon-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.icon-btn--danger:hover:not(:disabled) {
  background-color: rgba(239, 68, 68, 0.25);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.4);
}

/*
 * Width badge: a tiny number overlay on the resize button showing the
 * current width value so users understand what they are cycling.
 */
.width-badge {
  font-size: 0.65rem;
  font-weight: 700;
  color: #3b82f6;
  line-height: 1;
}
</style>
