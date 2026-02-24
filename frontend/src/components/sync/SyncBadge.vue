<script setup lang="ts">
/**
 * SyncBadge — tiny inline indicator for per-entity sync state
 *
 * WHY THIS COMPONENT EXISTS
 * The SyncIndicator in the header shows the aggregate sync health. But when
 * a user is looking at a list of transactions or accounts, they may want to
 * know *which specific items* have not been synced yet. This badge provides
 * that per-item visibility without adding text or extra UI chrome.
 *
 * WHY A 2×2 DOT (w-2 h-2)?
 * The badge must be visually minimal — it is a secondary signal that should
 * not compete with the item's primary content (name, amount, date). A 2×2
 * dot is the smallest size that is still perceptible on a mobile retina
 * display. It sits alongside the title and does not cause layout shifts.
 *
 * WHY ONLY SHOW FOR 'pending' AND 'error' (v-if status !== 'synced')?
 * If everything is synced, showing a badge would add visual noise for no
 * informational benefit. We only show the badge when there is something to
 * communicate: "this item is waiting to sync" (amber) or "this item failed
 * to sync" (red).
 *
 * WHY aria-hidden="true"?
 * The dot provides redundant visual information — the header SyncIndicator
 * already communicates aggregate sync state, and the badge has no meaningful
 * text to read. Screen reader users would hear "unlabelled dot" for every
 * item in a list, which is noisy and unhelpful. aria-hidden suppresses the
 * badge from the accessibility tree entirely. The title attribute still
 * provides a tooltip for sighted mouse users who hover over the badge.
 *
 * WHY flex-shrink-0?
 * Without this, flexbox may compress the badge on very narrow screens
 * (320px width), making it invisible. flex-shrink-0 guarantees the dot
 * always renders at its full 8×8px size.
 *
 * WHERE IS THIS USED?
 * It is placed inline next to the item title in:
 * - AccountCard.vue — next to account name
 * - TransactionItem.vue — next to transaction title/category
 * - TransfersListView.vue — next to transfer title
 * Each consumer passes :status="item._sync_status" from the LocalXxx type.
 */

import type { SyncStatus } from '@/offline/types'

defineProps<{
  /**
   * The sync status of the entity this badge belongs to.
   * Comes from the _sync_status field on LocalAccount, LocalTransaction,
   * LocalTransfer (all defined in offline/types.ts).
   */
  status: SyncStatus
}>()
</script>

<template>
  <!--
    Why v-if instead of v-show?
    When status === 'synced', the badge should not exist in the DOM at all —
    not just be hidden. v-if removes it completely, preventing any potential
    layout impact (even display: none occupies space as an inline-block element
    in some flex contexts). The list performance cost of v-if vs v-show is
    negligible for a 2×2 dot that has no async children.
  -->
  <span
    v-if="status !== 'synced'"
    :class="[
      'inline-block w-2 h-2 rounded-full flex-shrink-0',
      status === 'pending' ? 'bg-amber-400' : 'bg-red-400'
    ]"
    :title="status === 'pending' ? 'Pendiente de sincronización' : 'Error al sincronizar'"
    aria-hidden="true"
  />
</template>
