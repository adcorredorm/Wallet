# Verificación de Instalación - Wallet Backend

Este documento te guiará para verificar que el backend esté correctamente instalado y funcionando.

## Checklist de Verificación

### 1. Estructura de Archivos

Verifica que todos los archivos estén presentes:

```bash
cd /Users/angelcorredor/Code/Wallet/backend

# Verificar archivos principales
ls -la app/models/*.py        # Debe mostrar 5 archivos
ls -la app/schemas/*.py       # Debe mostrar 7 archivos
ls -la app/repositories/*.py  # Debe mostrar 6 archivos
ls -la app/services/*.py      # Debe mostrar 6 archivos
ls -la app/api/*.py           # Debe mostrar 6 archivos
```

### 2. Dependencias

Verificar instalación de dependencias:

```bash
# Activar entorno virtual
source venv/bin/activate

# Verificar Flask
python -c "import flask; print(f'Flask {flask.__version__}')"

# Verificar SQLAlchemy
python -c "import sqlalchemy; print(f'SQLAlchemy {sqlalchemy.__version__}')"

# Verificar Pydantic
python -c "import pydantic; print(f'Pydantic {pydantic.__version__}')"

# Verificar todas las dependencias
pip list | grep -E "Flask|SQLAlchemy|pydantic|alembic|psycopg2"
```

Salida esperada:
```
Flask 3.0.0
SQLAlchemy 2.0.23
Pydantic 2.5.3
```

### 3. PostgreSQL

Verificar que PostgreSQL esté corriendo:

```bash
# Con Docker
docker ps | grep wallet_postgres

# Sin Docker (macOS/Linux)
pg_isready -h localhost -p 5432

# Conectar a la base de datos
psql -h localhost -U wallet_user -d wallet_db
# Password: wallet_password
# Dentro de psql:
\dt  # Listar tablas (debería estar vacío antes de migraciones)
\q   # Salir
```

### 4. Importaciones Python

Verificar que todas las importaciones funcionen:

```bash
python << 'EOF'
# Test imports
from app import create_app
from app.models import Account, Category, Transaction, Transfer
from app.schemas import AccountCreate, CategoryCreate
from app.repositories import AccountRepository
from app.services import AccountService
from app.api.accounts import accounts_bp

print("✅ Todas las importaciones exitosas")
EOF
```

### 5. Aplicación Flask

Verificar que la aplicación se pueda crear:

```bash
python << 'EOF'
from app import create_app

app = create_app('development')
print(f"✅ App creada: {app.name}")
print(f"✅ Debug mode: {app.debug}")
print(f"✅ Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:30]}...")
EOF
```

### 6. Migraciones Alembic

Verificar configuración de Alembic:

```bash
# Ver configuración
alembic current
# Debe mostrar: "No current revision" (antes de primera migración)

# Ver historial de migraciones disponibles
alembic history
# Debe mostrar la migración 001_initial_schema
```

### 7. Base de Datos

Aplicar migraciones y verificar tablas:

```bash
# Aplicar migraciones
alembic upgrade head

# Verificar tablas creadas
psql -h localhost -U wallet_user -d wallet_db -c "\dt"
```

Tablas esperadas:
- `alembic_version`
- `cuentas`
- `categorias`
- `transacciones`
- `transferencias`

### 8. Seeds

Verificar seed de categorías:

```bash
# Ejecutar seed
python cli.py seed

# Verificar categorías en BD
psql -h localhost -U wallet_user -d wallet_db -c "SELECT nombre, tipo FROM categorias WHERE categoria_padre_id IS NULL;"
```

Debe mostrar 12 categorías (Salario, Freelance, Alimentación, etc.)

### 9. Servidor

Iniciar y verificar servidor:

```bash
# Terminal 1: Iniciar servidor
python run.py
```

Debe mostrar algo como:
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
```

### 10. Health Check

En otra terminal:

```bash
# Health check
curl http://localhost:5000/health

# Salida esperada:
# {"service":"wallet-api","status":"healthy"}
```

### 11. Endpoints del API

Verificar endpoints principales:

```bash
# Listar categorías (debe mostrar las 12 predefinidas)
curl http://localhost:5000/api/v1/categories | python -m json.tool

# Crear una cuenta de prueba
curl -X POST http://localhost:5000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Test Account",
    "tipo": "debito",
    "divisa": "MXN",
    "descripcion": "Account for testing"
  }' | python -m json.tool

# Listar cuentas (debe mostrar la cuenta recién creada con balance 0)
curl http://localhost:5000/api/v1/accounts | python -m json.tool

# Dashboard
curl http://localhost:5000/api/v1/dashboard | python -m json.tool
```

### 12. Test Suite

Ejecutar el script de pruebas:

```bash
python test_api.py
```

Debe ejecutar múltiples pruebas y mostrar las respuestas. Algunas pruebas pueden fallar por reglas de negocio (eso es esperado).

### 13. CLI Commands

Verificar comandos CLI:

```bash
# Ayuda
python cli.py --help

# Listar rutas
python cli.py routes
```

Debe mostrar todos los endpoints disponibles organizados por blueprint.

### 14. Make Commands

Verificar Makefile:

```bash
# Ver comandos disponibles
make help

# Test comando routes
make routes
```

## Checklist Final

Marca cada item cuando lo hayas verificado:

- [ ] Estructura de archivos completa (46 archivos Python)
- [ ] Dependencias instaladas (Flask, SQLAlchemy, Pydantic, etc.)
- [ ] PostgreSQL corriendo y accesible
- [ ] Importaciones Python funcionan
- [ ] Aplicación Flask se crea correctamente
- [ ] Alembic configurado
- [ ] Migraciones aplicadas (4 tablas + alembic_version)
- [ ] Seeds ejecutados (12 categorías)
- [ ] Servidor inicia sin errores
- [ ] Health check responde 200
- [ ] Endpoints del API funcionan
- [ ] Test script ejecuta
- [ ] CLI commands funcionan
- [ ] Make commands funcionan

## Problemas Comunes

### Error: "ModuleNotFoundError: No module named 'app'"

**Solución**: Asegúrate de estar en el directorio `/backend` y que el entorno virtual esté activado.

```bash
cd /Users/angelcorredor/Code/Wallet/backend
source venv/bin/activate
```

### Error: "psycopg2.OperationalError: could not connect to server"

**Solución**: PostgreSQL no está corriendo.

```bash
# Con Docker
docker-compose up -d postgres

# Sin Docker (macOS)
brew services start postgresql@15
```

### Error: "alembic.util.exc.CommandError: Target database is not up to date"

**Solución**: Aplicar migraciones pendientes.

```bash
alembic upgrade head
```

### Error: "ImportError: cannot import name 'X' from 'app.models'"

**Solución**: Verificar que `__init__.py` en models/ tenga todos los imports.

```bash
cat app/models/__init__.py
# Debe importar Account, Category, Transaction, Transfer
```

### Error al crear transacción: "La categoria de tipo 'gasto' no es compatible..."

**Solución**: Esto es esperado. Estás intentando crear una transacción de tipo ingreso con una categoría de tipo gasto. Usa una categoría compatible o crea una categoría tipo "ambos".

## Verificación Completa Exitosa

Si todos los checks pasaron, verás:

✅ Backend instalado correctamente
✅ Base de datos configurada
✅ API funcionando
✅ Seeds cargados
✅ Todos los endpoints accesibles

El backend está listo para:
1. Desarrollo del frontend
2. Implementación de tests
3. Deployment

## Siguientes Pasos

1. **Explorar API**: Usar `API_EXAMPLES.md` para probar todos los endpoints
2. **Leer Documentación**: Revisar `README.md` para entender la arquitectura
3. **Frontend**: Continuar con implementación del frontend Vue.js
4. **Tests**: Implementar tests unitarios en `tests/`

## Soporte

Si encuentras problemas:
1. Revisa `QUICKSTART.md` para instrucciones de instalación
2. Verifica logs del servidor (`python run.py`)
3. Revisa `IMPLEMENTATION_SUMMARY.md` para estructura completa
