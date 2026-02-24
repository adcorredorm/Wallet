/**
 * useNetworkStatus — reactive wrapper around VueUse's useOnline()
 *
 * Why a composable wrapper instead of calling useOnline() directly?
 * Two reasons:
 *
 *   1. Abstraction boundary: any consumer that needs "do X when back online"
 *      calls onOnline(callback) rather than writing its own watch(). This
 *      keeps the event-subscription boilerplate in one place, so if we ever
 *      switch from VueUse to a custom navigator.onLine listener the rest of
 *      the codebase doesn't change.
 *
 *   2. Discoverability: developers looking for network-aware patterns can find
 *      this composable by name rather than hunting for useOnline() call sites
 *      scattered across the codebase.
 *
 * Why re-export isOnline as a Ref<boolean> instead of a plain boolean?
 * A plain boolean would be a snapshot — it would not update when the device
 * goes offline or comes back online. Returning the Ref keeps the value
 * reactive: any component or composable that reads isOnline.value in a
 * computed() or template will automatically re-render when connectivity
 * changes.
 *
 * Why not use immediate: true on the watchers?
 * The callbacks are for transition events ("just came online", "just went
 * offline"). Firing them immediately on mount would be incorrect — a callback
 * named onOnline should only fire when the state transitions from false → true,
 * not when we simply observe that we're already online at startup. The
 * initialisation path in main.ts handles the "already online at boot" case
 * explicitly via isOnline.value.
 */

import { useOnline } from '@vueuse/core'
import { watch } from 'vue'

export function useNetworkStatus() {
  // useOnline() returns a shared global Ref<boolean> managed by VueUse.
  // Multiple calls to useOnline() return the exact same Ref — there is only
  // one global navigator.onLine listener registered regardless of how many
  // times this composable is instantiated.
  const isOnline = useOnline()

  /**
   * Register a callback that fires each time the device regains connectivity.
   *
   * The watcher is created with the default `immediate: false` so the callback
   * only fires on true transitions, not on the initial evaluation.
   *
   * @param callback - Function to call when the device comes back online.
   */
  function onOnline(callback: () => void): void {
    watch(isOnline, (online) => {
      if (online) callback()
    })
  }

  /**
   * Register a callback that fires each time the device loses connectivity.
   *
   * @param callback - Function to call when the device goes offline.
   */
  function onOffline(callback: () => void): void {
    watch(isOnline, (online) => {
      if (!online) callback()
    })
  }

  return { isOnline, onOnline, onOffline }
}
