<script setup lang="ts">
/**
 * Simple Floating Action Button (FAB) Component
 *
 * Why a separate component from FloatingActionButton?
 * - FloatingActionButton: Complex menu-based FAB for dashboard (multiple actions)
 * - SimpleFab: Single-action FAB for list views (create account, category, etc.)
 * - Keeping them separate follows Single Responsibility Principle
 * - Each can evolve independently without affecting the other
 *
 * Design decisions:
 * - 56x56px on mobile (Material Design standard, exceeds 44px minimum)
 * - 64x64px on desktop (larger screen allows for more prominent button)
 * - Bottom right position: Thumb-friendly for right-handed users
 * - 80px from bottom on mobile: Clears 64px bottom nav + 16px spacing
 * - 96px from bottom on desktop: More generous spacing
 * - z-index 50: Above content, same level as menu-based FAB
 *
 * Mobile-first approach:
 * - Base styles optimized for 320px+ screens
 * - Touch target exceeds 44x44px minimum
 * - Positioned in thumb-friendly zone
 * - Hover effects only apply on devices with hover capability
 */

import { computed } from 'vue'

/**
 * Props:
 * - ariaLabel: Accessibility label for screen readers (required)
 * - icon: Icon name to display ('plus', 'check', 'arrow-up', etc.)
 * - color: Background color ('blue', 'green', 'red', 'purple')
 */
interface Props {
  ariaLabel: string
  icon?: string
  color?: 'blue' | 'green' | 'red' | 'purple'
}

const props = withDefaults(defineProps<Props>(), {
  icon: 'plus',
  color: 'blue'
})

/**
 * Emit click event to parent
 * Parent component handles navigation or action
 */
const emit = defineEmits<{
  click: []
}>()

/**
 * Icon SVG paths (Heroicons)
 * Using inline SVG for performance and full styling control
 *
 * Why these specific icons?
 * - plus: Default, universal "create new" action
 * - check: Confirm actions
 * - arrow-up: Upload or submit actions
 * - pencil: Edit actions
 */
const icons: Record<string, string> = {
  plus: 'M12 4.5v15m7.5-7.5h-15',
  check: 'M4.5 12.75l6 6 9-13.5',
  'arrow-up': 'M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18',
  pencil: 'M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10'
}

/**
 * Compute color classes based on prop
 * This allows for flexible styling while maintaining consistency
 *
 * Why specific colors?
 * - Blue: Primary actions (create, new)
 * - Green: Success actions (confirm, save)
 * - Red: Destructive actions (delete, remove)
 * - Purple: Special actions (transfer, convert)
 */
const colorClasses = computed(() => {
  const colorMap = {
    blue: 'bg-accent-blue hover:bg-blue-600',
    green: 'bg-accent-green hover:bg-green-600',
    red: 'bg-accent-red hover:bg-red-600',
    purple: 'bg-purple-500 hover:bg-purple-600'
  }
  return colorMap[props.color]
})

function handleClick() {
  emit('click')
}
</script>

<template>
  <button
    class="simple-fab"
    :class="colorClasses"
    :aria-label="ariaLabel"
    @click="handleClick"
  >
    <!-- Icon SVG -->
    <svg
      class="w-6 h-6"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        :d="icons[icon]"
      />
    </svg>
  </button>
</template>

<style scoped>
/**
 * Simple FAB Base Styles
 *
 * Why fixed positioning?
 * - Must remain visible during scroll
 * - Always accessible regardless of content length
 * - Mobile-first pattern for primary actions
 *
 * Why bottom: 80px on mobile?
 * - Bottom nav height: 64px (4rem)
 * - Spacing: 16px for comfortable separation
 * - Total: 80px keeps FAB clear of bottom nav
 * - This prevents accidental nav bar touches when tapping FAB
 *
 * Why right: 16px on mobile?
 * - Material Design recommends 16dp margin
 * - Keeps button in thumb-friendly zone (right-handed users)
 * - Prevents accidental edge swipes on iOS
 * - Not too far that it's hard to reach with thumb
 *
 * Why z-index: 50?
 * - Above content (z-0 to z-10)
 * - Above most overlays (z-10 to z-40)
 * - Same as menu-based FAB for consistency
 * - Below modals (z-50+) if we add them later
 *
 * Why 56x56px on mobile?
 * - Material Design standard FAB size
 * - Exceeds 44px minimum touch target (WCAG compliance)
 * - Visually prominent without being overwhelming
 * - Comfortable for thumb tapping
 */
.simple-fab {
  /* Positioning */
  position: fixed;
  bottom: 80px;
  right: 16px;
  z-index: 50;

  /* Size and shape */
  width: 56px;
  height: 56px;
  border-radius: 50%;

  /* Text color (icon) */
  color: white;

  /* Elevation - creates depth on dark backgrounds */
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1),
              0 4px 6px -2px rgba(0, 0, 0, 0.05);

  /* Center icon */
  display: flex;
  align-items: center;
  justify-content: center;

  /* Smooth transitions for interactive feedback */
  transition: all 200ms ease;
}

/**
 * Hover state
 *
 * Why scale(1.05)?
 * - Subtle growth indicates interactivity
 * - 5% is noticeable but not jarring
 * - Common Material Design pattern
 *
 * Why increased shadow?
 * - Simulates button "lifting" off the surface
 * - Provides visual feedback that button is interactive
 * - Maintains dark mode compatibility
 *
 * Note: @media (hover: hover) ensures these effects only apply
 * on devices with hover capability (desktop, not touch screens)
 */
@media (hover: hover) {
  .simple-fab:hover {
    transform: scale(1.05);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1),
                0 10px 10px -5px rgba(0, 0, 0, 0.04);
  }
}

/**
 * Active state (pressed)
 *
 * Why scale(0.95)?
 * - Simulates button being "pressed down"
 * - Provides tactile feedback on touch screens
 * - 5% reduction is noticeable but not excessive
 *
 * Why reduced shadow?
 * - Button appears closer to surface when pressed
 * - Completes the "lift and press" interaction cycle
 * - Matches physical button behavior
 */
.simple-fab:active {
  transform: scale(0.95);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
              0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/**
 * Desktop adjustments
 *
 * Why change on desktop?
 * - More screen space allows for larger, more prominent button
 * - Increased spacing from edges looks better on large screens
 * - Desktop users have mouse precision, so larger target is a bonus
 *
 * Why bottom: 96px on desktop?
 * - Bottom nav is still 64px
 * - But we have more vertical space, so 32px spacing looks better
 * - Prevents FAB from feeling cramped against nav bar
 *
 * Why right: 32px on desktop?
 * - More generous spacing from edge
 * - Matches desktop design patterns
 * - Keeps button away from potential scrollbars
 *
 * Why 64x64px on desktop?
 * - Larger screen = larger button feels proportional
 * - Still comfortable for mouse clicks
 * - More prominent without overwhelming the UI
 */
@media (min-width: 768px) {
  .simple-fab {
    bottom: 96px;
    right: 32px;
    width: 64px;
    height: 64px;
  }
}
</style>
