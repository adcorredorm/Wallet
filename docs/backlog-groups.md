# Backlog Groups — 2026-03-25

Agrupación de tickets activos (TODO + Backlog) por tema para planificar trabajo futuro.
Nota: encontrados ~28 de 39 tickets activos totales (11 TODO + 28 Backlog según Kanban).

---

## Grupo A — Bugs críticos activos
_Fixes puntuales de alta prioridad. Atacar primero._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| BUG: GET /api/v1/settings y /exchange-rates retornan 401 para usuario autenticado | TODO | Medium | 32779901-d1b8-81a6 |
| BUG: Título personalizado de transferencia no se persiste al crear | Backlog | Medium | 32779901-d1b8-81fe |
| UX: dashboard no se actualiza tras sync inicial sin hard refresh | TODO | Medium | 32579901-d1b8-81b4 |

> ⚠️ El ticket de dashboard puede estar resuelto con el nuevo flujo de login multiusuario — verificar antes de trabajar.

---

## Grupo B — Robustez del sync
_Todos tocan sync-manager, stores y Dexie. Van juntos en una sesión._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| fix(sync): mutaciones no deben morir por MAX_RETRIES cuando backend inaccesible | Backlog | Medium | 32279901-d1b8-81b7 |
| fix(sync): fullReadSync no poda widgets eliminados dentro de dashboards existentes | Backlog | Medium | 32279901-d1b8-81e0 |
| fix(store): revalidación en background puede eliminar dashboards creados offline | Backlog | Medium | 32279901-d1b8-8132 |
| UI: mostrar registros con error de sync y permitir reintentar o descartar | Backlog | Low | 32179901-d1b8-81c6 |

> El de MAX_RETRIES es el más importante y bloquea conceptualmente al de UI errores. Orden sugerido: MAX_RETRIES → dashboards offline → fullReadSync widgets → UI errores.

---

## Grupo C — UX pulido (Frontend)
_Mejoras de experiencia de usuario. Independientes entre sí, se pueden paralelizar._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| UX: categorías archivadas — lista agrupada, cascade restore y bloqueo de padre archivado | Backlog | Medium | 32379901-d1b8-816d |
| Settings: opción para deshabilitar sync con backend (modo offline total) | Backlog | Medium | 32679901-d1b8-81df |
| UX: al crear un dashboard nuevo, entrar en modo edición automáticamente | Backlog | Low | 32579901-d1b8-818b |
| BUG: Nombre de cuenta truncado en Actividad Reciente del dashboard | Backlog | Low | 32779901-d1b8-8115 |
| BUG: Botones deshabilitados momentáneamente en /accounts/new al cargar | Backlog | Low | 32779901-d1b8-81b1 |
| BUG: FAB no se cierra con tecla Escape | Backlog | Low | 32779901-d1b8-8147 |
| BUG: CurrencyDisplay recibe amount como string en vez de number (Vue warning) | Backlog | Low | 32f79901-d1b8-8156 |

---

## Grupo D — Features de cuentas
_Un feature cohesivo: reordenar cuentas + emojis en cuentas (el ticket lo menciona explícitamente)._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Habilidad para reordenar las cuentas (+ agregar emoji a cuentas) | TODO | Medium | 32979901-d1b8-8068 |

---

## Grupo E — Deuda técnica Backend
_Limpieza y corrección de warnings/deprecaciones._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Chore: reemplazar Query.get() por Session.get() en modelos SQLAlchemy | Backlog | Low | 32679901-d1b8-817c |
| Limpiar sistema Alembic duplicado (backend/alembic/ vs backend/migrations/) | TODO | Low | 32879901-d1b8-8136 |

---

## Grupo F — Deuda técnica Frontend
_Mejoras de arquitectura y calidad de código._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Refactor: composable useOfflineMutation para escrituras offline-first | Backlog | Medium | 32279901-d1b8-81d8 |
| Revisar sync y visualización de entidades creadas vía API directa | Backlog | Medium | 32179901-d1b8-8196 |
| Explorar: filtrado temporal en stats panel (account/category detail) | Backlog | Medium | 32679901-d1b8-8163 |
| Revisar límites de IndexedDB (offline-first) | Backlog | Low | 31b79901-d1b8-8172 |

> ⚠️ Verificar si los dos tickets de TS errors siguen siendo válidos post-Grupo B (que cerró "0 errores TypeScript"):
> - Fix: corregir errores de TypeScript pre-existentes (TODO, Medium) — 32679901-d1b8-8132-9f1b
> - Cleanup: fix pre-existing TypeScript type-check errors (TODO, Low) — 32079901-d1b8-816c

---

## Grupo G — Agentes y DevOps
_Mejoras al sistema de desarrollo._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Mejora agentes: permisos y entornos de ejecución | TODO | Medium | 32179901-d1b8-811b |

---

## Grupo H — Roadmap futuro (features grandes)
_Requieren ADD y brainstorming antes de implementar. Sin fecha._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Presupuestos sobre cuentas y categorías | Backlog | Medium | 31b79901-d1b8-81a7 |
| Widget / accesos rápidos Android | Backlog | Medium | 31b79901-d1b8-8152 |
| Cuentas especiales para activos no monetarios | Backlog | Medium | 31b79901-d1b8-8191 |
| Cuentas compartidas y split de gastos | Backlog | Medium | 31b79901-d1b8-81b7 |
| Operaciones con fee | Backlog | Medium | 31b79901-d1b8-814a |

---

## Orden sugerido de ataque

```
A (bugs críticos) → B (sync robustez) → C (UX pulido) + D (cuentas) → E + F (deuda técnica) → G (agentes) → H (roadmap)
```
