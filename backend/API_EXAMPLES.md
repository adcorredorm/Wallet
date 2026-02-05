# Wallet API - Ejemplos de Uso

Este documento contiene ejemplos de cómo usar cada endpoint del API.

## Base URL

```
http://localhost:5000/api/v1
```

## Health Check

```bash
curl http://localhost:5000/health
```

## Cuentas (Accounts)

### Listar todas las cuentas

```bash
curl http://localhost:5000/api/v1/accounts
```

Con cuentas archivadas:

```bash
curl http://localhost:5000/api/v1/accounts?include_archived=true
```

### Crear una cuenta

```bash
curl -X POST http://localhost:5000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Cuenta de Ahorro",
    "tipo": "debito",
    "divisa": "MXN",
    "descripcion": "Mi cuenta principal de ahorro",
    "tags": ["ahorro", "personal"]
  }'
```

### Obtener una cuenta por ID

```bash
curl http://localhost:5000/api/v1/accounts/{account_id}
```

### Actualizar una cuenta

```bash
curl -X PUT http://localhost:5000/api/v1/accounts/{account_id} \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Cuenta de Ahorro Plus",
    "descripcion": "Cuenta actualizada"
  }'
```

### Archivar una cuenta

```bash
curl -X DELETE http://localhost:5000/api/v1/accounts/{account_id}
```

### Obtener balance de una cuenta

```bash
curl http://localhost:5000/api/v1/accounts/{account_id}/balance
```

## Categorías (Categories)

### Listar todas las categorías

```bash
curl http://localhost:5000/api/v1/categories
```

Filtrar por tipo:

```bash
curl http://localhost:5000/api/v1/categories?tipo=gasto
```

### Crear una categoría

```bash
curl -X POST http://localhost:5000/api/v1/categories \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Entretenimiento",
    "tipo": "gasto",
    "icono": "film",
    "color": "#EC4899"
  }'
```

Crear una subcategoría:

```bash
curl -X POST http://localhost:5000/api/v1/categories \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Netflix",
    "tipo": "gasto",
    "icono": "tv",
    "categoria_padre_id": "{parent_category_id}"
  }'
```

### Obtener una categoría por ID

```bash
curl http://localhost:5000/api/v1/categories/{category_id}
```

### Actualizar una categoría

```bash
curl -X PUT http://localhost:5000/api/v1/categories/{category_id} \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Entretenimiento Digital",
    "color": "#F97316"
  }'
```

### Eliminar una categoría

```bash
curl -X DELETE http://localhost:5000/api/v1/categories/{category_id}
```

## Transacciones (Transactions)

### Listar transacciones

```bash
curl http://localhost:5000/api/v1/transactions
```

Con filtros:

```bash
curl "http://localhost:5000/api/v1/transactions?cuenta_id={account_id}&tipo=gasto&page=1&limit=20"
```

Con rango de fechas:

```bash
curl "http://localhost:5000/api/v1/transactions?fecha_desde=2024-01-01&fecha_hasta=2024-01-31"
```

### Crear una transacción (Ingreso)

```bash
curl -X POST http://localhost:5000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "ingreso",
    "monto": 5000.00,
    "fecha": "2024-01-15",
    "cuenta_id": "{account_id}",
    "categoria_id": "{category_id}",
    "titulo": "Pago de salario",
    "descripcion": "Salario enero 2024",
    "tags": ["salario", "mensual"]
  }'
```

### Crear una transacción (Gasto)

```bash
curl -X POST http://localhost:5000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "gasto",
    "monto": 350.50,
    "fecha": "2024-01-16",
    "cuenta_id": "{account_id}",
    "categoria_id": "{category_id}",
    "titulo": "Compra supermercado",
    "descripcion": "Despensa semanal",
    "tags": ["comida", "necesario"]
  }'
```

### Obtener una transacción por ID

```bash
curl http://localhost:5000/api/v1/transactions/{transaction_id}
```

### Actualizar una transacción

```bash
curl -X PUT http://localhost:5000/api/v1/transactions/{transaction_id} \
  -H "Content-Type: application/json" \
  -d '{
    "monto": 375.00,
    "descripcion": "Despensa semanal (actualizado)"
  }'
```

### Eliminar una transacción

```bash
curl -X DELETE http://localhost:5000/api/v1/transactions/{transaction_id}
```

## Transferencias (Transfers)

### Listar transferencias

```bash
curl http://localhost:5000/api/v1/transfers
```

Con filtros:

```bash
curl "http://localhost:5000/api/v1/transfers?cuenta_id={account_id}&page=1&limit=20"
```

### Crear una transferencia

```bash
curl -X POST http://localhost:5000/api/v1/transfers \
  -H "Content-Type: application/json" \
  -d '{
    "cuenta_origen_id": "{source_account_id}",
    "cuenta_destino_id": "{destination_account_id}",
    "monto": 1000.00,
    "fecha": "2024-01-17",
    "descripcion": "Ahorro mensual",
    "tags": ["ahorro"]
  }'
```

### Obtener una transferencia por ID

```bash
curl http://localhost:5000/api/v1/transfers/{transfer_id}
```

### Actualizar una transferencia

```bash
curl -X PUT http://localhost:5000/api/v1/transfers/{transfer_id} \
  -H "Content-Type: application/json" \
  -d '{
    "monto": 1200.00,
    "descripcion": "Ahorro mensual aumentado"
  }'
```

### Eliminar una transferencia

```bash
curl -X DELETE http://localhost:5000/api/v1/transfers/{transfer_id}
```

## Dashboard

### Obtener dashboard completo

```bash
curl http://localhost:5000/api/v1/dashboard
```

Con mes/año específico:

```bash
curl "http://localhost:5000/api/v1/dashboard?mes=1&anio=2024"
```

### Obtener patrimonio neto

```bash
curl http://localhost:5000/api/v1/dashboard/net-worth
```

### Obtener resumen mensual

```bash
curl http://localhost:5000/api/v1/dashboard/summary
```

Con mes/año específico:

```bash
curl "http://localhost:5000/api/v1/dashboard/summary?mes=1&anio=2024"
```

### Obtener actividad reciente

```bash
curl http://localhost:5000/api/v1/dashboard/recent-activity
```

Con límite personalizado:

```bash
curl "http://localhost:5000/api/v1/dashboard/recent-activity?limit=20"
```

## Ejemplos con Python (requests)

```python
import requests
import json

BASE_URL = "http://localhost:5000/api/v1"

# Crear cuenta
account_data = {
    "nombre": "Tarjeta de Crédito",
    "tipo": "credito",
    "divisa": "MXN",
    "descripcion": "Visa Gold"
}

response = requests.post(f"{BASE_URL}/accounts", json=account_data)
account = response.json()["data"]
account_id = account["id"]

print(f"Cuenta creada: {account_id}")

# Obtener cuenta con balance
response = requests.get(f"{BASE_URL}/accounts/{account_id}")
account_with_balance = response.json()["data"]
print(f"Balance: {account_with_balance['balance']}")

# Listar transacciones con filtros
params = {
    "cuenta_id": account_id,
    "tipo": "gasto",
    "fecha_desde": "2024-01-01",
    "fecha_hasta": "2024-01-31",
    "page": 1,
    "limit": 20
}

response = requests.get(f"{BASE_URL}/transactions", params=params)
transactions = response.json()["data"]["items"]
print(f"Transacciones encontradas: {len(transactions)}")
```

## Respuestas del API

### Respuesta exitosa (200/201)

```json
{
  "success": true,
  "message": "Cuenta creada exitosamente",
  "data": {
    "id": "uuid-here",
    "nombre": "Cuenta de Ahorro",
    "tipo": "debito",
    "divisa": "MXN",
    "balance": "1500.00",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

### Respuesta paginada (200)

```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "total": 45,
      "page": 1,
      "page_size": 20,
      "total_pages": 3
    }
  }
}
```

### Error de validación (400)

```json
{
  "success": false,
  "message": "Error de validación",
  "errors": [
    {
      "loc": ["body", "monto"],
      "msg": "El monto debe ser mayor a 0",
      "type": "value_error"
    }
  ]
}
```

### Recurso no encontrado (404)

```json
{
  "success": false,
  "message": "Account con ID {id} no encontrado"
}
```

### Error de regla de negocio (422)

```json
{
  "success": false,
  "message": "No se pueden transferir fondos entre cuentas con diferentes divisas"
}
```
