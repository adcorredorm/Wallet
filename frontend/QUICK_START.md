# Quick Start - Wallet Frontend

## Instalación Rápida

```bash
# 1. Navegar al directorio
cd /Users/angelcorredor/Code/Wallet/frontend

# 2. Instalar dependencias
npm install

# 3. Crear archivo de configuración
cp .env.example .env

# 4. Editar .env y configurar la URL del backend
# VITE_API_BASE_URL=http://localhost:5000/api/v1

# 5. Iniciar servidor de desarrollo
npm run dev
```

La aplicación estará disponible en **http://localhost:3000**

---

## Comandos Principales

```bash
# Desarrollo
npm run dev          # Servidor de desarrollo con hot reload

# Build
npm run build        # Generar build de producción
npm run preview      # Preview del build

# Calidad de código
npm run lint         # Ejecutar ESLint
npm run type-check   # Verificar tipos TypeScript
```

---

## Estructura Rápida

```
frontend/
├── src/
│   ├── api/              # Comunicación con backend
│   ├── stores/           # Estado global (Pinia)
│   ├── components/       # Componentes Vue
│   │   ├── ui/          # Botones, inputs, modales
│   │   ├── accounts/    # Componentes de cuentas
│   │   ├── transactions/# Componentes de transacciones
│   │   └── ...
│   ├── views/           # Páginas/vistas
│   ├── router/          # Rutas de la app
│   ├── types/           # TypeScript types
│   └── utils/           # Utilidades (formatters, validators)
```

---

## Rutas Principales

- `/` - Dashboard (vista principal)
- `/accounts` - Lista de cuentas
- `/accounts/new` - Crear cuenta
- `/transactions` - Lista de transacciones
- `/transactions/new` - Crear transacción
- `/transfers` - Lista de transferencias
- `/transfers/new` - Crear transferencia
- `/categories` - Gestión de categorías

---

## Flujo de Datos

1. **Usuario interactúa** → Vista (View)
2. **Vista llama** → Store (Pinia)
3. **Store hace request** → API Client (Axios)
4. **API Client comunica** → Backend Flask
5. **Backend responde** → API Client
6. **Store actualiza estado** → Vista se actualiza (reactive)

---

## Tecnologías Clave

- **Vue 3** - Framework progresivo
- **TypeScript** - Type safety
- **Pinia** - State management
- **Vue Router** - Navegación SPA
- **Tailwind CSS** - Utility-first CSS
- **Axios** - HTTP client
- **Vite** - Build tool rápido

---

## Mobile-First

Este proyecto está diseñado **mobile-first**:
- Todos los estilos base son para móvil (320px+)
- Navegación inferior en móvil (bottom nav)
- Botones grandes (min 44px) para touch
- Dark mode por defecto

Para ver correctamente en desktop, la app se adapta automáticamente en pantallas > 768px.

---

## Próximos Pasos

1. **Explorar el código**: Empezar por `src/main.ts` y `src/App.vue`
2. **Ver el Dashboard**: `src/views/DashboardView.vue`
3. **Entender los stores**: `src/stores/accounts.ts`
4. **Revisar componentes**: `src/components/ui/BaseButton.vue`

Cada archivo tiene comentarios explicativos sobre las decisiones técnicas.

---

## Problemas Comunes

### Puerto 3000 ocupado
```bash
# Cambiar puerto en vite.config.js
server: {
  port: 3001  # O cualquier otro puerto
}
```

### Backend no responde
- Verificar que el backend Flask esté corriendo
- Confirmar URL en `.env` (VITE_API_BASE_URL)
- Revisar CORS en el backend

### Tipos TypeScript errores
```bash
npm run type-check  # Ver errores específicos
```

---

## Recursos

- **README.md** - Documentación completa
- **IMPLEMENTATION_SUMMARY.md** - Resumen técnico detallado
- **Comentarios en código** - Explicaciones inline

Todos los archivos están completamente documentados.
