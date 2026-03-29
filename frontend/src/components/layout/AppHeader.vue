<script setup lang="ts">
/**
 * App Header Component
 *
 * Why separate header?
 * - Consistent branding across all views
 * - Quick actions accessible from any page
 * - Mobile: Minimal, shows current page title + drawer access
 * - Desktop: Can show additional actions/search
 *
 * Updated for drawer navigation:
 * - Left side: Hamburger button (opens drawer) OR back button
 * - Hamburger button provides access to secondary navigation (Accounts, Categories)
 * - Back button takes precedence when showBackButton is true
 * - This reduces bottom nav clutter while maintaining accessibility
 */

import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '@/stores'
import HamburgerButton from '@/components/ui/HamburgerButton.vue'
// Phase 5: sync status indicator in the header right slot
import SyncIndicator from '@/components/sync/SyncIndicator.vue'
import NotificationBell from '@/components/recurring/NotificationBell.vue'
import { usePendingOccurrences } from '@/composables/usePendingOccurrences'

const route = useRoute()
const router = useRouter()
const uiStore = useUiStore()

const pendingHelper = usePendingOccurrences()

onMounted(async () => {
  await pendingHelper.loadOccurrences()
})

const pageTitle = computed(() => route.meta.title as string || 'Wallet')
const showBackButton = computed(() => route.meta.showBackButton as boolean || false)

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

/**
 * Toggle drawer state
 * Why? Provides access to secondary navigation without cluttering bottom nav
 */
function toggleDrawer() {
  uiStore.toggleDrawer()
}
</script>

<template>
  <header class="bg-dark-bg-secondary border-b border-dark-border">
    <div class="container mx-auto px-4 h-16 flex items-center justify-between max-w-7xl">
      <!--
        Left: Hamburger or Back button
        Why this priority?
        - Back button has precedence (critical navigation)
        - Hamburger visible on primary views (dashboard, lists)
        - Both are mutually exclusive to avoid clutter
      -->
      <div class="flex items-center gap-3">
        <!-- Back button (only on detail/edit views) -->
        <button
          v-if="showBackButton"
          class="p-2 hover:bg-dark-bg-tertiary rounded-lg transition-colors"
          aria-label="Volver"
          @click="goBack"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <!-- Hamburger button (primary views only) -->
        <HamburgerButton
          v-else
          :is-open="uiStore.isDrawerOpen"
          @click="toggleDrawer"
        />

        <!-- Logo/Title -->
        <h1 class="text-xl font-bold">
          {{ pageTitle }}
        </h1>
      </div>

      <!--
        Right: Sync indicator + future quick actions (notifications, profile)

        Why SyncIndicator here specifically?
        The right side of a mobile header is the conventional location for
        status/action icons (iOS: navigation bar trailing items, Android:
        toolbar overflow). Placing the sync indicator here is spatially
        consistent with those platform conventions, so users will intuitively
        scan this area for status information.

        The SyncIndicator is tap-to-reveal — it does not auto-expand or show
        text by default, keeping the header visually clean on mobile.
      -->
      <div class="flex items-center gap-2">
        <NotificationBell :count="pendingHelper.pendingCount.value" />
        <SyncIndicator />
      </div>
    </div>
  </header>
</template>
