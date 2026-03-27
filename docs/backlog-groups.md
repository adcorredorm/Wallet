# Backlog Groups — 2026-03-26

29 tickets activos (Backlog + TODO) agrupados por area testeable.
Criterio: tickets que tocan las mismas pantallas/modulos y se pueden desarrollar y testear juntos.

---

## Grupo A — Bugs criticos activos — COMPLETADO
## Grupo B — Robustez del sync — COMPLETADO

---

## Grupo CD — Bloque 1: bugs rapidos + deuda (C, D-fix, H, I-parcial)
_Tickets triviales/small sin dependencias entre si. Se paralelizan con agentes frontend + backend._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| BUG: CurrencyDisplay recibe amount como string en vez de number | Backlog | Low | 32f79901-d1b8-8156 |
| BUG: Nombre de cuenta truncado en Actividad Reciente del dashboard | Backlog | Low | 32779901-d1b8-8115 |
| UX: al crear un dashboard nuevo, entrar en modo edicion automaticamente | Backlog | Low | 32579901-d1b8-818b |
| BUG: Botones deshabilitados momentaneamente en /accounts/new al cargar | Backlog | Low | 32779901-d1b8-81b1 |
| BUG: FAB no se cierra con tecla Escape | Backlog | Low | 32779901-d1b8-8147 |
| BUG: Paginacion regresa a pagina 1 espontaneamente | TODO | Medium | (buscar en Kanban) |
| ~~Chore: reemplazar Query.get() por Session.get() en modelos SQLAlchemy~~ | Done | Low | 32679901-d1b8-817c |
| Deuda: ValidationError handler no es JSON-safe en Pydantic v2 | Backlog | Medium | (buscar en Kanban) |

---

## Grupo CD — Bloque 2: reorder cuentas + Alembic cleanup (requieren diseno)
_Ambos tocan migraciones de DB. Requieren ADD antes de implementar._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Habilidad para reordenar las cuentas | TODO | Medium | 32979901-d1b8-8068 |
| Limpiar sistema Alembic duplicado (backend/alembic/ vs backend/migrations/) | TODO | Low | 32879901-d1b8-8136 |

---

## Grupo E — Categorias: archivado avanzado
_Toca CategoryListView, archive/restore, jerarquia padre-hijo. Testear en /categories._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| UX: categorias archivadas — lista agrupada, cascade restore y bloqueo de padre archivado | Backlog | Medium | 32379901-d1b8-816d |

---

## Grupo F — Auth & Sesion
_Tocan el sistema de autenticacion, tokens, multi-dispositivo. Testear con login/logout, multiples dispositivos._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| INVESTIGAR: Inicio de sesion en multiples dispositivos | TODO | Medium | (buscar en Kanban) |

> Ticket de token no reconocido cerrado (resuelto con grace period del Grupo B).

---

## Grupo G — Sync & Offline avanzado
_Tocan sync-manager, mutation queue, stores, y settings de sync. Testear con escenarios offline, API directa, y settings._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Settings: opcion para deshabilitar sync con backend (modo offline total) | Backlog | Medium | 32679901-d1b8-81df |
| Refactor: composable useOfflineMutation para escrituras offline-first | Backlog | Medium | 32279901-d1b8-81d8 |
| Revisar sync y visualizacion de entidades creadas via API directa | Backlog | Medium | 32179901-d1b8-8196 |
| Revisar limites de IndexedDB (offline-first) | Backlog | Low | 31b79901-d1b8-8172 |

---

## Grupo H — UI bugs menores — ABSORBIDO en Grupo CD Bloque 1
## Grupo I — Deuda tecnica Backend — ABSORBIDO en Grupo CD (Bloque 1 + Bloque 2)

---

## Grupo J — Deuda tecnica Frontend (TypeScript) — COMPLETADO

Ambos tickets cerrados. `vue-tsc --noEmit` limpio desde el Grupo B formularios (commit 32e79901).

---

## Grupo K — Stats & Filtrado
_Toca account detail, category detail, y los paneles de estadisticas. Testear en vistas de detalle._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Explorar: filtrado temporal en stats panel (account/category detail) | Backlog | Medium | 32679901-d1b8-8163 |

---

## Grupo L — MCP & Integraciones dev
_Herramientas de desarrollo y MCP servers. No afectan el producto final._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Anadir MCP de PostgreSQL para QA | TODO | Medium | (buscar en Kanban) |
| Exponer MCP en el backend | Backlog | Medium | (buscar en Kanban) |
| Configurar MCP de GitHub para el repo | Backlog | Medium | (buscar en Kanban) |

---

## Grupo M — Roadmap futuro (features grandes)
_Requieren ADD y brainstorming antes de implementar. Sin fecha._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| Presupuestos sobre cuentas y categorias | Backlog | Medium | 31b79901-d1b8-81a7 |
| Transacciones recurrentes | Backlog | Medium | (buscar en Kanban) |
| Widget / accesos rapidos Android | Backlog | Medium | 31b79901-d1b8-8152 |
| Cuentas especiales para activos no monetarios | Backlog | Medium | 31b79901-d1b8-8191 |
| Cuentas compartidas y split de gastos | Backlog | Medium | 31b79901-d1b8-81b7 |
| Operaciones con fee | Backlog | Medium | 31b79901-d1b8-814a |
| Exportacion de datos para ML | Backlog | Medium | (buscar en Kanban) |
| Crear bot de TG para subir fotos y mensajes rapidos de gastos | Backlog | Medium | (buscar en Kanban) |
| Poder leer mails y tal vez SMS para crear entradas en el app | Backlog | Medium | (buscar en Kanban) |

---

## Orden sugerido de ataque

```
CD-Bloque1 (bugs + deuda rapida) → CD-Bloque2 (reorder + Alembic)
→ F (auth, verificar si resuelto) → E (categorias) → G (sync avanzado)
→ K (stats) → L (MCP/dev tools) → M (roadmap)
```

Notas:
- CD-Bloque1: 8 tickets triviales/small, paralelizables — una sesion
- CD-Bloque2: 2 tickets medium que tocan migraciones — requiere ADD
- F requiere verificacion antes de trabajar (puede estar resuelto post Grupo B)
- G es el grupo mas complejo — requiere diseno previo
- L es trabajo de infraestructura dev, no afecta al usuario
- M son features grandes que necesitan ADD
