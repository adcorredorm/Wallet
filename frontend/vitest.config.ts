import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      // jsdom gives us window, document, navigator.onLine — required for
      // stores that reference browser globals at module evaluation time
      // (sync.ts reads navigator.onLine in the ref() initialiser).
      environment: 'jsdom',
      // globals: true means describe/it/expect/vi are available without
      // explicit imports in every spec file — matches Jest muscle memory.
      globals: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov'],
        include: ['src/**/*.ts', 'src/**/*.vue'],
        exclude: ['src/**/*.spec.ts', 'src/main.ts', 'src/offline/db.ts']
      }
    }
  })
)
