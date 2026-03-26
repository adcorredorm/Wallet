<script setup lang="ts">
/**
 * GuestBanner — persistent banner shown when the user is not authenticated.
 *
 * WHY THIS COMPONENT EXISTS
 * The app works fully offline (offline-first architecture). A user can create
 * accounts, transactions, and transfers without logging in — all data lives
 * in IndexedDB locally. However, those changes will NOT be backed up to the
 * cloud until the user authenticates. This banner provides that important
 * information so the user understands the trade-off.
 *
 * WHY AMBER/YELLOW INSTEAD OF RED?
 * This is an informational state, not an error. The user can use the app
 * normally in guest mode — their data is safe locally. Amber communicates
 * "this is worth knowing" without suggesting something is broken.
 *
 * WHY NOT AMBER LIKE NetworkBanner?
 * NetworkBanner also uses amber, but they represent different states:
 * - NetworkBanner: amber with dark text — the device is completely offline
 * - GuestBanner: amber/yellow with light text, border-based — online but
 *   not syncing due to lack of auth. Visually similar tone but distinct
 *   enough that a user who sees both can differentiate them.
 *
 * WHY NOT HAVE A CLOSE BUTTON?
 * The guest state is permanent until the user logs in. A close button would
 * let them dismiss it and then forget they are in guest mode, leading to
 * confusion when changes are lost. The banner auto-hides when they log in
 * (isAuthenticated becomes true).
 *
 * MOBILE-FIRST DECISIONS
 * - Full width: occupies the full layout width so it's impossible to miss
 * - Text wraps naturally: no truncation on narrow screens (320px)
 * - "Iniciar sesión" is a RouterLink — navigates to /login
 * - Padding px-4 py-2 keeps the banner compact but touch-accessible
 *
 * ACCESSIBILITY
 * - role="alert" + aria-live="polite": announces to screen readers when
 *   the banner appears (e.g., after the store initializes async).
 *   "polite" because this is informational, not an emergency interruption.
 */

import { useAuthStore } from '@/stores/auth'
import { RouterLink } from 'vue-router'

const authStore = useAuthStore()
</script>

<template>
  <!--
    Why <Transition name="banner">?
    Same animation approach as NetworkBanner: max-height collapse/expand
    so the banner pushes the header and content down when it appears,
    rather than overlaying (which would cover content on small screens).
  -->
  <Transition name="banner">
    <div
      v-if="!authStore.hasSession"
      role="alert"
      aria-live="polite"
      class="w-full flex items-center justify-between gap-3 px-4 py-2 text-sm overflow-hidden"
      style="background-color: rgba(120, 53, 15, 0.4); border-bottom: 1px solid rgba(245, 158, 11, 0.4); color: #fde68a;"
    >
      <!--
        Message + icon wrapper
        Why flex with gap-2?
        On mobile (320px), the text and icon need to sit on the same line
        without overlapping. flex handles this gracefully and the text
        wraps naturally if the screen is very narrow.
      -->
      <div class="flex items-start gap-2 flex-1 min-w-0">
        <!--
          Warning icon (Heroicons outline, 16px)
          Why inline SVG?
          No external icon library is imported in this project. Inline SVG
          gives full control over size and color via currentColor.

          Why aria-hidden="true"?
          The icon is decorative — the text conveys the full meaning.
          Screen readers will read the banner text, not describe the icon.
        -->
        <svg
          class="w-4 h-4 flex-shrink-0 mt-0.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>

        <span class="leading-snug">
          Los cambios realizados no serán guardados en la nube.
          Inicia sesión para sincronizar tus datos.
        </span>
      </div>

      <!--
        "Iniciar sesión" link

        Why RouterLink instead of a button with router.push()?
        RouterLink renders as an <a> element, which is semantically correct
        for navigation and accessible by default (keyboard, screen readers).
        It also shows the destination URL in the browser status bar on hover,
        giving the user a preview of where they'll go.

        Why min-h-[44px] and flex items-center?
        WCAG and Apple HIG require minimum 44px touch target height. The
        banner is compact (~36px tall), so we use min-h-[44px] on the link
        to expand its touch area beyond the visible text without increasing
        the banner height.
      -->
      <RouterLink
        to="/login"
        class="flex-shrink-0 flex items-center min-h-[44px] px-2 font-medium underline
               transition-opacity duration-150 hover:opacity-80 focus:outline-none
               focus:ring-2 focus:ring-amber-400/50 rounded"
        style="color: #fbbf24;"
        aria-label="Ir a la página de inicio de sesión"
      >
        Iniciar sesión
      </RouterLink>
    </div>
  </Transition>
</template>

<style scoped>
/**
 * Banner push-down animation — same technique as NetworkBanner.
 * max-height collapse so the banner pushes content downward when visible.
 * overflow: hidden prevents content spill during the animation.
 *
 * Why 3rem as the target max-height?
 * py-2 (16px) + text-sm (~20px) ≈ 36px total. 3rem (48px) gives a safe
 * upper bound so the transition is never clipped prematurely.
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
