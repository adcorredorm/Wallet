<script setup lang="ts">
/**
 * EmojiPicker — self-contained emoji picker with bilingual search and categories.
 *
 * Props:  modelValue — currently selected emoji string (v-model)
 * Emits:  update:modelValue — when user selects an emoji
 * No external dependencies. Fully revertible: delete this file + restore the
 * one-line swap in CategoryEditView / CategoryCreateView.
 */

import { ref, computed } from 'vue'

const props = defineProps<{
  modelValue: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

// ── Dataset ──────────────────────────────────────────────────────────────────
// Each entry: [emoji, nameEs, nameEn]
type EmojiEntry = { emoji: string; nameEs: string; nameEn: string; category: string }

const ALL_EMOJIS: EmojiEntry[] = [
  // Familia / Family
  { emoji: '👨‍👩‍👧‍👦', nameEs: 'familia', nameEn: 'family', category: 'Familia' },
  { emoji: '🏠', nameEs: 'casa hogar', nameEn: 'house home', category: 'Familia' },
  { emoji: '🏡', nameEs: 'casa jardín', nameEn: 'house garden', category: 'Familia' },
  { emoji: '👶', nameEs: 'bebé', nameEn: 'baby', category: 'Familia' },
  { emoji: '🧒', nameEs: 'niño', nameEn: 'child', category: 'Familia' },
  { emoji: '🎂', nameEs: 'torta cumpleaños', nameEn: 'birthday cake', category: 'Familia' },
  { emoji: '🎈', nameEs: 'globo fiesta', nameEn: 'balloon party', category: 'Familia' },
  { emoji: '🎀', nameEs: 'lazo regalo', nameEn: 'ribbon bow', category: 'Familia' },
  { emoji: '💝', nameEs: 'corazón amor', nameEn: 'heart love', category: 'Familia' },
  { emoji: '🛏️', nameEs: 'cama dormitorio', nameEn: 'bed bedroom', category: 'Familia' },
  { emoji: '🪑', nameEs: 'silla mueble', nameEn: 'chair furniture', category: 'Familia' },
  { emoji: '🧸', nameEs: 'osito juguete', nameEn: 'teddy bear toy', category: 'Familia' },
  { emoji: '🛁', nameEs: 'bañera baño', nameEn: 'bathtub bathroom', category: 'Familia' },
  { emoji: '🧹', nameEs: 'escoba limpieza', nameEn: 'broom cleaning', category: 'Familia' },
  { emoji: '🔑', nameEs: 'llave', nameEn: 'key', category: 'Familia' },
  // Trabajo / Work
  { emoji: '💼', nameEs: 'maletín trabajo', nameEn: 'briefcase work', category: 'Trabajo' },
  { emoji: '💻', nameEs: 'laptop computadora', nameEn: 'laptop computer', category: 'Trabajo' },
  { emoji: '🖥️', nameEs: 'monitor computadora', nameEn: 'desktop computer', category: 'Trabajo' },
  { emoji: '⌨️', nameEs: 'teclado', nameEn: 'keyboard', category: 'Trabajo' },
  { emoji: '🖨️', nameEs: 'impresora', nameEn: 'printer', category: 'Trabajo' },
  { emoji: '📊', nameEs: 'gráfico barras', nameEn: 'bar chart', category: 'Trabajo' },
  { emoji: '📋', nameEs: 'portapapeles documento', nameEn: 'clipboard document', category: 'Trabajo' },
  { emoji: '📌', nameEs: 'tachuela nota', nameEn: 'pushpin note', category: 'Trabajo' },
  { emoji: '✏️', nameEs: 'lápiz escribir', nameEn: 'pencil write', category: 'Trabajo' },
  { emoji: '🗂️', nameEs: 'archivador carpeta', nameEn: 'file folder', category: 'Trabajo' },
  { emoji: '📎', nameEs: 'clip sujetapapeles', nameEn: 'paperclip', category: 'Trabajo' },
  { emoji: '🏢', nameEs: 'oficina edificio', nameEn: 'office building', category: 'Trabajo' },
  { emoji: '💡', nameEs: 'bombilla idea', nameEn: 'light bulb idea', category: 'Trabajo' },
  { emoji: '🔧', nameEs: 'llave inglesa herramienta', nameEn: 'wrench tool', category: 'Trabajo' },
  { emoji: '📡', nameEs: 'antena señal', nameEn: 'antenna signal', category: 'Trabajo' },
  // Viajes / Travel
  { emoji: '✈️', nameEs: 'avión vuelo', nameEn: 'airplane flight', category: 'Viajes' },
  { emoji: '🚗', nameEs: 'carro auto', nameEn: 'car vehicle', category: 'Viajes' },
  { emoji: '🚌', nameEs: 'bus autobús', nameEn: 'bus', category: 'Viajes' },
  { emoji: '🚂', nameEs: 'tren ferrocarril', nameEn: 'train railway', category: 'Viajes' },
  { emoji: '🚢', nameEs: 'barco crucero', nameEn: 'ship cruise', category: 'Viajes' },
  { emoji: '🏨', nameEs: 'hotel hospedaje', nameEn: 'hotel lodging', category: 'Viajes' },
  { emoji: '🗺️', nameEs: 'mapa', nameEn: 'map', category: 'Viajes' },
  { emoji: '🧳', nameEs: 'maleta equipaje', nameEn: 'luggage suitcase', category: 'Viajes' },
  { emoji: '🎒', nameEs: 'mochila bolso', nameEn: 'backpack bag', category: 'Viajes' },
  { emoji: '🏖️', nameEs: 'playa arena sol', nameEn: 'beach sand sun', category: 'Viajes' },
  { emoji: '🏔️', nameEs: 'montaña nieve', nameEn: 'mountain snow', category: 'Viajes' },
  { emoji: '🗼', nameEs: 'torre paris', nameEn: 'eiffel tower paris', category: 'Viajes' },
  { emoji: '⛺', nameEs: 'carpa camping', nameEn: 'tent camping', category: 'Viajes' },
  { emoji: '🚕', nameEs: 'taxi transporte', nameEn: 'taxi transport', category: 'Viajes' },
  { emoji: '🛵', nameEs: 'moto scooter', nameEn: 'scooter motorcycle', category: 'Viajes' },
  // Comida / Food
  { emoji: '🍔', nameEs: 'hamburguesa comida', nameEn: 'burger fast food', category: 'Comida' },
  { emoji: '🍕', nameEs: 'pizza', nameEn: 'pizza', category: 'Comida' },
  { emoji: '🍣', nameEs: 'sushi japonés', nameEn: 'sushi japanese', category: 'Comida' },
  { emoji: '🍜', nameEs: 'ramen fideos sopa', nameEn: 'ramen noodles soup', category: 'Comida' },
  { emoji: '🌮', nameEs: 'taco mexicano', nameEn: 'taco mexican', category: 'Comida' },
  { emoji: '🥗', nameEs: 'ensalada verdura', nameEn: 'salad vegetable', category: 'Comida' },
  { emoji: '🍿', nameEs: 'palomitas cine', nameEn: 'popcorn movies', category: 'Comida' },
  { emoji: '🥤', nameEs: 'bebida refresco', nameEn: 'drink beverage', category: 'Comida' },
  { emoji: '☕', nameEs: 'café cafetería', nameEn: 'coffee cafe', category: 'Comida' },
  { emoji: '🍺', nameEs: 'cerveza alcohol', nameEn: 'beer alcohol', category: 'Comida' },
  { emoji: '🍷', nameEs: 'vino copa', nameEn: 'wine glass', category: 'Comida' },
  { emoji: '🥂', nameEs: 'brindis celebración', nameEn: 'champagne celebration', category: 'Comida' },
  { emoji: '🍰', nameEs: 'pastel torta', nameEn: 'cake dessert', category: 'Comida' },
  { emoji: '🍦', nameEs: 'helado postre', nameEn: 'ice cream dessert', category: 'Comida' },
  { emoji: '🥐', nameEs: 'croissant panadería', nameEn: 'croissant bakery', category: 'Comida' },
  { emoji: '🛒', nameEs: 'supermercado compras', nameEn: 'supermarket shopping cart', category: 'Comida' },
  // Entretenimiento / Entertainment
  { emoji: '🎬', nameEs: 'cine película', nameEn: 'movies cinema film', category: 'Entretenimiento' },
  { emoji: '🎮', nameEs: 'videojuegos consola', nameEn: 'video games console', category: 'Entretenimiento' },
  { emoji: '🎵', nameEs: 'música nota', nameEn: 'music note', category: 'Entretenimiento' },
  { emoji: '🎧', nameEs: 'audífonos música', nameEn: 'headphones music', category: 'Entretenimiento' },
  { emoji: '📺', nameEs: 'televisión tele', nameEn: 'television tv', category: 'Entretenimiento' },
  { emoji: '🎭', nameEs: 'teatro obra', nameEn: 'theater drama', category: 'Entretenimiento' },
  { emoji: '🎨', nameEs: 'arte pintura', nameEn: 'art painting', category: 'Entretenimiento' },
  { emoji: '🎲', nameEs: 'dados juego', nameEn: 'dice game', category: 'Entretenimiento' },
  { emoji: '♟️', nameEs: 'ajedrez', nameEn: 'chess', category: 'Entretenimiento' },
  { emoji: '🎯', nameEs: 'objetivo diana', nameEn: 'target bullseye', category: 'Entretenimiento' },
  { emoji: '🎸', nameEs: 'guitarra música', nameEn: 'guitar music', category: 'Entretenimiento' },
  { emoji: '📱', nameEs: 'celular móvil', nameEn: 'phone mobile', category: 'Entretenimiento' },
  { emoji: '📸', nameEs: 'foto cámara', nameEn: 'photo camera', category: 'Entretenimiento' },
  { emoji: '🎪', nameEs: 'circo parque', nameEn: 'circus park', category: 'Entretenimiento' },
  { emoji: '🎠', nameEs: 'carrusel diversión', nameEn: 'carousel fun', category: 'Entretenimiento' },
  // Salud / Health
  { emoji: '💊', nameEs: 'pastilla medicamento', nameEn: 'pill medicine', category: 'Salud' },
  { emoji: '🏥', nameEs: 'hospital clínica', nameEn: 'hospital clinic', category: 'Salud' },
  { emoji: '🩺', nameEs: 'médico doctor', nameEn: 'doctor stethoscope', category: 'Salud' },
  { emoji: '💉', nameEs: 'inyección vacuna', nameEn: 'injection vaccine', category: 'Salud' },
  { emoji: '🩹', nameEs: 'curita venda', nameEn: 'bandage band-aid', category: 'Salud' },
  { emoji: '🏃', nameEs: 'correr ejercicio', nameEn: 'running exercise', category: 'Salud' },
  { emoji: '🧘', nameEs: 'yoga meditación', nameEn: 'yoga meditation', category: 'Salud' },
  { emoji: '💪', nameEs: 'músculo fuerza', nameEn: 'muscle strength', category: 'Salud' },
  { emoji: '🏋️', nameEs: 'pesas gimnasio', nameEn: 'weights gym', category: 'Salud' },
  { emoji: '🚴', nameEs: 'bicicleta ciclismo', nameEn: 'bicycle cycling', category: 'Salud' },
  { emoji: '🌿', nameEs: 'planta natural', nameEn: 'plant natural herb', category: 'Salud' },
  { emoji: '🧴', nameEs: 'loción cuidado', nameEn: 'lotion skincare', category: 'Salud' },
  { emoji: '🦷', nameEs: 'diente dental', nameEn: 'tooth dental', category: 'Salud' },
  { emoji: '😷', nameEs: 'cubrebocas enfermedad', nameEn: 'mask sick', category: 'Salud' },
  { emoji: '🛌', nameEs: 'descanso dormir', nameEn: 'rest sleep', category: 'Salud' },
  // Productividad / Productivity
  { emoji: '📚', nameEs: 'libros estudio', nameEn: 'books study', category: 'Productividad' },
  { emoji: '📖', nameEs: 'libro leer', nameEn: 'book reading', category: 'Productividad' },
  { emoji: '🖊️', nameEs: 'pluma escribir', nameEn: 'pen writing', category: 'Productividad' },
  { emoji: '📝', nameEs: 'nota apunte', nameEn: 'note memo', category: 'Productividad' },
  { emoji: '📅', nameEs: 'calendario agenda', nameEn: 'calendar schedule', category: 'Productividad' },
  { emoji: '⏰', nameEs: 'reloj alarma', nameEn: 'alarm clock', category: 'Productividad' },
  { emoji: '🔔', nameEs: 'notificación campana', nameEn: 'notification bell', category: 'Productividad' },
  { emoji: '🏆', nameEs: 'trofeo logro', nameEn: 'trophy achievement', category: 'Productividad' },
  { emoji: '🧠', nameEs: 'cerebro inteligencia', nameEn: 'brain intelligence', category: 'Productividad' },
  { emoji: '📐', nameEs: 'escuadra diseño', nameEn: 'ruler design', category: 'Productividad' },
  { emoji: '🔬', nameEs: 'microscopio ciencia', nameEn: 'microscope science', category: 'Productividad' },
  { emoji: '🔭', nameEs: 'telescopio astronomía', nameEn: 'telescope astronomy', category: 'Productividad' },
  { emoji: '🎓', nameEs: 'graduación educación', nameEn: 'graduation education', category: 'Productividad' },
  { emoji: '🗓️', nameEs: 'fecha planificación', nameEn: 'date planning', category: 'Productividad' },
  { emoji: '✅', nameEs: 'completado tarea', nameEn: 'done task completed', category: 'Productividad' },
  // Finanzas / Finance
  { emoji: '💰', nameEs: 'dinero billete', nameEn: 'money bag', category: 'Finanzas' },
  { emoji: '💳', nameEs: 'tarjeta crédito', nameEn: 'credit card', category: 'Finanzas' },
  { emoji: '💵', nameEs: 'dólar efectivo', nameEn: 'dollar cash', category: 'Finanzas' },
  { emoji: '💴', nameEs: 'yen japón', nameEn: 'yen japan', category: 'Finanzas' },
  { emoji: '💶', nameEs: 'euro europa', nameEn: 'euro europe', category: 'Finanzas' },
  { emoji: '💷', nameEs: 'libra reino unido', nameEn: 'pound sterling uk', category: 'Finanzas' },
  { emoji: '🏦', nameEs: 'banco institución', nameEn: 'bank institution', category: 'Finanzas' },
  { emoji: '📈', nameEs: 'inversión subida', nameEn: 'chart up investment', category: 'Finanzas' },
  { emoji: '📉', nameEs: 'bajada pérdida', nameEn: 'chart down loss', category: 'Finanzas' },
  { emoji: '💹', nameEs: 'mercado bolsa', nameEn: 'stock market', category: 'Finanzas' },
  { emoji: '🤑', nameEs: 'rico dinero', nameEn: 'money face rich', category: 'Finanzas' },
  { emoji: '🧾', nameEs: 'recibo factura', nameEn: 'receipt invoice', category: 'Finanzas' },
  { emoji: '💸', nameEs: 'gasto pago', nameEn: 'payment expense', category: 'Finanzas' },
  { emoji: '🪙', nameEs: 'moneda', nameEn: 'coin', category: 'Finanzas' },
  { emoji: '💎', nameEs: 'diamante valor', nameEn: 'diamond value', category: 'Finanzas' },
  // Banderas / Flags
  { emoji: '🇺🇸', nameEs: 'estados unidos eeuu', nameEn: 'united states usa', category: 'Banderas' },
  { emoji: '🇲🇽', nameEs: 'méxico', nameEn: 'mexico', category: 'Banderas' },
  { emoji: '🇨🇴', nameEs: 'colombia', nameEn: 'colombia', category: 'Banderas' },
  { emoji: '🇧🇷', nameEs: 'brasil', nameEn: 'brazil', category: 'Banderas' },
  { emoji: '🇦🇷', nameEs: 'argentina', nameEn: 'argentina', category: 'Banderas' },
  { emoji: '🇪🇸', nameEs: 'españa', nameEn: 'spain', category: 'Banderas' },
  { emoji: '🇺🇾', nameEs: 'uruguay', nameEn: 'uruguay', category: 'Banderas' },
  { emoji: '🇨🇱', nameEs: 'chile', nameEn: 'chile', category: 'Banderas' },
  { emoji: '🇵🇪', nameEs: 'perú', nameEn: 'peru', category: 'Banderas' },
  { emoji: '🇻🇪', nameEs: 'venezuela', nameEn: 'venezuela', category: 'Banderas' },
  { emoji: '🇯🇵', nameEs: 'japón', nameEn: 'japan', category: 'Banderas' },
  { emoji: '🇫🇷', nameEs: 'francia', nameEn: 'france', category: 'Banderas' },
  { emoji: '🇩🇪', nameEs: 'alemania', nameEn: 'germany', category: 'Banderas' },
  { emoji: '🇬🇧', nameEs: 'reino unido', nameEn: 'united kingdom uk', category: 'Banderas' },
  { emoji: '🇨🇳', nameEs: 'china', nameEn: 'china', category: 'Banderas' },
  // Deportes / Sports
  { emoji: '⚽', nameEs: 'fútbol soccer', nameEn: 'soccer football', category: 'Deportes' },
  { emoji: '🏀', nameEs: 'baloncesto basket', nameEn: 'basketball', category: 'Deportes' },
  { emoji: '🎾', nameEs: 'tenis raqueta', nameEn: 'tennis racket', category: 'Deportes' },
  { emoji: '🏈', nameEs: 'fútbol americano', nameEn: 'american football', category: 'Deportes' },
  { emoji: '⚾', nameEs: 'béisbol', nameEn: 'baseball', category: 'Deportes' },
  { emoji: '🏓', nameEs: 'ping pong tenis de mesa', nameEn: 'table tennis ping pong', category: 'Deportes' },
  { emoji: '🏸', nameEs: 'bádminton', nameEn: 'badminton', category: 'Deportes' },
  { emoji: '🥊', nameEs: 'boxeo guante', nameEn: 'boxing glove', category: 'Deportes' },
  { emoji: '🤿', nameEs: 'buceo natación', nameEn: 'diving snorkeling', category: 'Deportes' },
  { emoji: '🏄', nameEs: 'surf ola', nameEn: 'surfing wave', category: 'Deportes' },
  { emoji: '⛷️', nameEs: 'esquí nieve', nameEn: 'skiing snow', category: 'Deportes' },
  { emoji: '🧗', nameEs: 'escalada montaña', nameEn: 'climbing mountain', category: 'Deportes' },
  { emoji: '🏊', nameEs: 'natación piscina', nameEn: 'swimming pool', category: 'Deportes' },
  { emoji: '🤸', nameEs: 'gimnasia acrobacia', nameEn: 'gymnastics acrobatics', category: 'Deportes' },
  { emoji: '⛳', nameEs: 'golf campo', nameEn: 'golf course', category: 'Deportes' },
  // Otros / Others
  { emoji: '🌟', nameEs: 'estrella especial', nameEn: 'star special', category: 'Otros' },
  { emoji: '⭐', nameEs: 'estrella favorito', nameEn: 'star favorite', category: 'Otros' },
  { emoji: '🌙', nameEs: 'luna noche', nameEn: 'moon night', category: 'Otros' },
  { emoji: '☀️', nameEs: 'sol día', nameEn: 'sun day', category: 'Otros' },
  { emoji: '🌈', nameEs: 'arcoíris colores', nameEn: 'rainbow colors', category: 'Otros' },
  { emoji: '🌊', nameEs: 'ola agua', nameEn: 'wave water', category: 'Otros' },
  { emoji: '🌺', nameEs: 'flor hibisco', nameEn: 'flower hibiscus', category: 'Otros' },
  { emoji: '🌸', nameEs: 'flor cerezo', nameEn: 'cherry blossom flower', category: 'Otros' },
  { emoji: '🍀', nameEs: 'trébol suerte', nameEn: 'clover luck', category: 'Otros' },
  { emoji: '🦋', nameEs: 'mariposa', nameEn: 'butterfly', category: 'Otros' },
  { emoji: '🐾', nameEs: 'huella mascota', nameEn: 'paw print pet', category: 'Otros' },
  { emoji: '🎋', nameEs: 'bambú decoración', nameEn: 'bamboo decoration', category: 'Otros' },
  { emoji: '🪴', nameEs: 'planta decoración', nameEn: 'potted plant decoration', category: 'Otros' },
  { emoji: '🔮', nameEs: 'bola cristal misterio', nameEn: 'crystal ball mystery', category: 'Otros' },
  { emoji: '🌍', nameEs: 'mundo tierra planeta', nameEn: 'world earth planet', category: 'Otros' },
]

const CATEGORY_NAMES = [
  'Familia', 'Trabajo', 'Viajes', 'Comida', 'Entretenimiento',
  'Salud', 'Productividad', 'Finanzas', 'Banderas', 'Deportes', 'Otros'
] as const

// ── State ─────────────────────────────────────────────────────────────────────
const search = ref('')
const activeCategory = ref<string | null>(null)

// ── Computed ──────────────────────────────────────────────────────────────────
const filteredEmojis = computed(() => {
  const q = search.value.trim().toLowerCase()
  let list = ALL_EMOJIS

  if (activeCategory.value) {
    list = list.filter(e => e.category === activeCategory.value)
  }

  if (q) {
    list = list.filter(e =>
      e.nameEs.toLowerCase().includes(q) ||
      e.nameEn.toLowerCase().includes(q) ||
      e.emoji === q
    )
  }

  return list
})

// ── Handlers ──────────────────────────────────────────────────────────────────
function selectEmoji(emoji: string) {
  if (!props.disabled) {
    emit('update:modelValue', emoji)
  }
}

function toggleCategory(cat: string) {
  activeCategory.value = activeCategory.value === cat ? null : cat
}
</script>

<template>
  <div class="space-y-3">
    <!-- Search -->
    <input
      v-model="search"
      type="text"
      placeholder="Buscar emoji (ej: café, coffee)…"
      :disabled="disabled"
      class="w-full rounded-lg bg-dark-bg-tertiary border border-dark-bg-tertiary/80
             px-3 py-2 text-sm text-dark-text-primary placeholder-dark-text-secondary
             focus:outline-none focus:ring-2 focus:ring-accent-blue
             disabled:opacity-40 disabled:cursor-not-allowed"
    />

    <!-- Category chips -->
    <div class="flex flex-wrap gap-1.5">
      <button
        v-for="cat in CATEGORY_NAMES"
        :key="cat"
        type="button"
        :disabled="disabled"
        :class="[
          'px-2.5 py-1 rounded-full text-xs transition-colors',
          disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer',
          activeCategory === cat
            ? 'bg-accent-blue text-white'
            : 'bg-dark-bg-tertiary text-dark-text-secondary hover:bg-dark-bg-tertiary/80'
        ]"
        @click="toggleCategory(cat)"
      >
        {{ cat }}
      </button>
    </div>

    <!-- Emoji grid -->
    <div v-if="filteredEmojis.length > 0" class="grid grid-cols-8 gap-1.5 max-h-48 overflow-y-auto">
      <button
        v-for="entry in filteredEmojis"
        :key="entry.emoji"
        type="button"
        :disabled="disabled"
        :title="`${entry.nameEs} / ${entry.nameEn}`"
        :class="[
          'p-2 rounded-lg text-2xl transition-colors',
          disabled ? 'opacity-40 cursor-not-allowed' : 'hover:bg-dark-bg-tertiary',
          modelValue === entry.emoji ? 'bg-dark-bg-tertiary ring-2 ring-accent-blue' : ''
        ]"
        @click="selectEmoji(entry.emoji)"
      >
        {{ entry.emoji }}
      </button>
    </div>

    <p v-else class="text-sm text-dark-text-secondary text-center py-4">
      No se encontraron emojis para "{{ search }}"
    </p>
  </div>
</template>
