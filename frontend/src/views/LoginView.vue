<script setup lang="ts">
/**
 * LoginView — vista de autenticación.
 *
 * Por qué un solo botón?
 * El plan especifica: "un único botón 'Continuar con Google'". Sin formularios,
 * sin campos, sin complejidad. Google valida la identidad — nosotros solo
 * iniciamos el flujo y procesamos el resultado.
 *
 * Flujo OAuth:
 * 1. onMounted: inicializa el SDK de Google con VITE_GOOGLE_CLIENT_ID
 * 2. Usuario toca "Continuar con Google"
 * 3. Google presenta el selector de cuenta (popup nativo del browser)
 * 4. callback recibe { credential: id_token }
 * 5. loginWithGoogle(id_token) → POST /auth/google → estado actualizado
 * 6. router.push('/') — navegamos al home
 *
 * Por qué onMounted para inicializar google.accounts.id?
 * El SDK debe inicializarse DESPUÉS de que el DOM existe. onMounted garantiza
 * que el componente está en el DOM antes de llamar initialize().
 *
 * Por qué VITE_GOOGLE_CLIENT_ID via import.meta.env?
 * Las variables VITE_* en Vite se inline en el bundle en build time.
 * Es la forma estándar de inyectar configuración pública en Vite.
 */

import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const isLoading = ref(false)
const error = ref<string | null>(null)

// ---------------------------------------------------------------------------
// Inicializar Google Identity Services SDK
// ---------------------------------------------------------------------------
onMounted(() => {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

  if (!clientId) {
    console.warn('[LoginView] VITE_GOOGLE_CLIENT_ID no está configurado.')
    error.value = 'Configuración de Google OAuth faltante.'
    return
  }

  if (!window.google?.accounts?.id) {
    error.value = 'No se pudo cargar el SDK de Google. Verifica tu conexión.'
    return
  }

  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: handleGoogleCallback,
    auto_select: false,
    cancel_on_tap_outside: true,
  })
})

// ---------------------------------------------------------------------------
// Manejador del callback de Google
// ---------------------------------------------------------------------------
async function handleGoogleCallback(response: { credential: string }): Promise<void> {
  isLoading.value = true
  error.value = null

  try {
    await authStore.loginWithGoogle(response.credential)
    // Navegamos al home — la lógica post-login (onboarding, etc.) se maneja allí
    await router.push('/')
  } catch (err: unknown) {
    error.value = err instanceof Error
      ? err.message
      : 'Error al iniciar sesión con Google. Inténtalo de nuevo.'
    console.error('[LoginView] Error en loginWithGoogle:', err)
  } finally {
    isLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Iniciar flujo de Google (el botón llama a prompt())
// ---------------------------------------------------------------------------
function handleLoginClick(): void {
  if (!window.google?.accounts?.id) {
    error.value = 'SDK de Google no disponible. Recarga la página.'
    return
  }
  error.value = null
  window.google.accounts.id.prompt()
}
</script>

<template>
  <!--
    Por qué min-h-screen con flex center?
    La vista de login no usa AppLayout (sin nav inferior, sin header).
    Centramos verticalmente usando flex para que el contenido quede en el
    "golden ratio" visual de la pantalla, sin importar el tamaño del dispositivo.
  -->
  <div
    class="min-h-screen flex flex-col items-center justify-center px-6"
    style="background-color: #0f172a;"
  >
    <!-- Contenedor de contenido — max-width para tablets/desktop -->
    <div class="w-full max-w-sm space-y-8">

      <!-- Logo / nombre de app -->
      <div class="text-center space-y-2">
        <h1 class="text-3xl font-bold" style="color: #f1f5f9;">
          Wallet
        </h1>
        <p class="text-sm" style="color: #cbd5e1;">
          Tus finanzas personales, siempre contigo.
        </p>
      </div>

      <!-- Card del botón de login -->
      <div
        class="rounded-2xl p-6 space-y-4"
        style="background-color: #1e293b; border: 1px solid rgba(51, 65, 85, 0.5);"
      >

        <!-- Texto introductorio -->
        <p class="text-center text-sm" style="color: #cbd5e1;">
          Inicia sesión para sincronizar tus datos en todos tus dispositivos.
        </p>

        <!--
          Botón "Continuar con Google"

          Por qué min-h-[44px]?
          WCAG y Apple HIG recomiendan mínimo 44x44px para touch targets.
          En pantallas móviles, botones más pequeños son difíciles de tocar
          con precisión.

          Por qué w-full?
          En móvil, los botones de acción principal deben ocupar todo el ancho
          disponible para maximizar el área de toque y seguir convenciones
          de apps nativas.
        -->
        <button
          @click="handleLoginClick"
          :disabled="isLoading"
          class="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl
                 font-medium text-sm transition-all duration-200
                 disabled:opacity-50 disabled:cursor-not-allowed
                 min-h-[44px]"
          style="background-color: #ffffff; color: #0f172a;"
          aria-label="Continuar con Google para iniciar sesión"
        >
          <!-- Spinner de carga -->
          <svg
            v-if="isLoading"
            class="w-5 h-5 animate-spin flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              class="opacity-25"
              cx="12" cy="12" r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>

          <!-- Icono de Google (SVG inline oficial) -->
          <svg
            v-else
            class="w-5 h-5 flex-shrink-0"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>

          <span>{{ isLoading ? 'Iniciando sesión...' : 'Continuar con Google' }}</span>
        </button>

        <!-- Mensaje de error -->
        <p
          v-if="error"
          class="text-center text-xs"
          style="color: #ef4444;"
          role="alert"
          aria-live="assertive"
        >
          {{ error }}
        </p>

      </div>

      <!-- Nota de modo invitado -->
      <p class="text-center text-xs" style="color: #64748b;">
        Puedes usar la app sin cuenta.
        <button
          @click="$router.push('/')"
          class="underline transition-colors duration-150"
          style="color: #3b82f6;"
        >
          Continuar como invitado
        </button>
      </p>

    </div>
  </div>
</template>
