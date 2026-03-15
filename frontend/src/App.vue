<script setup lang="ts">
/**
 * Root Application Component
 *
 * Why this structure?
 * - AppLayout wraps all views with navigation
 * - RouterView renders the current route
 * - Toast notifications are global
 * - Single source of truth for layout
 *
 * noLayout support:
 * Routes with meta.noLayout = true (e.g. /login) render RouterView directly
 * without AppLayout. This allows the login view to have a minimal centered
 * layout without bottom navigation or any chrome.
 */

import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAccountsStore, useCategoriesStore } from '@/stores'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseToast from '@/components/ui/BaseToast.vue'

const route = useRoute()
const accountsStore = useAccountsStore()
const categoriesStore = useCategoriesStore()

// Load initial data on app mount
onMounted(async () => {
  // Fetch accounts and categories in parallel for faster initial load
  // Using Promise.allSettled instead of Promise.all so one failure doesn't block others
  const results = await Promise.allSettled([
    accountsStore.fetchAccounts(true), // Load only active accounts
    categoriesStore.fetchCategories()
  ])

  // Log any errors but don't block the app
  results.forEach((result, index) => {
    if (result.status === 'rejected') {
      const resource = index === 0 ? 'accounts' : 'categories'
      console.error(`Error loading ${resource}:`, result.reason)
    }
  })
})
</script>

<template>
  <div id="app" class="min-h-screen">
    <!-- Routes with noLayout (e.g. /login) render without AppLayout chrome -->
    <RouterView v-if="route.meta.noLayout" />

    <!-- All other routes use the full layout with bottom navigation -->
    <AppLayout v-else>
      <RouterView />
    </AppLayout>

    <!-- Global toast notifications -->
    <BaseToast />
  </div>
</template>
