/// <reference types="vite/client" />

/**
 * PWA virtual module type declarations.
 *
 * Why a reference directive instead of compilerOptions.types?
 * - compilerOptions.types applies the package globally and requires the
 *   package to be resolvable at tsconfig parse time. If the package is not
 *   yet installed the compiler throws TS2688.
 * - A triple-slash reference directive is resolved lazily at type-check time,
 *   scoped to this file, and is the pattern recommended by vite-plugin-pwa's
 *   own documentation.
 *
 * This declaration registers the `virtual:pwa-register/vue` module so
 * TypeScript understands the import in src/main.ts without a TS2307 error.
 */
/// <reference types="vite-plugin-pwa/client" />
