# Wallet

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

Aplicacion de seguimiento y analisis de gastos para finanzas personales. Permite registrar transacciones, gestionar multiples cuentas y obtener una vision clara del estado financiero personal.

## Caracteristicas

- Gestion de multiples cuentas (debito, credito, efectivo) en distintas divisas
- Registro de transacciones (ingresos y gastos) con categorias jerarquicas
- Transferencias entre cuentas propias
- Balance calculado dinamicamente (nunca almacenado)
- Dashboard con patrimonio neto y resumen mensual
- Categorias predefinidas con subcategorias
- UI mobile-first con dark mode

## Stack

| Capa | Tecnologia |
|------|-----------|
| Frontend | Vue 3 + TypeScript + Pinia + Tailwind CSS |
| Backend | Flask + SQLAlchemy + Pydantic |
| Base de datos | PostgreSQL 15 |
| Infraestructura | Docker + Docker Compose |

## Requisitos

- Docker 24+
- Docker Compose 2.20+
- 4 GB RAM minimo

## Inicio rapido

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd Wallet
```

### 2. Crear el archivo de entorno

```bash
cp .env.example .env
```

Los valores por defecto en `.env.example` funcionan para desarrollo local sin modificaciones.

### 3. Levantar los servicios

```bash
docker-compose up --build
```

Espera hasta ver los tres servicios en estado `healthy` (toma 1-2 minutos la primera vez).

### 4. Verificar que todo funcione

```bash
# Backend
curl http://localhost:5001/health

# Frontend
open http://localhost:3000
```

### Servicios disponibles

| Servicio | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:5001 |
| pgAdmin (dev) | http://localhost:5050 |

> pgAdmin requiere levantar con el profile dev: `docker-compose --profile dev up`
> Credenciales: `admin@wallet.local` / `admin`

## Comandos utiles

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio especifico
docker-compose logs -f backend

# Reiniciar un servicio
docker-compose restart backend

# Detener (preserva datos)
docker-compose down

# Detener y borrar volumenes (reset completo)
docker-compose down -v

# Reconstruir imagenes (despues de cambiar dependencias)
docker-compose build --no-cache

# Acceder a la base de datos
docker-compose exec db psql -U wallet_user -d wallet_db

# Ejecutar migraciones manualmente
docker-compose exec backend flask db upgrade
```

## Variables de entorno

El archivo `.env` controla la configuracion de todos los servicios. Las principales:

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `DB_NAME` | `wallet_db` | Nombre de la base de datos |
| `DB_USER` | `wallet_user` | Usuario de PostgreSQL |
| `DB_PASSWORD` | `wallet_password` | Contrasena de PostgreSQL |
| `SECRET_KEY` | `dev-secret-key-...` | Clave secreta de Flask |
| `FLASK_ENV` | `development` | Entorno de Flask |
| `DEBUG` | `False` | Modo debug |
| `VITE_API_BASE_URL` | `http://localhost:5001` | URL del backend para el frontend |

## API

El backend expone una API REST en `/api/v1/`:

| Recurso | Endpoints |
|---------|-----------|
| Cuentas | `GET/POST /accounts`, `GET/PUT/DELETE /accounts/:id` |
| Categorias | `GET/POST /categories`, `GET/PUT/DELETE /categories/:id` |
| Transacciones | `GET/POST /transactions`, `GET/PUT/DELETE /transactions/:id` |
| Transferencias | `GET/POST /transfers`, `GET/PUT/DELETE /transfers/:id` |
| Dashboard | `GET /dashboard`, `GET /dashboard/net-worth`, `GET /dashboard/summary` |

## Estructura del proyecto

```
Wallet/
├── backend/          # API Flask
│   ├── app/
│   │   ├── api/      # Blueprints (endpoints)
│   │   ├── models/   # Modelos SQLAlchemy
│   │   ├── schemas/  # Validacion Pydantic
│   │   ├── services/ # Logica de negocio
│   │   └── repositories/ # Acceso a datos
│   └── alembic/      # Migraciones
├── frontend/         # SPA Vue 3
│   └── src/
│       ├── views/    # Vistas por entidad
│       ├── components/ # Componentes reutilizables
│       ├── stores/   # Estado global (Pinia)
│       └── api/      # Cliente HTTP
├── docker-compose.yml
├── docker-compose.dev.yml
└── docker-compose.prod.yml
```

## Despliegue en produccion

> Antes de desplegar a produccion asegurate de:
> - [ ] Generar un `SECRET_KEY` fuerte (ej: `openssl rand -hex 32`)
> - [ ] Cambiar `DB_PASSWORD` por una contrasena segura
> - [ ] Configurar `FLASK_CORS_ORIGINS` con el dominio real
> - [ ] Crear el directorio de datos: `sudo mkdir -p /var/lib/wallet/data`
> - [ ] Configurar un reverse proxy (Nginx, Caddy) para HTTPS

```bash
# Construir imagenes de produccion
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Levantar en modo produccion
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verificar estado
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

### Backup de la base de datos

```bash
# Exportar
docker-compose exec db pg_dump -U wallet_user wallet_db > backup_$(date +%Y%m%d).sql

# Restaurar
docker-compose exec -T db psql -U wallet_user wallet_db < backup.sql
```

## Licencia

Copyright (C) 2026 Angel Corredor

Este proyecto se distribuye bajo la licencia **GNU Affero General Public License v3.0 (AGPL-3.0)**.
Cualquier trabajo derivado, incluyendo modificaciones usadas para ofrecer servicios en red, debe
publicarse bajo la misma licencia. Ver [LICENSE](LICENSE) para el texto completo.
