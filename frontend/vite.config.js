import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      // 'prompt' strategy: show a UI prompt when a new SW version is available.
      // For a finance app this is safer than 'autoUpdate', which would force a
      // page reload mid-session and could discard unsaved form state.
      registerType: 'autoUpdate',

      // Disable the Service Worker in development so code changes are always
      // served fresh without cached-bundle interference. The SW only makes
      // sense in production where assets are hashed and stable.
      devOptions: {
        enabled: false,
      },

      // Static assets that Workbox should precache during build.
      // favicon.svg is the existing icon; icons/* covers our PWA icons.
      // TODO: change 'icons/*.svg' to 'icons/*.png' once real icons are generated.
      includeAssets: ['favicon.svg', 'icons/*.svg'],

      // Web App Manifest — tells the browser how to install and display the app.
      manifest: {
        name: 'Wallet - Finanzas Personales',
        short_name: 'Wallet',
        description: 'Aplicacion de seguimiento y analisis de gastos personales',
        start_url: '/',
        // 'standalone' hides the browser chrome so the app feels native on mobile.
        display: 'standalone',
        // Use the project's actual primary background color (#0f172a = slate-900)
        // confirmed from tailwind.config.js dark.bg.primary value.
        background_color: '#0f172a',
        theme_color: '#0f172a',
        // TODO (Phase 1 placeholder): These are SVG placeholder icons.
        // Before production, generate real PNGs with a tool such as
        // `npx pwa-asset-generator logo.svg public/icons` and restore
        // the `.png` extensions and `type: 'image/png'` entries below.
        icons: [
          {
            src: '/icons/icon-192.svg',
            sizes: '192x192',
            type: 'image/svg+xml'
          },
          {
            src: '/icons/icon-512.svg',
            sizes: '512x512',
            type: 'image/svg+xml'
          },
          {
            // maskable purpose: allows the OS to apply its own shape mask (circle,
            // squircle, etc.) to the icon. Required for a good install experience
            // on Android home screens.
            src: '/icons/icon-maskable-512.svg',
            sizes: '512x512',
            type: 'image/svg+xml',
            purpose: 'maskable'
          }
        ]
      },

      workbox: {
        // Precache every compiled JS, CSS, HTML, SVG, PNG and font file.
        // This is what enables the app shell to load fully offline.
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],

        runtimeCaching: [
          {
            // Match any request to our Flask API endpoints.
            urlPattern: /^https?:\/\/.*\/api\/v1\/.*/i,

            // NetworkFirst: always try the network. If the network responds
            // within networkTimeoutSeconds, use that fresh response and cache it.
            // If offline or slow, serve the cached version as a fallback.
            // This is the right strategy for financial data: fresh by default,
            // but still functional offline.
            handler: 'NetworkFirst',

            options: {
              cacheName: 'api-cache',
              expiration: {
                // Keep at most 100 API responses cached (prevents unbounded growth).
                maxEntries: 100,
                // Expire cached responses after 24 hours so stale data is bounded.
                maxAgeSeconds: 60 * 60 * 24
              },
              // If the network does not respond in 5 seconds, fall back to cache.
              networkTimeoutSeconds: 5
            }
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 3000,
    proxy: {
      // Proxy API requests to Flask backend.
      // BACKEND_URL env var allows Docker to override the target (uses Docker
      // internal DNS: http://backend:5000) while local dev defaults to host port.
      '/api': {
        target: process.env.BACKEND_URL || 'http://localhost:5001',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
