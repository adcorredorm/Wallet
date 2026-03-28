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
| E | Categorias: archivado avanzado | 1 cerrado (won't do — sobreingeniería) |

---

## Grupo L — MCP & Integraciones dev (parcial)
_Herramientas de desarrollo y MCP servers. No afectan el producto final._

| Ticket | Status | Prioridad | Notas |
|--------|--------|-----------|-------|
| Anadir MCP de PostgreSQL para QA | Done | Medium | Neon MCP (prod, read-only) + @henkey/postgres-mcp-server (local) |
| Exponer MCP en el backend | Pospuesto | Medium | Se implementará junto con Bot de TG (Grupo M-T3) |
| Configurar MCP de GitHub para el repo | Won't do | Medium | `gh` CLI es suficiente, MCP no agrega valor |

---

## Quick wins (sueltos)
_Tickets pequeños que no pertenecen a un grupo. Se pueden hacer en cualquier momento._

| Ticket | Status | Complejidad | ID Notion |
|--------|--------|-------------|-----------|
| Ocultar saldos en home (modo privacidad) | TODO | Baja | 33079901-d1b8-81ed-a2ee-d6a2bb371b14 |

---

## Grupo M — Roadmap futuro (features grandes)
_Requieren ADD y brainstorming antes de implementar. Brainstorm completado 2026-03-27._

### Tier 1 — Extensiones del modelo actual (bajo riesgo, alcance acotado)

| Ticket | Complejidad | ID Notion |
|--------|-------------|-----------|
| Operaciones con fee | Baja | 31b79901-d1b8-814a-9b2e-e37f7e44b812 |
| Presupuestos sobre cuentas y categorias | Media | 31b79901-d1b8-81a7-a722-e5145a47e332 |
| Transacciones recurrentes | Media-Alta | 31b79901-d1b8-81fc-9d36-ebdf0e9f7d11 |
| Exportacion de transacciones para analisis | Baja | 31b79901-d1b8-8188-bc09-c6955e2de59b |
| Backup/Restore completo de datos offline | Media | 33079901-d1b8-81cf-bc26-ec93e648ff62 |

### Tier 2 — Requieren investigacion tecnica significativa

| Ticket | Complejidad | ID Notion |
|--------|-------------|-----------|
| Widget / accesos rapidos Android | Baja | 31b79901-d1b8-8152-b7fe-c6eb7897b0e0 |
| Cuentas especiales para activos no monetarios | Alta | 31b79901-d1b8-8191-aab5-c07de4f67671 |

### Tier 3 — Integraciones externas (asume Grupo L completado)

| Ticket | Complejidad | ID Notion |
|--------|-------------|-----------|
| Bot de TG para gastos rapidos | Alta | 32779901-d1b8-80e6-8880-c2217e269187 |
| Leer mails/SMS para crear entradas | Media | 32079901-d1b8-805f-8c49-efb455b5769e |

### Tier 4 — Cambio arquitectural mayor

| Ticket | Complejidad | ID Notion |
|--------|-------------|-----------|
| Cuentas compartidas y split de gastos | Muy Alta | 31b79901-d1b8-81b7-85de-cbc0385be3c6 |

### Dependencias clave

```
Grupo L (MCP backend, pospuesto) ──→ Bot de TG (se implementará junto)
                                 ──→ Leer mails/SMS
Soporte multiusuario ───→ Cuentas compartidas
Activos no monetarios ──→ API externa de precios (acciones, crypto)
Transacciones recurrentes ──→ Bandeja de pendientes ←── Leer mails/SMS
```

---

## Orden sugerido de ataque

```
L (MCP/dev tools) → M-T1 → M-T2 → M-T3 → M-T4
```

Notas:
- L es trabajo de infraestructura dev, no afecta al usuario
- M-T1 son features aditivas que no rompen el modelo actual
- M-T2 requiere investigacion previa (APIs de precios, PWA shortcuts)
- M-T3 depende de que Grupo L este completado
- M-T4 es el mas complejo — requiere multiusuario como prerequisito
- Cada ticket tiene hallazgos detallados del brainstorm en Notion
