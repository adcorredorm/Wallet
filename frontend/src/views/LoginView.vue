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

import { ref, onMounted, useTemplateRef } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePostLoginFlow } from '@/composables/usePostLoginFlow'

const router = useRouter()
const authStore = useAuthStore()
const { handlePostLogin } = usePostLoginFlow()

const isLoading = ref(false)
const error = ref<string | null>(null)
const googleButtonContainer = useTemplateRef<HTMLDivElement>('googleButtonContainer')

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

  // SDK carga con async defer — puede no estar listo en onMounted.
  // Esperamos hasta 5s con polling antes de mostrar error.
  // Usamos renderButton en lugar de prompt() — más confiable y
  // permite elegir cualquier cuenta de Google (no solo la última usada).
  const initSdk = () => {
    if (window.google?.accounts?.id) {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleCallback,
        auto_select: false,
        cancel_on_tap_outside: true,
      })
      if (googleButtonContainer.value) {
        window.google.accounts.id.renderButton(googleButtonContainer.value, {
          theme: 'filled_blue',
          size: 'large',
          text: 'continue_with',
          locale: 'es',
          width: 280,
        })
      }
      return
    }
    let attempts = 0
    const interval = setInterval(() => {
      attempts++
      if (window.google?.accounts?.id) {
        clearInterval(interval)
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: handleGoogleCallback,
          auto_select: false,
          cancel_on_tap_outside: true,
        })
        if (googleButtonContainer.value) {
          window.google.accounts.id.renderButton(googleButtonContainer.value, {
            theme: 'filled_blue',
            size: 'large',
            text: 'continue_with',
            locale: 'es',
            width: 280,
          })
        }
      } else if (attempts >= 50) {
        clearInterval(interval)
        error.value = 'No se pudo cargar el SDK de Google. Verifica tu conexión.'
      }
    }, 100)
  }

  initSdk()
})

// ---------------------------------------------------------------------------
// Manejador del callback de Google
// ---------------------------------------------------------------------------
async function handleGoogleCallback(response: { credential: string }): Promise<void> {
  isLoading.value = true
  error.value = null

  try {
    const { is_new_user } = await authStore.loginWithGoogle(response.credential)
    await handlePostLogin(is_new_user)
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

// handleLoginClick ya no es necesario — renderButton gestiona el click internamente.
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
        <!-- Botón oficial de Google (renderButton) — más confiable que prompt(),
             permite elegir cualquier cuenta y funciona sin cooldown. -->
        <div class="flex justify-center min-h-[44px] items-center">
          <div v-if="isLoading" class="flex items-center gap-2 text-sm" style="color: #cbd5e1;">
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <span>Iniciando sesión...</span>
          </div>
          <div v-else ref="googleButtonContainer" />
        </div>

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
