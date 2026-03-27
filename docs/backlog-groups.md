# Backlog Groups — 2026-03-26

Tickets activos agrupados por area testeable.
Criterio: tickets que tocan las mismas pantallas/modulos y se pueden desarrollar y testear juntos.

---

## Completados

| Grupo | Descripcion | Tickets |
|-------|-------------|---------|
| A | Bugs criticos activos | todos cerrados |
| B | Robustez del sync | todos cerrados |
| CD-Bloque 1 | Bugs rapidos + deuda (C, D-fix, H, I-parcial) | 8 cerrados (7 implementados + 1 ya resuelto) |
| H | UI bugs menores | absorbido en CD-Bloque 1 |
| I | Deuda tecnica Backend (parcial) | absorbido en CD-Bloque 1 + Bloque 2 |
| J | Deuda tecnica Frontend (TypeScript) | todos cerrados |
| CD-Bloque 2 | Reorder cuentas + icon + Alembic cleanup | 2 cerrados + icon bonus |

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
| UX: en modo invitado, reemplazar boton Logout por "Borrar todo" con confirmacion | Backlog | Medium | 33079901-d1b8-8152 |

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
F (auth, verificar si resuelto) → E (categorias) → G (sync avanzado) → K (stats)
→ L (MCP/dev tools) → M (roadmap)
```

Notas:
- F requiere verificacion antes de trabajar (puede estar resuelto post Grupo B)
- E es feature mediano — una sesion
- G es el grupo mas complejo — requiere diseno previo
- L es trabajo de infraestructura dev, no afecta al usuario
- M son features grandes que necesitan ADD
