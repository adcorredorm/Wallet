<script setup lang="ts">
/**
 * SyncIndicator — header sync status icon with tooltip label
 *
 * WHY THIS COMPONENT EXISTS
 * The NetworkBanner communicates "you are offline" — a binary, high-priority
 * state. The SyncIndicator communicates a richer 5-state status (offline,
 * syncing, pending, error, synced) in a compact, always-visible form in the
 * app header. It gives power users at-a-glance visibility into the sync
 * health without taking screen space or interrupting workflow.
 *
 * WHY A CLOUD ICON?
 * The cloud metaphor is universally understood to represent sync/cloud storage
 * (iOS Files, Google Drive, Dropbox all use it). A cloud with modifications
 * (rotating arrows, check, exclamation, slash) communicates the sub-state
 * clearly without words.
 *
 * WHY INLINE SVG INSTEAD OF AN ICON LIBRARY?
 * The project uses inline SVG throughout (AppNavigation, AppHeader). No icon
 * library is installed. The cloud SVG here is a minimal 24x24 Heroicons-style
 * path that matches the visual style of the rest of the app's icons.
 *
 * WHY A TOGGLE-ON-CLICK TOOLTIP INSTEAD OF CSS HOVER?
 * On mobile, hover states don't exist. Tap-to-reveal is the mobile-native
 * pattern for "see more info". The tooltip appears on tap and dismisses on
 * a second tap or when the user taps anywhere else (via a global click
 * listener registered in onMounted). This provides the same discoverability
 * on desktop (hover-like) and touch devices (tap-to-reveal).
 *
 * WHY 24x24 (w-6 h-6) ICON SIZE?
 * The header is 64px tall (h-16). The back/hamburger buttons also use w-6 h-6
 * icons (see AppHeader.vue). Matching their size keeps the header visually
 * consistent.
 *
 * TOUCH TARGET SIZE
 * The button wrapper is `min-h-touch min-w-touch` (44x44px as per
 * tailwind.config.js), satisfying Apple HIG and WCAG 2.5.5 for touch targets.
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { useSyncStatus } from '@/composables/useSyncStatus'

const { syncStatus, statusLabel, statusColor } = useSyncStatus()

/**
 * Tooltip visibility toggle.
 * Why ref(false)? We want the tooltip hidden by default. The user explicitly
 * taps to reveal it. This is more intentional than auto-showing on mount.
 */
const tooltipVisible = ref(false)

function toggleTooltip(): void {
  tooltipVisible.value = !tooltipVisible.value
}

/**
 * Hide the tooltip when the user taps outside this component.
 * Why a global click handler?
 * On mobile, the standard way to dismiss floating UI elements (tooltips,
 * dropdowns) is to tap anywhere outside them. Capturing the document click
 * event and checking if it's outside our element achieves this. We use
 * `capture: false` (the default) so regular DOM propagation applies.
 */
const containerRef = ref<HTMLElement | null>(null)

function handleOutsideClick(event: MouseEvent): void {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    tooltipVisible.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
})

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick)
})
</script>

<template>
  <!--
    Container ref: used by handleOutsideClick to detect taps outside this
    component. position: relative so the tooltip can be absolutely positioned
    relative to this container.
  -->
  <div ref="containerRef" class="relative">
    <!--
      Button wrapper for touch target size compliance (44x44px minimum).
      Why type="button"? Prevents accidental form submission if this component
      is ever placed inside a form element.
    -->
    <button
      type="button"
      class="flex items-center justify-center min-h-touch min-w-touch p-2 rounded-lg transition-colors hover:bg-dark-bg-tertiary"
      :aria-label="`Estado de sincronización: ${statusLabel}`"
      :aria-expanded="tooltipVisible"
      @click.stop="toggleTooltip"
    >
      <!--
        Cloud icon with state-specific overlay indicator.
        Each state renders the same cloud base plus a small badge/overlay:
        - synced:  green cloud with a check mark path
        - syncing: blue cloud with rotating arrows (CSS animation)
        - pending: amber cloud with a clock dot indicator
        - error:   red cloud with an exclamation mark
        - offline: gray cloud with a slash through it
      -->

      <!-- SYNCED: green cloud with check -->
      <svg
        v-if="syncStatus === 'synced'"
        class="w-6 h-6 text-green-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <!-- Cloud body -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"
        />
        <!-- Check mark inside cloud -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 12l2 2 4-4"
        />
      </svg>

      <!-- SYNCING: blue cloud with rotating arrows -->
      <svg
        v-else-if="syncStatus === 'syncing'"
        class="w-6 h-6 text-blue-400 syncing-spin"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <!--
          Why a circular arrows path instead of animating the cloud?
          Rotating the entire cloud looks odd because clouds are not rotationally
          symmetric. A circular arrows icon (refresh/sync) is the established
          metaphor for "loading / in progress" and rotates beautifully.
          The CSS animation class `syncing-spin` applies a continuous 360deg
          rotation defined in <style scoped>.
        -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      </svg>

      <!-- PENDING: amber cloud with small dot (clock-like waiting state) -->
      <svg
        v-else-if="syncStatus === 'pending'"
        class="w-6 h-6 text-amber-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <!-- Cloud body -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"
        />
        <!-- Clock hands inside cloud to indicate "waiting" -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 13V11m0 2h.01"
        />
      </svg>

      <!-- ERROR: red cloud with exclamation -->
      <svg
        v-else-if="syncStatus === 'error'"
        class="w-6 h-6 text-red-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <!-- Cloud body -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"
        />
        <!-- Exclamation mark: vertical stroke + dot -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 11v2m0 2h.01"
        />
      </svg>

      <!-- OFFLINE: gray cloud with slash -->
      <svg
        v-else
        class="w-6 h-6 text-slate-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <!-- Cloud body (muted gray) -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"
        />
        <!-- Diagonal slash to indicate unavailable/disconnected -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 12l6 6"
        />
      </svg>
    </button>

    <!--
      Tooltip: shows statusLabel on tap/click.

      WHY ABSOLUTE POSITIONING + right-0?
      The indicator is in the right side of the header (see AppHeader.vue
      right-side slot). Anchoring the tooltip to right-0 of the indicator
      container prevents it from overflowing off-screen on the right edge,
      which is a common mobile issue with tooltips that open to the right.

      WHY top-full + mt-1 (not top-0)?
      We want the tooltip below the button, not overlapping it. top-full
      positions the tooltip just below the button's bottom edge. mt-1 adds 4px
      of gap so the tooltip doesn't appear glued to the button.

      WHY z-40?
      The header is at the top of the layout stack. The tooltip should appear
      above the header content (z-auto/0) but below the side drawer overlay
      (z-50, per AppNavigation z-45 comment) and below the NetworkBanner (z-50).
      z-40 achieves this without conflicting with other layers.

      WHY whitespace-nowrap?
      The status labels can be multi-word (e.g. "Sincronizando...") on narrow
      screens. whitespace-nowrap prevents the tooltip from wrapping mid-label,
      which would make it taller and harder to read.
    -->
    <Transition name="tooltip">
      <div
        v-if="tooltipVisible"
        class="absolute top-full right-0 mt-1 z-40 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap pointer-events-none"
        :class="[
          statusColor,
          'bg-dark-bg-secondary border border-dark-border shadow-lg'
        ]"
        role="tooltip"
      >
        {{ statusLabel }}
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/**
 * Syncing rotation animation
 *
 * Why transform-origin: center?
 * SVG elements rotate around their own center by default in CSS (unlike SVG's
 * rotate attribute which rotates around the SVG origin 0,0). Setting
 * transform-origin explicitly ensures the icon spins around its visual center.
 *
 * Why 1s linear infinite?
 * 1 second per rotation is fast enough to communicate "active work" but slow
 * enough not to feel frantic. linear easing produces uniform rotation speed,
 * which matches the "continuous background process" nature of syncing (as
 * opposed to ease-in-out which would imply discrete bursts).
 */
.syncing-spin {
  animation: spin 1s linear infinite;
  transform-origin: center;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/**
 * Tooltip fade-scale animation
 *
 * Why scale + opacity instead of just opacity?
 * The combined scale(0.95) → scale(1) with opacity 0 → 1 creates a subtle
 * "pop" effect that matches mobile UI conventions (iOS tooltips, Android
 * snackbars). Pure opacity fade looks flat. The scale is subtle enough (0.95)
 * not to be distracting.
 *
 * Why 150ms?
 * Shorter than the banner animation (300ms) because a tooltip is a secondary
 * UI element. Fast enough to feel responsive to the tap that triggers it.
 */
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
