<script setup lang="ts">
/**
 * NetworkBanner — non-intrusive offline connectivity notice
 *
 * WHY THIS COMPONENT EXISTS
 * The app works fully offline (Phase 3/4 offline-first architecture). When
 * the device has no network, the user needs to know that their changes are
 * safe but not yet sent to the server. This banner provides that assurance
 * without blocking interaction or being alarming.
 *
 * WHY FIXED POSITIONING AT THE TOP?
 * On mobile the content area starts just below the header (64px / 4rem from
 * the top of the viewport). By using `fixed top-0` with z-index: 50, the
 * banner slides in above the header, pushing nothing — it overlays. This is
 * intentional: we do not want to shift the entire layout when connectivity
 * changes (layout shift is disorienting on mobile). The banner is thin (py-2
 * = 8px top+bottom + text = ~36px total) so it never covers meaningful
 * content.
 *
 * WHY <Transition> NOT v-show ALONE?
 * v-show would toggle visibility instantly, which feels abrupt on mobile.
 * <Transition> with a 300ms slide-down animation gives visual continuity —
 * the user perceives the banner as entering from above, which matches its
 * spatial position. The leave animation (slide back up) is equally brief.
 *
 * WHY AMBER INSTEAD OF RED?
 * "Offline" is not an error — it is a connectivity state the user may have
 * intentionally entered (airplane mode, underground commute). Red would
 * suggest something is broken and needs fixing. Amber communicates
 * "attention: something to be aware of" without creating alarm.
 *
 * WHY role="alert" + aria-live="polite"?
 * Screen readers must be told about connectivity changes. role="alert"
 * marks this as an ARIA live region. aria-live="polite" means the screen
 * reader will announce it after finishing the current speech, not interrupt.
 * We use "polite" rather than "assertive" because offline mode is not an
 * emergency — the app still works.
 *
 * WHY NOT INCLUDE A CLOSE BUTTON?
 * The banner should stay visible for as long as the device is offline. A
 * close button would let users dismiss it and then forget they are offline,
 * leading to confusion when they try to interact with features that require
 * connectivity. The banner auto-disappears when connectivity is restored.
 */

import { useSyncStore } from '@/stores/sync'

const syncStore = useSyncStore()
</script>

<template>
  <!--
    Why <Transition name="banner">?
    The CSS classes banner-enter-active / banner-leave-active (defined in
    <style scoped>) control the slide animation. Naming the transition "banner"
    avoids collision with any other <Transition> names in the app.
  -->
  <Transition name="banner">
    <div
      v-if="!syncStore.isOnline"
      role="alert"
      aria-live="polite"
      class="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium overflow-hidden"
      style="background-color: rgba(217, 119, 6, 0.95); color: #1c1917; backdrop-filter: blur(4px);"
    >
      <!--
        Wifi-off icon (inline SVG, Heroicons outline style)

        Why inline SVG?
        The project uses inline SVG throughout (see AppNavigation.vue,
        AppHeader.vue). No external icon library is imported. Inline SVG means
        no network request and full control over size/color via currentColor.

        Why 16x16 (w-4 h-4)?
        The banner is compact (py-2). A larger icon would force the banner
        taller, increasing the visual intrusion. 16px is readable and
        proportionate to the 14px (text-sm) label next to it.
      -->
      <svg
        class="w-4 h-4 flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <!--
          Wifi arc (upper arc of a typical wifi icon, rendered as a slash-through
          style using two paths: the wifi signal path + a diagonal slash)
        -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"
        />
        <!-- Diagonal slash through the wifi icon -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M3 3l18 18"
        />
      </svg>

      <!--
        Message text
        Why this specific wording?
        "Sin conexión" — clear, concise status.
        "Los cambios se guardan" — reassures the user their data is not lost.
        "y sincronizarán al reconectar" — explains what will happen automatically.
        This three-part message addresses the three user concerns: status,
        data safety, and resolution.
      -->
      <span>Sin conexión · Los cambios se guardan y sincronizarán al reconectar</span>
    </div>
  </Transition>
</template>

<style scoped>
/**
 * Banner push-down animation using max-height collapse.
 *
 * Why max-height instead of translateY?
 * The banner is now part of the normal flex flow (not fixed), so it pushes
 * the header and all content down when visible. translateY only moves the
 * element visually without affecting layout — it would not push the header.
 * max-height: 0 → 3rem collapses/expands the space the banner occupies,
 * creating a smooth push-down / retract-up effect.
 *
 * Why 3rem as the max-height target?
 * py-2 (8px top + 8px bottom) + text-sm (~20px) ≈ 36px. 3rem (48px) gives
 * a safe upper bound so the transition is never clipped early.
 *
 * overflow: hidden is required so content does not spill outside the
 * collapsing box during the animation.
 */
.banner-enter-active {
  transition: max-height 0.3s ease-out, opacity 0.3s ease-out;
}

.banner-leave-active {
  transition: max-height 0.25s ease-in, opacity 0.25s ease-in;
}

.banner-enter-from,
.banner-leave-to {
  max-height: 0;
  opacity: 0;
}

.banner-enter-to,
.banner-leave-from {
  max-height: 3rem;
  opacity: 1;
}
</style>
