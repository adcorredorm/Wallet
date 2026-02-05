<script setup lang="ts">
/**
 * 404 Not Found View
 */

import { useRouter } from 'vue-router'
import BaseButton from '@/components/ui/BaseButton.vue'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>

<template>
  <div class="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
    <div class="text-8xl mb-4">404</div>
    <h1 class="text-3xl font-bold mb-2">Página no encontrada</h1>
    <p class="text-dark-text-secondary mb-8">
      La página que buscas no existe o ha sido movida.
    </p>
    <BaseButton variant="primary" @click="goHome">
      Volver al inicio
    </BaseButton>
  </div>
</template>
