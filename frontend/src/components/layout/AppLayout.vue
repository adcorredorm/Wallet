<script setup lang="ts">
/**
 * App Layout Component - Updated with Side Drawer
 *
 * Why this layout?
 * - Mobile-first with optimized 3-item bottom navigation
 * - Side drawer for secondary navigation (Accounts, Categories)
 * - Header with hamburger/back button for intuitive navigation
 * - Consistent padding and safe areas
 *
 * Layout structure:
 * ┌─────────────────────────────┐
 * │ Header (Hamburger + Title)  │ ← AppHeader with HamburgerButton
 * ├─────────────────────────────┤
 * │                             │
 * │   Main Content Area         │ ← slot for views
 * │   (scrollable)              │
 * │                             │
 * ├─────────────────────────────┤
 * │ Bottom Nav (3 items)        │ ← AppNavigation (mobile only)
 * └─────────────────────────────┘
 *
 * When drawer opens:
 * ┌────────┬────────────────────┐
 * │ Drawer │ Dimmed Content     │ ← AppDrawer overlays with backdrop
 * │ Panel  │                    │
 * └────────┴────────────────────┘
 *
 * All screen sizes:
 * - Fixed bottom navigation (3 items: Home, Transactions, Transfers)
 * - Side drawer for Accounts & Categories
 * - Proper bottom padding for nav
 * - Max-width content container for readability on desktop
 */

import AppHeader from './AppHeader.vue'
import AppNavigation from './AppNavigation.vue'
import AppDrawer from './AppDrawer.vue'
// Phase 5: offline visibility banner — shown when device has no connectivity
import NetworkBanner from '@/components/sync/NetworkBanner.vue'
// Multiusuario: guest mode banner — shown when user is not authenticated
import GuestBanner from '@/components/sync/GuestBanner.vue'
</script>

<template>
  <div class="flex flex-col h-screen">
    <!--
      NetworkBanner (Phase 5)
      First flex child so it pushes the header and all content downward when
      visible. Uses a max-height collapse animation so the push-down is smooth
      rather than an instant layout jump.
    -->
    <NetworkBanner />

    <!--
      GuestBanner (Multiusuario)
      Shown when the user is online but not authenticated. Placed after
      NetworkBanner so that if both are visible at the same time (offline +
      guest — which shouldn't happen in normal flow, but is possible if the
      user goes offline while unauthenticated), NetworkBanner is on top as
      the higher-priority message.

      Why here and not inside the main content area?
      The banner is persistent and applies to the entire app, not to any
      specific view. Placing it in AppLayout (above the header) means it
      appears on every screen equally, following the same pattern as
      NetworkBanner. This avoids having to add it to every individual view.
    -->
    <GuestBanner />

    <!--
      Side Drawer
      Why Teleport? Drawer uses fixed positioning and needs to be at root level
      to overlay properly with correct z-index stacking
    -->
    <AppDrawer />

    <!-- Header with hamburger button and navigation -->
    <AppHeader class="flex-shrink-0" />

    <!--
      Main content area
      Why pb-24? Bottom nav is 64px (4rem) + safe area
      Prevents content from being hidden behind bottom nav
    -->
    <main class="flex-1 overflow-y-auto">
      <div class="container mx-auto px-4 py-6 pb-24 max-w-7xl">
        <slot />
      </div>
    </main>

    <!--
      Bottom navigation (all screen sizes)
      3 items for optimal UX
    -->
    <AppNavigation class="flex-shrink-0" />
  </div>
</template>
