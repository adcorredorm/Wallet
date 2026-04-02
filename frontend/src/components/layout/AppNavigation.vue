<script setup lang="ts">
/**
 * App Navigation Component - Optimized for 3 Primary Actions
 *
 * Why only 3 items?
 * - Optimal for mobile UX (Apple HIG recommends 3-5, with 3-4 ideal)
 * - Reduces cognitive load and visual clutter
 * - Most frequently used actions get priority
 * - Secondary navigation (Accounts, Categories) moved to drawer
 *
 * Why these 3?
 * - Home: Always accessible return point
 * - Transactions: Most frequent action (recording income/expenses)
 * - Transfers: Second most frequent action (moving money between accounts)
 *
 * Where did Accounts go?
 * - Moved to side drawer (accessed via hamburger button)
 * - Still easily accessible but doesn't occupy prime bottom nav space
 * - Dashboard shows account overview anyway
 *
 * All screens: Fixed at bottom with safe area support (thumb-friendly)
 * Provides quick access to primary actions on all devices
 */

import { useRoute } from 'vue-router'

const route = useRoute()

/**
 * Primary navigation items
 * These are the most frequently accessed sections
 */
const navItems = [
  {
    name: 'dashboard',
    label: 'Inicio',
    icon: 'home',
    path: '/'
  },
  {
    name: 'transactions',
    label: 'Movimientos',
    icon: 'list',
    path: '/transactions'
  },
  {
    name: 'transfers',
    label: 'Transferencias',
    icon: 'transfer',
    path: '/transfers'
  }
]

function isActive(itemName: string): boolean {
  return route.name?.toString().startsWith(itemName) || false
}

/**
 * SVG icon paths (Heroicons outline style)
 * Using inline SVG for:
 * - Better performance (no external requests)
 * - Full control over styling
 * - Easy color changes with currentColor
 */
const icons: Record<string, string> = {
  home: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  list: 'M4 6h16M4 12h16M4 18h16',
  transfer: 'M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4',
  budget: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01'
}
</script>

<template>
  <!-- Fixed bottom navigation (all screen sizes) -->
  <nav class="nav-bottom fixed bottom-0 left-0 right-0 bg-dark-bg-secondary border-t border-dark-border pb-safe-bottom">
    <div class="flex items-center justify-around h-16">
      <router-link
        v-for="item in navItems"
        :key="item.name"
        :to="item.path"
        :class="[
          'flex flex-col items-center justify-center flex-1 h-full transition-colors',
          isActive(item.name)
            ? 'text-accent-blue'
            : 'text-dark-text-tertiary hover:text-dark-text-secondary'
        ]"
      >
        <!-- Icon -->
        <svg class="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="icons[item.icon]" />
        </svg>

        <!-- Label -->
        <span class="text-xs">{{ item.label }}</span>
      </router-link>
    </div>
  </nav>
</template>

<style scoped>
/**
 * Bottom Navigation Styles
 *
 * Why z-index: 45?
 * - Must be above content (z-index: auto/0)
 * - Must be above any modals or overlays that might cover it
 * - Must be below drawer overlay (z-index: 50)
 * - Ensures always accessible for navigation
 */
.nav-bottom {
  z-index: 45;
}
</style>
