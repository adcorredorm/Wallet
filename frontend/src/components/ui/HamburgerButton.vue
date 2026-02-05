<script setup lang="ts">
/**
 * Hamburger Button Component
 *
 * Why animated hamburger?
 * - Provides immediate visual feedback when drawer opens/closes
 * - Universal UX pattern (Material Design, iOS HIG)
 * - Reduces cognitive load: same button that opens also closes
 * - Smooth animation creates perception of fluid interaction
 *
 * Technical decisions:
 * - Uses CSS transforms (GPU-accelerated, 60fps on mobile)
 * - 250ms duration matches drawer animation for synchronization
 * - ease-in-out timing function feels natural
 * - No JavaScript animation (pure CSS for better performance)
 * - Touch target: 44x44px (Apple HIG minimum for mobile)
 */

interface Props {
  isOpen?: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  click: []
}>()

function handleClick() {
  emit('click')
}
</script>

<template>
  <button
    type="button"
    class="hamburger-button"
    :class="{ 'is-open': isOpen }"
    :aria-label="isOpen ? 'Cerrar menú' : 'Abrir menú'"
    :aria-expanded="isOpen"
    @click="handleClick"
  >
    <!--
      SVG with three lines that transform into X
      viewBox="0 0 24 24" gives us 24x24 coordinate system
      Lines are positioned at y=6, y=12, y=18 for even spacing
    -->
    <svg
      class="w-6 h-6"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <!-- Top line: rotates -45deg and moves down -->
      <line
        class="line-top"
        x1="4"
        y1="6"
        x2="20"
        y2="6"
      />

      <!-- Middle line: fades out -->
      <line
        class="line-middle"
        x1="4"
        y1="12"
        x2="20"
        y2="12"
      />

      <!-- Bottom line: rotates +45deg and moves up -->
      <line
        class="line-bottom"
        x1="4"
        y1="18"
        x2="20"
        y2="18"
      />
    </svg>
  </button>
</template>

<style scoped>
/**
 * Button Base Styles
 * - Min 44x44px for touch targets (Apple HIG)
 * - Flexbox centering for perfect alignment
 * - Rounded corners match dark mode aesthetic
 * - Hover state provides feedback on desktop
 */
.hamburger-button {
  /* Touch-friendly size */
  min-width: 44px;
  min-height: 44px;

  /* Flexbox centering */
  display: flex;
  align-items: center;
  justify-content: center;

  /* Visual style */
  padding: 0.625rem; /* 10px - provides spacing around 24px icon */
  border-radius: 0.5rem; /* 8px - soft corners */

  /* Interactive states */
  transition: background-color 150ms ease-in-out;
  cursor: pointer;

  /* Remove default button styles */
  border: none;
  background: transparent;
  color: inherit;
}

.hamburger-button:hover {
  /* Subtle hover state (dark mode) */
  background-color: rgb(51 65 85 / 0.5); /* dark-bg-tertiary with opacity */
}

.hamburger-button:active {
  /* Pressed state for immediate feedback */
  background-color: rgb(51 65 85 / 0.7);
}

/**
 * Line Animations
 * Default state (closed): Three horizontal lines
 * Open state: Transform into X shape
 *
 * Why these specific transforms?
 * - rotate() creates the diagonal lines
 * - translateY() moves lines to center (where middle line was)
 * - Origin is center of each line for smooth rotation
 */

/* Top line transformation */
.line-top {
  /* Default position */
  transform-origin: center;
  transition: transform 250ms ease-in-out;
}

.is-open .line-top {
  /* Rotates -45deg and moves to center */
  transform: rotate(-45deg) translateY(6px);
}

/* Middle line transformation */
.line-middle {
  /* Default visible */
  opacity: 1;
  transition: opacity 150ms ease-in-out;
}

.is-open .line-middle {
  /* Fades out completely */
  opacity: 0;
}

/* Bottom line transformation */
.line-bottom {
  /* Default position */
  transform-origin: center;
  transition: transform 250ms ease-in-out;
}

.is-open .line-bottom {
  /* Rotates +45deg and moves to center */
  transform: rotate(45deg) translateY(-6px);
}

/**
 * Focus state for accessibility
 * - Visible outline for keyboard navigation
 * - Uses accent color for consistency
 * - Offset prevents clipping
 */
.hamburger-button:focus-visible {
  outline: 2px solid #3b82f6; /* accent-blue */
  outline-offset: 2px;
}
</style>
