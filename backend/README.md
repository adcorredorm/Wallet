# Wallet Backend API

API REST para gestión de finanzas personales construido con Flask, SQLAlchemy y PostgreSQL.

## Características

- **CRUD Completo** para Cuentas, Categorías, Transacciones y Transferencias
- **Cálculo Dinámico de Balances** (nunca almacenado en BD)
- **Validación Robusta** con Pydantic
- **Filtros y Paginación** en endpoints de listado
- **Dashboard Consolidado** con patrimonio neto y resumen mensual
- **Arquitectura por Capas** (API → Services → Repositories → Models)
- **Type Hints Completo** en todo el código
- **Migraciones de BD** con Alembic

## Stack Tecnológico

- **Framework**: Flask 3.x
- **ORM**: SQLAlchemy 2.0
- **Validación**: Pydantic v2
- **Base de Datos**: PostgreSQL 15+
- **Migraciones**: Alembic
- **Python**: 3.11+

## Estructura del Proyecto

```
backend/
├── app/
│   ├── __init__.py           # Application factory
│   ├── config.py             # Configuración por entorno
│   ├── extensions.py         # Extensiones Flask
│   ├── models/               # Modelos SQLAlchemy
│   ├── schemas/              # Schemas Pydantic
│   ├── repositories/         # Capa de acceso a datos
│   ├── services/             # Lógica de negocio
│   ├── api/                  # Flask Blueprints
│   ├── utils/                # Utilidades y excepciones
│   └── seeds/                # Datos iniciales
├── alembic/                  # Migraciones de BD
├── requirements.txt          # Dependencias
├── .env.example             # Variables de entorno
└── run.py                   # Entry point

## Instalación

### 1. Prerrequisitos

- Python 3.11 o superior
- PostgreSQL 15 o superior
- pip y virtualenv

### 2. Configurar Base de Datos

```bash
# Crear base de datos PostgreSQL
createdb wallet_db

# O usando psql
psql -U postgres
CREATE DATABASE wallet_db;
CREATE USER wallet_user WITH PASSWORD 'wallet_password';
GRANT ALL PRIVILEGES ON DATABASE wallet_db TO wallet_user;
```

### 3. Instalar Dependencias

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En macOS/Linux:
source venv/bin/activate
# En Windows:
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus valores
# DATABASE_URL=postgresql://wallet_user:wallet_password@localhost:5432/wallet_db
```

### 5. Ejecutar Migraciones

```bash
# Aplicar migraciones
alembic upgrade head

# Seed de categorías predefinidas (opcional)
python -c "from app import create_app; from app.seeds import seed_categories; app = create_app(); app.app_context().push(); seed_categories()"
```

### 6. Iniciar Servidor

```bash
# Desarrollo
python run.py

# O con Flask CLI
export FLASK_APP=run.py
export FLASK_ENV=development
flask run
```

El API estará disponible en `http://localhost:5000`

## API Endpoints

### Cuentas (`/api/v1/accounts`)

- `GET /` - Listar cuentas con balances
- `POST /` - Crear cuenta
- `GET /<id>` - Obtener cuenta con balance
- `PUT /<id>` - Actualizar cuenta
- `DELETE /<id>` - Archivar cuenta (soft delete)
- `GET /<id>/balance` - Obtener balance calculado

### Categorías (`/api/v1/categories`)

- `GET /` - Listar categorías
- `POST /` - Crear categoría
- `GET /<id>` - Obtener categoría con subcategorías
- `PUT /<id>` - Actualizar categoría
- `DELETE /<id>` - Eliminar categoría

### Transacciones (`/api/v1/transactions`)

- `GET /` - Listar transacciones (con filtros y paginación)
- `POST /` - Crear transacción
- `GET /<id>` - Obtener transacción
- `PUT /<id>` - Actualizar transacción
- `DELETE /<id>` - Eliminar transacción

**Filtros disponibles**: `cuenta_id`, `categoria_id`, `tipo`, `fecha_desde`, `fecha_hasta`, `tags`, `page`, `limit`

### Transferencias (`/api/v1/transfers`)

- `GET /` - Listar transferencias (con filtros y paginación)
- `POST /` - Crear transferencia
- `GET /<id>` - Obtener transferencia
- `PUT /<id>` - Actualizar transferencia
- `DELETE /<id>` - Eliminar transferencia

**Filtros disponibles**: `cuenta_id`, `fecha_desde`, `fecha_hasta`, `tags`, `page`, `limit`

### Dashboard (`/api/v1/dashboard`)

- `GET /` - Dashboard completo
- `GET /net-worth` - Patrimonio neto por divisa
- `GET /summary` - Resumen mensual
- `GET /recent-activity` - Actividad reciente

## Reglas de Negocio

### Cuentas
- Balance calculado dinámicamente (nunca almacenado)
- Soft delete: cuentas se marcan como inactivas en lugar de eliminarse
- Soporta divisas: MXN, USD, EUR, GBP, CAD, JPY

### Categorías
- Soporta jerarquía (categorías padre e hijas)
- Tipos: INGRESO, GASTO, AMBOS
- No se puede eliminar si tiene transacciones o subcategorías

### Transacciones
- Tipo debe ser compatible con tipo de categoría
- Categorías tipo AMBOS son compatibles con cualquier transacción
- Monto siempre positivo

### Transferencias
- Solo entre cuentas con la misma divisa
- No se puede transferir a la misma cuenta
- Monto siempre positivo

## Migraciones de Base de Datos

```bash
# Crear nueva migración
alembic revision --autogenerate -m "Descripción del cambio"

# Aplicar migraciones
alembic upgrade head

# Revertir migración
alembic downgrade -1

# Ver historial
alembic history

# Ver versión actual
alembic current
```

## Desarrollo

### Estructura de Código

- **Models**: Definición de tablas SQLAlchemy
- **Schemas**: Validación y serialización con Pydantic
- **Repositories**: Queries y acceso a datos
- **Services**: Lógica de negocio y reglas
- **API**: Endpoints Flask (controllers)

### Principios

- **Type Hints**: Todo el código usa type hints
- **Docstrings**: Todas las clases y funciones públicas documentadas
- **Separation of Concerns**: Capas claramente separadas
- **Business Logic in Services**: Controllers solo manejan HTTP
- **Calculated not Stored**: Balances siempre calculados

## Próximos Pasos

- [ ] Tests unitarios y de integración
- [ ] Autenticación y autorización
- [ ] Rate limiting
- [ ] Documentación OpenAPI/Swagger
- [ ] Docker y docker-compose
- [ ] CI/CD pipeline

## Licencia

MIT
