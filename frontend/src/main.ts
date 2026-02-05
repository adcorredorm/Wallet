/**
 * Application Entry Point
 *
 * Why this structure?
 * - createApp(): Vue 3 initialization
 * - Pinia before router: Store must be available for route guards
 * - Import CSS: Global Tailwind styles
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/css/main.css'

const app = createApp(App)

// Initialize Pinia store (must come before router)
const pinia = createPinia()
app.use(pinia)

// Initialize router
app.use(router)

// Mount application
app.mount('#app')
