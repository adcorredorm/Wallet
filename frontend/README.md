# Wallet Frontend

Frontend mobile-first de la aplicación Wallet, construido con Vue.js 3, TypeScript, y Tailwind CSS.

## Características

### Arquitectura Mobile-First
- Diseño optimizado para dispositivos móviles (320px+)
- Navegación inferior (bottom navigation) en móvil
- Botones touch-friendly (mínimo 44px de altura)
- Dark mode nativo para mejor experiencia y ahorro de batería

### Stack Tecnológico
- **Vue 3** con Composition API
- **TypeScript** para type-safety
- **Pinia** para gestión de estado
- **Vue Router** para navegación SPA
- **Axios** para comunicación con API
- **Tailwind CSS** para estilos utility-first
- **Vite** como build tool (desarrollo rápido)

### Estructura del Proyecto

```
src/
├── api/              # Cliente HTTP para backend API
├── assets/           # CSS global y assets estáticos
├── components/       # Componentes Vue reutilizables
│   ├── ui/           # Componentes base (Button, Input, etc)
│   ├── shared/       # Componentes compartidos (AmountInput, etc)
│   ├── layout/       # Layout y navegación
│   ├── accounts/     # Componentes de cuentas
│   ├── categories/   # Componentes de categorías
│   ├── transactions/ # Componentes de transacciones
│   ├── transfers/    # Componentes de transferencias
│   └── dashboard/    # Componentes del dashboard
├── composables/      # Composables de Vue (lógica reutilizable)
├── router/           # Configuración de Vue Router
├── stores/           # Pinia stores (estado global)
├── types/            # TypeScript type definitions
├── utils/            # Utilidades (formatters, validators, etc)
├── views/            # Componentes de página/vista
├── App.vue           # Componente raíz
└── main.ts           # Entry point

## Instalación

1. Instalar dependencias:
```bash
npm install
```

2. Copiar archivo de configuración:
```bash
cp .env.example .env
```

3. Configurar la URL del backend en `.env`:
```
VITE_API_BASE_URL=http://localhost:5000/api/v1
```

## Desarrollo

Iniciar servidor de desarrollo:
```bash
npm run dev
```

La aplicación estará disponible en `http://localhost:3000`

## Build

Generar build de producción:
```bash
npm run build
```

Preview del build de producción:
```bash
npm run preview
```

## Scripts Disponibles

- `npm run dev` - Inicia servidor de desarrollo
- `npm run build` - Genera build de producción
- `npm run preview` - Preview del build de producción
- `npm run lint` - Ejecuta ESLint
- `npm run type-check` - Verifica tipos TypeScript

## Principios de Diseño Mobile-First

### Breakpoints
- **Mobile**: 320px - 767px (base, sin media query)
- **Tablet**: 768px - 1023px (`@media (min-width: 768px)`)
- **Desktop**: 1024px+ (`@media (min-width: 1024px)`)

### Consideraciones de UI
1. **Touch Targets**: Mínimo 44x44px para elementos interactivos
2. **Spacing**: Mínimo 8px entre elementos clickeables
3. **Navegación**: Bottom navigation en móvil, más accesible con el pulgar
4. **Formularios**: Inputs grandes, teclado numérico para montos
5. **Feedback**: Toast notifications no intrusivos, carga con spinners

### Dark Mode
Paleta de colores optimizada:
- Background: `#0f172a` (dark slate)
- Cards: `#1e293b` (slate)
- Text: `#f1f5f9` (near white)
- Accent: `#3b82f6` (blue)

## Estructura de Stores (Pinia)

### accountsStore
- Gestión de cuentas financieras
- Cálculo de balances desde API
- CRUD operations

### categoriesStore
- Gestión de categorías (ingreso/gasto)
- Soporte para jerarquías (subcategorías)

### transactionsStore
- Gestión de transacciones (ingresos y gastos)
- Filtros por cuenta, categoría, fecha
- Cálculos de totales

### transfersStore
- Gestión de transferencias entre cuentas
- Filtros y búsqueda

### uiStore
- Estado global de UI (toasts, modals, loading)
- Notificaciones

## Comunicación con Backend

El cliente API (`src/api/`) usa Axios con:
- Interceptores para manejo centralizado de errores
- Transformación automática de respuestas
- Timeout configurado (10s para redes móviles)
- Base URL configurable via `.env`

Endpoints principales:
- `/api/v1/accounts` - Cuentas
- `/api/v1/categories` - Categorías
- `/api/v1/transactions` - Transacciones
- `/api/v1/transfers` - Transferencias
- `/api/v1/dashboard` - Dashboard summary

## Validaciones

Validación en dos niveles:
1. **Cliente (este frontend)**: Feedback inmediato, mejor UX
2. **Servidor (backend Flask)**: Validación autoritativa, seguridad

Las validaciones cliente están en `src/utils/validators.ts`

## Formatters

Formateo consistente de:
- **Moneda**: `formatCurrency()` con soporte multi-divisa
- **Fechas**: `formatDate()`, `formatDateRelative()` (Hoy, Ayer, etc)
- **Números**: `formatNumber()` con decimales configurables

Ver `src/utils/formatters.ts`

## Convenciones de Código

1. **Componentes**: PascalCase (ej: `AccountCard.vue`)
2. **Composables**: camelCase con prefijo `use` (ej: `useAccounts.ts`)
3. **Tipos**: PascalCase (ej: `Account`, `Transaction`)
4. **Stores**: camelCase con sufijo `Store` (ej: `accountsStore`)

## Testing (Próximamente)

- Unit tests: Vitest
- Component tests: Vue Test Utils
- E2E tests: Cypress

## Contribuir

1. Seguir principios mobile-first
2. Usar TypeScript para nuevos componentes
3. Mantener componentes pequeños y reutilizables
4. Documentar decisiones de diseño en comentarios
5. Probar en móvil real antes de PR

## Licencia

MIT
