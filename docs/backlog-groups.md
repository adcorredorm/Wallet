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
| F | Auth & Sesion | 2 cerrados (1 investigacion + 1 feature) |
| G | Sync & Offline avanzado | 4 cerrados (1 toggle + 1 refactor + 1 ya resuelto + 1 investigacion) |

---

## Grupo E — Categorias: archivado avanzado
_Toca CategoryListView, archive/restore, jerarquia padre-hijo. Testear en /categories._

| Ticket | Status | Prioridad | ID Notion |
|--------|--------|-----------|-----------|
| UX: categorias archivadas — lista agrupada, cascade restore y bloqueo de padre archivado | Backlog | Medium | 32379901-d1b8-816d |

---

---

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
E (categorias) → K (stats) → L (MCP/dev tools) → M (roadmap)
```

Notas:
- E es feature mediano — una sesion
- L es trabajo de infraestructura dev, no afecta al usuario
- M son features grandes que necesitan ADD
