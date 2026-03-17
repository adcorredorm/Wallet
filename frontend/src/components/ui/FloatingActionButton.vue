<script setup lang="ts">
/**
 * Floating Action Button (FAB) Component
 *
 * Why a FAB?
 * - Mobile-first pattern for primary actions
 * - Always accessible without scrolling
 * - Reduces dashboard clutter by removing button grid
 * - Material Design standard for mobile apps
 *
 * Design decisions:
 * - 56x56px size: Material Design standard, exceeds 44px minimum touch target
 * - Bottom right position: Thumb-friendly for right-handed users (majority)
 * - 16px margin: Comfortable distance from screen edges
 * - 80px from bottom: Clears 64px bottom nav + 16px spacing
 * - z-index 40: Above content but below bottom nav (z-45)
 *
 * Menu behavior:
 * - Appears above FAB with slide-up animation
 * - Click outside or on backdrop closes menu
 * - Each action navigates and auto-closes menu
 * - Touch-friendly 48px height menu items
 */

import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useUiStore } from '@/stores'

const router = useRouter()

interface Props {
  disabled?: boolean
}
const props = withDefaults(defineProps<Props>(), { disabled: false })
const uiStore = useUiStore()

const isMenuOpen = ref(false)

/**
 * Menu actions - Primary user workflows
 *
 * Why only 2 actions?
 * - Transaction: Most frequent action (income/expense recording)
 * - Transfer: Second most frequent (moving money between accounts)
 * - Account/Category creation moved to their respective list views
 */
const menuActions = [
  {
    id: 'transaction',
    label: 'Nueva Transacción',
    icon: 'plus-circle',
    path: '/transactions/new',
    color: 'text-accent-blue'
  },
  {
    id: 'transfer',
    label: 'Nueva Transferencia',
    icon: 'arrows-right-left',
    path: '/transfers/new',
    color: 'text-accent-green'
  }
]

/**
 * Toggle menu open/close
 * When opening, adds click listener to close on outside click
 */
function toggleMenu() {
  if (props.disabled) {
    uiStore.showWarning('Completa la configuración primero')
    return
  }
  isMenuOpen.value = !isMenuOpen.value
}

/**
 * Handle menu action click
 * Navigates to the target route and closes menu
 */
function handleAction(path: string) {
  router.push(path)
  isMenuOpen.value = false
}

/**
 * Close menu when clicking outside
 * This improves UX by allowing users to dismiss the menu naturally
 */
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.fab-container')) {
    isMenuOpen.value = false
  }
}

/**
 * Add click listener when menu opens
 * Remove when component unmounts to prevent memory leaks
 */
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

/**
 * SVG icon paths (Heroicons)
 * Using inline SVG for performance and full styling control
 */
const icons: Record<string, string> = {
  plus: 'M12 4.5v15m7.5-7.5h-15',
  'plus-circle': 'M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z',
  'arrows-right-left': 'M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5'
}
</script>

<template>
  <div class="fab-container">
    <!-- Menu backdrop (semi-transparent overlay when menu is open) -->
    <Transition name="fade">
      <div
        v-if="isMenuOpen"
        class="fab-backdrop"
        @click="isMenuOpen = false"
      />
    </Transition>

    <!-- Action menu (appears above FAB) -->
    <Transition name="slide-up">
      <div v-if="isMenuOpen" class="fab-menu">
        <button
          v-for="action in menuActions"
          :key="action.id"
          class="fab-menu-item"
          @click="handleAction(action.path)"
        >
          <!-- Icon -->
          <svg
            class="w-5 h-5"
            :class="action.color"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              :d="icons[action.icon]"
            />
          </svg>

          <!-- Label -->
          <span class="text-base font-medium">{{ action.label }}</span>
        </button>
      </div>
    </Transition>

    <!-- Main FAB button -->
    <button
      class="fab-button"
      :class="{ 'fab-button-open': isMenuOpen, 'fab-button-disabled': disabled }"
      @click.stop="toggleMenu"
      aria-label="Abrir menú de acciones rápidas"
    >
      <!-- Plus icon (rotates 45deg when open to form X) -->
      <svg
        class="w-6 h-6 transition-transform duration-200"
        :class="{ 'rotate-45': isMenuOpen }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          :d="icons.plus"
        />
      </svg>
    </button>
  </div>
</template>

<style scoped>
/**
 * FAB Container
 *
 * Why fixed positioning?
 * - Must remain visible during scroll
 * - Always accessible regardless of content length
 * - Mobile-first pattern for primary actions
 *
 * Why bottom: 80px?
 * - Bottom nav height: 64px (h-16 = 4rem)
 * - Spacing: 16px for comfortable separation
 * - Total: 80px keeps FAB clear of bottom nav
 *
 * Why right: 16px?
 * - Material Design recommends 16dp margin
 * - Keeps button in thumb-friendly zone
 * - Prevents accidental edge swipes on iOS
 *
 * Why z-index: 50?
 * - Above content (z-0)
 * - Above bottom nav (z-45)
 * - Primary action should always be accessible
 */
.fab-container {
  position: fixed;
  bottom: 80px;
  right: 16px;
  z-index: 50;
}

/**
 * FAB Button
 *
 * Why 56x56px (3.5rem)?
 * - Material Design standard FAB size
 * - Well above 44px minimum touch target
 * - Visually prominent without being overwhelming
 *
 * Why circular?
 * - Material Design standard
 * - Indicates interactive element
 * - Differentiates from rectangular buttons
 *
 * Shadow strategy:
 * - Base: Subtle elevation (shadow-lg)
 * - Hover: Increased elevation for feedback
 * - Active: Reduced elevation (pressed effect)
 */
.fab-button {
  @apply flex items-center justify-center;
  @apply w-14 h-14 rounded-full;
  @apply bg-accent-blue text-white;
  @apply shadow-lg hover:shadow-xl active:shadow-md;
  @apply transition-all duration-200;
  @apply hover:scale-105 active:scale-95;
}

/**
 * FAB open state
 * Adds visual feedback when menu is open
 */
.fab-button-open {
  @apply bg-accent-blue/90;
}

.fab-button-disabled {
  @apply bg-dark-bg-tertiary text-dark-text-secondary;
  @apply cursor-not-allowed;
  @apply shadow-none hover:shadow-none hover:scale-100 active:scale-100;
}

/**
 * Menu Backdrop
 *
 * Why full screen overlay?
 * - Dim content to focus on menu
 * - Provides click target to close menu
 * - Common mobile pattern for modal interactions
 *
 * Why z-index: -1 (relative to container)?
 * - Behind menu items but above content
 * - Container z-40 + relative -1 = effective z-39
 * - Ensures proper stacking without conflicts
 */
.fab-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.4);
  z-index: -1;
}

/**
 * Action Menu
 *
 * Why appear above FAB?
 * - User's thumb is already at bottom-right
 * - Menu slides up into view naturally
 * - Doesn't hide the FAB button
 *
 * Why bottom: 72px?
 * - FAB height: 56px
 * - Spacing: 16px for visual separation
 * - Total: 72px positions menu above FAB
 *
 * Why min-width: 240px?
 * - Comfortable space for Spanish text
 * - Prevents awkward wrapping
 * - Material Design recommends 240-280dp for menu width
 */
.fab-menu {
  position: absolute;
  bottom: 72px;
  right: 0;
  min-width: 240px;
  @apply bg-dark-bg-secondary rounded-lg shadow-xl;
  @apply border border-dark-border;
  @apply overflow-hidden;
}

/**
 * Menu Items
 *
 * Why 48px height?
 * - Exceeds 44px minimum touch target
 * - Material Design list item standard
 * - Comfortable for thumb tapping
 *
 * Why gap-3 (12px)?
 * - Comfortable spacing between icon and text
 * - Follows 8px grid system (12 = 8 + 4)
 * - Maintains visual balance
 */
.fab-menu-item {
  @apply flex items-center gap-3;
  @apply w-full px-4 py-3;
  @apply text-left text-dark-text-primary;
  @apply hover:bg-dark-bg-tertiary active:bg-dark-bg-tertiary/80;
  @apply transition-colors duration-150;
  min-height: 48px;
}

.fab-menu-item:not(:last-child) {
  @apply border-b border-dark-border;
}

/**
 * Animation: Fade
 * Used for backdrop appearance/disappearance
 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 200ms ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/**
 * Animation: Slide Up
 * Used for menu appearance/disappearance
 *
 * Why slide up?
 * - Natural motion from FAB to menu
 * - Follows user's thumb movement
 * - Common mobile pattern for contextual menus
 *
 * Why 200ms duration?
 * - Fast enough to feel responsive
 * - Slow enough to be perceived (not jarring)
 * - Material Design recommends 200-300ms
 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.95);
}

/**
 * Desktop adjustments
 * On larger screens, make FAB larger and keep it above bottom nav
 * Bottom nav is always visible (64px), so FAB needs clearance
 */
@media (min-width: 768px) {
  .fab-container {
    bottom: 96px;  /* 64px nav + 32px spacing for better desktop UX */
    right: 32px;   /* More spacing from edge on desktop */
  }

  .fab-button {
    @apply w-16 h-16;
  }

  .fab-menu {
    min-width: 280px;
  }
}
</style>
