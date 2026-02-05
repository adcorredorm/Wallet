# Wallet Backend - Quick Start Guide

Guía rápida para iniciar el backend del API de Wallet en 5 minutos.

## Prerrequisitos

- Python 3.11+
- PostgreSQL 15+
- pip y virtualenv

## Inicio Rápido con Docker (Recomendado)

### 1. Iniciar PostgreSQL con Docker

```bash
# Desde la raíz del proyecto
docker-compose up -d postgres
```

Esto iniciará PostgreSQL en el puerto 5432 con:
- **Database**: wallet_db
- **Usuario**: wallet_user
- **Password**: wallet_password

### 2. Configurar Backend

```bash
cd backend

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar configuración
cp .env.example .env
```

### 3. Inicializar Base de Datos

```bash
# Opción 1: Usando Make (más simple)
make init-db

# Opción 2: Usando CLI
python cli.py init-db

# Opción 3: Manual
alembic upgrade head
python -c "from app import create_app; from app.seeds import seed_categories; app = create_app(); app.app_context().push(); seed_categories()"
```

### 4. Iniciar Servidor

```bash
# Opción 1: Usando Make
make dev

# Opción 2: Usando CLI
python cli.py run

# Opción 3: Direct
python run.py
```

El servidor estará disponible en: **http://localhost:5000**

### 5. Probar el API

```bash
# Health check
curl http://localhost:5000/health

# Listar categorías predefinidas
curl http://localhost:5000/api/v1/categories

# Ejecutar suite de pruebas
python test_api.py
```

## Inicio Manual (Sin Docker)

### 1. Instalar y Configurar PostgreSQL

```bash
# macOS (con Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt-get install postgresql-15
sudo systemctl start postgresql

# Crear base de datos y usuario
psql -U postgres
CREATE DATABASE wallet_db;
CREATE USER wallet_user WITH PASSWORD 'wallet_password';
GRANT ALL PRIVILEGES ON DATABASE wallet_db TO wallet_user;
\q
```

### 2. Continuar desde el paso 2 del inicio rápido

## Comandos Útiles

### Make Commands

```bash
make help        # Ver todos los comandos disponibles
make install     # Instalar dependencias
make dev         # Iniciar servidor de desarrollo
make init-db     # Inicializar base de datos
make seed        # Seed de categorías
make reset-db    # Reset completo de BD (¡cuidado!)
make routes      # Listar todas las rutas del API
make clean       # Limpiar archivos cache
```

### CLI Commands

```bash
python cli.py --help                    # Ver ayuda
python cli.py run                       # Iniciar servidor
python cli.py init-db                   # Inicializar BD
python cli.py seed                      # Seed de categorías
python cli.py routes                    # Listar rutas
python cli.py migrate "mensaje"         # Crear migración
python cli.py upgrade                   # Aplicar migraciones
python cli.py downgrade                 # Revertir migración
```

### Alembic (Migraciones)

```bash
alembic current                         # Ver versión actual
alembic history                         # Ver historial
alembic upgrade head                    # Actualizar a última versión
alembic downgrade -1                    # Revertir última migración
alembic revision --autogenerate -m "msg" # Crear nueva migración
```

## Estructura de Datos Inicial

Después de `make init-db`, tendrás:

### Categorías de Gastos
- Alimentación (Supermercado, Restaurantes, Cafetería)
- Transporte (Gasolina, Transporte Público, Taxi/Uber)
- Vivienda (Renta, Servicios, Mantenimiento)
- Entretenimiento (Streaming, Cine, Eventos)
- Salud (Medicamentos, Consultas, Gimnasio)
- Educación (Cursos, Libros, Material)
- Compras (Ropa, Tecnología, Hogar)
- Otros Gastos

### Categorías de Ingresos
- Salario
- Freelance
- Inversiones
- Otros Ingresos

## Primeros Pasos con el API

### 1. Crear una cuenta

```bash
curl -X POST http://localhost:5000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Mi Cuenta de Ahorro",
    "tipo": "debito",
    "divisa": "MXN",
    "descripcion": "Cuenta principal"
  }'
```

### 2. Crear una transacción

Guarda el `id` de la cuenta del paso anterior y un `id` de categoría:

```bash
curl -X POST http://localhost:5000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "gasto",
    "monto": 250.50,
    "fecha": "2024-01-15",
    "cuenta_id": "UUID-DE-LA-CUENTA",
    "categoria_id": "UUID-DE-CATEGORIA",
    "titulo": "Compra supermercado",
    "descripcion": "Despensa semanal"
  }'
```

### 3. Ver balance de la cuenta

```bash
curl http://localhost:5000/api/v1/accounts/UUID-DE-LA-CUENTA/balance
```

### 4. Ver dashboard

```bash
curl http://localhost:5000/api/v1/dashboard
```

## Recursos Adicionales

- **README.md**: Documentación completa
- **API_EXAMPLES.md**: Ejemplos detallados de todos los endpoints
- **test_api.py**: Script de pruebas interactivo

## Solución de Problemas

### Error: "Connection refused" al conectar a PostgreSQL

```bash
# Verificar que PostgreSQL esté corriendo
docker ps  # Si usas Docker
# O
pg_isready -h localhost -p 5432

# Reiniciar PostgreSQL
docker-compose restart postgres
```

### Error: "ModuleNotFoundError"

```bash
# Asegúrate de estar en el entorno virtual
source venv/bin/activate

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: "alembic.util.exc.CommandError"

```bash
# Resetear migraciones
alembic downgrade base
alembic upgrade head
```

### Ver logs detallados

```bash
# Activar modo debug en .env
FLASK_ENV=development

# O correr con debug
python cli.py run --debug
```

## Siguiente Paso: Frontend

Una vez que el backend esté funcionando, puedes continuar con el frontend en `/frontend`

## Soporte

Para más información, revisa:
- README.md
- API_EXAMPLES.md
- agent_staging/00_MVP_plan.md
