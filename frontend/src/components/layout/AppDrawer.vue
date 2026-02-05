<script setup lang="ts">
/**
 * App Drawer Component
 *
 * Why a side drawer?
 * - Reduces bottom nav clutter (from 4 items to 3)
 * - Groups secondary navigation (Accounts, Categories)
 * - Follows Material Design and iOS patterns
 * - Preserves screen space when closed
 *
 * Mobile-first decisions:
 * - 280px width (optimal for content without overwhelming)
 * - Slides from left (standard convention)
 * - Overlay dims background (focuses attention)
 * - Touch outside to close (intuitive gesture)
 *
 * Technical implementation:
 * - transform: translateX() for GPU acceleration
 * - Fixed positioning for overlay above all content
 * - z-index: 50 (above content, below toasts)
 * - Smooth 250ms transitions synchronized with hamburger
 */

import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUiStore } from '@/stores'

const router = useRouter()
const uiStore = useUiStore()

/**
 * Navigation items for the drawer
 * These are secondary actions moved from bottom nav
 */
const drawerItems = [
  {
    name: 'accounts',
    label: 'Cuentas',
    icon: 'wallet',
    path: '/accounts',
    description: 'Gestiona tus cuentas bancarias'
  },
  {
    name: 'categories',
    label: 'Categorías',
    icon: 'tag',
    path: '/categories',
    description: 'Organiza tus gastos e ingresos'
  }
]

/**
 * SVG path data for icons
 * Using Heroicons outline style for consistency
 */
const icons: Record<string, string> = {
  wallet: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z',
  tag: 'M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z'
}

/**
 * Handle navigation item click
 * - Navigate to route
 * - Close drawer automatically
 */
function handleItemClick(path: string) {
  router.push(path)
  uiStore.closeDrawer()
}

/**
 * Close drawer when clicking overlay
 */
function handleOverlayClick() {
  uiStore.closeDrawer()
}

/**
 * Watch for route changes and close drawer
 * Why? User expects drawer to close after navigation
 */
watch(() => router.currentRoute.value.path, () => {
  if (uiStore.isDrawerOpen) {
    uiStore.closeDrawer()
  }
})

/**
 * Prevent body scroll when drawer is open
 * Why? Improves UX by preventing background scrolling
 */
watch(() => uiStore.isDrawerOpen, (isOpen) => {
  if (isOpen) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})
</script>

<template>
  <!--
    Drawer container
    Only rendered when open for better performance
  -->
  <Teleport to="body">
    <Transition name="drawer">
      <div
        v-if="uiStore.isDrawerOpen"
        class="drawer-container"
        role="dialog"
        aria-modal="true"
        aria-label="Menú de navegación"
      >
        <!-- Overlay: dims background and captures clicks -->
        <div
          class="drawer-overlay"
          @click="handleOverlayClick"
        />

        <!-- Drawer panel -->
        <nav class="drawer-panel">
          <!-- Header -->
          <div class="drawer-header">
            <h2 class="text-xl font-bold">
              Wallet
            </h2>
          </div>

          <!-- Navigation items -->
          <div class="drawer-nav">
            <button
              v-for="item in drawerItems"
              :key="item.name"
              class="drawer-item"
              @click="handleItemClick(item.path)"
            >
              <!-- Icon -->
              <div class="drawer-item-icon">
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
                    :d="icons[item.icon]"
                  />
                </svg>
              </div>

              <!-- Text content -->
              <div class="drawer-item-content">
                <span class="drawer-item-label">{{ item.label }}</span>
                <span class="drawer-item-description">{{ item.description }}</span>
              </div>

              <!-- Arrow indicator -->
              <svg
                class="w-5 h-5 text-dark-text-tertiary"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>

          <!-- Footer (optional - could add user info, settings, etc) -->
          <div class="drawer-footer">
            <p class="text-xs text-dark-text-tertiary text-center">
              Wallet v1.0
            </p>
          </div>
        </nav>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/**
 * Drawer Container
 * - Fixed positioning covers entire viewport
 * - High z-index (50) appears above content
 * - Flex layout for overlay + panel positioning
 */
.drawer-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  display: flex;
}

/**
 * Overlay
 * - Semi-transparent black dims background
 * - backdrop-blur creates depth perception
 * - Covers entire viewport
 * - Clicking closes drawer (handled in template)
 */
.drawer-overlay {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px); /* Safari support */
}

/**
 * Drawer Panel
 * - 280px width (optimal for mobile - not too wide, not cramped)
 * - Full height
 * - Dark mode background
 * - Shadow for depth
 * - Relative positioning for z-index stacking
 */
.drawer-panel {
  position: relative;
  width: 280px;
  height: 100%;
  background-color: #1e293b; /* dark-bg-secondary */
  box-shadow: 4px 0 12px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

/**
 * Drawer Header
 * - Padding for breathing room
 * - Border bottom for visual separation
 */
.drawer-header {
  padding: 1.5rem 1rem;
  border-bottom: 1px solid #334155; /* dark-border */
  flex-shrink: 0;
}

/**
 * Drawer Navigation Section
 * - Flex grow to fill available space
 * - Padding for touch-friendly spacing
 */
.drawer-nav {
  flex: 1;
  padding: 1rem 0.5rem;
}

/**
 * Drawer Item (Navigation Link)
 * - Full width button
 * - Min 56px height for touch targets (exceeds 44px minimum)
 * - Flex layout for icon + text + arrow
 * - Hover/active states for feedback
 */
.drawer-item {
  width: 100%;
  min-height: 56px;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  margin-bottom: 0.25rem;
  border-radius: 0.5rem;
  background: transparent;
  border: none;
  color: #f1f5f9; /* dark-text-primary */
  text-align: left;
  cursor: pointer;
  transition: background-color 150ms ease-in-out;
}

.drawer-item:hover {
  background-color: #334155; /* dark-bg-tertiary */
}

.drawer-item:active {
  background-color: #475569;
}

/**
 * Drawer Item Icon Container
 * - Fixed size for alignment
 * - Flex centering for icon
 */
.drawer-item-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  background-color: rgba(59, 130, 246, 0.1); /* accent-blue with low opacity */
  color: #3b82f6; /* accent-blue */
}

/**
 * Drawer Item Text Content
 * - Flex grow to fill space
 * - Column layout for label + description
 */
.drawer-item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.drawer-item-label {
  font-size: 0.9375rem; /* 15px - readable but compact */
  font-weight: 500;
  color: #f1f5f9; /* dark-text-primary */
}

.drawer-item-description {
  font-size: 0.75rem; /* 12px */
  color: #94a3b8; /* dark-text-tertiary */
}

/**
 * Drawer Footer
 * - Fixed at bottom
 * - Padding for spacing
 */
.drawer-footer {
  flex-shrink: 0;
  padding: 1rem;
  border-top: 1px solid #334155; /* dark-border */
}

/**
 * Drawer Transitions
 * - Slide in from left (translateX)
 * - Overlay fades in
 * - 250ms duration (synchronized with hamburger animation)
 * - ease-in-out for natural feel
 */

/* Entering transitions */
.drawer-enter-active {
  transition: opacity 250ms ease-in-out;
}

.drawer-enter-active .drawer-panel {
  transition: transform 250ms ease-in-out;
}

.drawer-enter-from {
  opacity: 0;
}

.drawer-enter-from .drawer-panel {
  transform: translateX(-100%);
}

/* Leaving transitions */
.drawer-leave-active {
  transition: opacity 250ms ease-in-out;
}

.drawer-leave-active .drawer-panel {
  transition: transform 250ms ease-in-out;
}

.drawer-leave-to {
  opacity: 0;
}

.drawer-leave-to .drawer-panel {
  transform: translateX(-100%);
}

/**
 * Desktop considerations
 * On larger screens, drawer could be wider or different behavior
 * For MVP: keeping mobile-first approach on all screens
 */
@media (min-width: 768px) {
  .drawer-panel {
    /* Could increase width on desktop */
    /* width: 320px; */
  }
}

/**
 * Focus state for accessibility
 * Drawer items show focus outline for keyboard navigation
 */
.drawer-item:focus-visible {
  outline: 2px solid #3b82f6; /* accent-blue */
  outline-offset: -2px;
}
</style>
