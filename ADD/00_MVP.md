# Wallet - MVP Specification

## 1. Descripcion General del Proyecto

**Wallet** es una aplicacion de seguimiento y analisis de gastos para finanzas personales. Permite a los usuarios registrar sus transacciones financieras, gestionar multiples cuentas y obtener una vision clara de su situacion financiera.

### Vision

Proporcionar una herramienta simple pero potente para que los usuarios tomen control de sus finanzas personales mediante el registro y categorizacion de sus movimientos financieros.

### Principios de Diseno

- **Simplicidad**: El registro de transacciones debe ser rapido y sin friccion
- **Precision**: El modelo de datos debe reflejar la realidad financiera del usuario
- **Flexibilidad**: Soporte para multiples cuentas, divisas y categorias personalizables
- **Integridad**: Los balances deben ser siempre consistentes y calculados, no almacenados

---

## 2. Objetivos del MVP

### Objetivo Principal

Crear una aplicacion funcional que permita llevar un registro completo de gastos e ingresos personales con soporte para multiples cuentas.

### Objetivos Especificos

1. Gestionar multiples cuentas financieras (debito, credito, efectivo)
2. Registrar transacciones (ingresos y gastos) categorizadas
3. Realizar transferencias entre cuentas propias
4. Visualizar balances por cuenta y patrimonio neto total
5. Categorizar transacciones de forma flexible

### Fuera del Alcance del MVP

- Transacciones recurrentes (suscripciones, salario automatico)
- Presupuestos y alertas
- Reportes graficos y analiticas avanzadas
- Exportacion de datos (CSV, PDF)
- Multi-usuario / cuentas compartidas
- Sincronizacion con bancos
- Metas de ahorro

---

## 3. Modelo de Datos

### 3.1 Diagrama de Entidades

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│   CUENTA    │       │   TRANSACCION   │       │  CATEGORIA  │
├─────────────┤       ├─────────────────┤       ├─────────────┤
│ id          │◄──────│ cuenta_id       │       │ id          │
│ nombre      │       │ categoria_id    │──────►│ nombre      │
│ tipo        │       │ tipo            │       │ tipo        │
│ divisa      │       │ monto           │       │ icono       │
│ descripcion │       │ fecha           │       │ color       │
│ tags        │       │ titulo          │       │ padre_id    │──┐
│ activa      │       │ descripcion     │       └─────────────┘  │
│             │       │ tags            │             ▲          │
└─────────────┘       └─────────────────┘             └──────────┘
       ▲
       │
       ├──────────────────┐
       │                  │
┌──────┴──────┐    ┌──────┴──────┐
│   origen    │    │   destino   │
├─────────────┴────┴─────────────┤
│         TRANSFERENCIA          │
├────────────────────────────────┤
│ id                             │
│ cuenta_origen_id               │
│ cuenta_destino_id              │
│ monto                          │
│ fecha                          │
│ descripcion                    │
│ tags                           │
└────────────────────────────────┘
```

### 3.2 Entidad: CUENTA

Representa una cuenta financiera del usuario (cuenta bancaria, tarjeta de credito, efectivo en cartera, etc.).

| Campo | Tipo | Requerido | Default | Descripcion |
|-------|------|-----------|---------|-------------|
| id | UUID | Si | Auto | Identificador unico |
| nombre | String | Si | - | Nombre descriptivo de la cuenta |
| tipo | Enum | Si | - | `debito`, `credito`, `efectivo` |
| divisa | String | Si | - | Codigo ISO 4217 (MXN, USD, EUR) |
| descripcion | String | No | null | Descripcion opcional |
| tags | String[] | No | [] | Etiquetas para agrupacion |
| activa | Boolean | Si | true | Si la cuenta esta activa |
| created_at | Timestamp | Si | Auto | Fecha de creacion |
| updated_at | Timestamp | Si | Auto | Fecha de ultima modificacion |

**Notas:**
- El balance de toda cuenta inicia en 0 y se calcula a partir de sus transacciones y transferencias
- El campo `tags` permite asociar cuentas relacionadas (ej: todas las del "Banco BC")
- El campo `activa` permite archivar cuentas sin perder el historial
- El balance actual se calcula dinamicamente, nunca se almacena directamente

### 3.3 Entidad: CATEGORIA

Representa una categoria para clasificar transacciones.

| Campo | Tipo | Requerido | Default | Descripcion |
|-------|------|-----------|---------|-------------|
| id | UUID | Si | Auto | Identificador unico |
| nombre | String | Si | - | Nombre de la categoria |
| tipo | Enum | Si | - | `ingreso`, `gasto`, `ambos` |
| icono | String | No | null | Identificador de icono |
| color | String | No | null | Color en formato hexadecimal |
| categoria_padre_id | UUID | No | null | Referencia a categoria padre |
| created_at | Timestamp | Si | Auto | Fecha de creacion |
| updated_at | Timestamp | Si | Auto | Fecha de ultima modificacion |

**Notas:**
- El campo `tipo` restringe en que tipo de transacciones puede usarse
- `categoria_padre_id` permite crear subcategorias (ej: Transporte > Gasolina, Uber)

### 3.4 Entidad: TRANSACCION

Representa un ingreso o gasto real (dinero que entra o sale del ecosistema financiero del usuario).

| Campo | Tipo | Requerido | Default | Descripcion |
|-------|------|-----------|---------|-------------|
| id | UUID | Si | Auto | Identificador unico |
| tipo | Enum | Si | - | `ingreso`, `gasto` |
| monto | Decimal | Si | - | Cantidad de dinero (siempre positivo) |
| fecha | Date | Si | - | Fecha de la transaccion |
| cuenta_id | UUID | Si | - | Referencia a la cuenta |
| categoria_id | UUID | Si | - | Referencia a la categoria |
| titulo | String | No | null | Titulo breve |
| descripcion | String | No | null | Descripcion detallada |
| tags | String[] | No | [] | Etiquetas adicionales |
| created_at | Timestamp | Si | Auto | Fecha de creacion |
| updated_at | Timestamp | Si | Auto | Fecha de ultima modificacion |

**Notas:**
- El monto siempre se almacena como valor positivo
- El `tipo` determina si suma o resta al balance
- La divisa se hereda de la cuenta asociada

### 3.5 Entidad: TRANSFERENCIA

Representa un movimiento de dinero entre cuentas propias del usuario. No afecta el patrimonio neto total.

| Campo | Tipo | Requerido | Default | Descripcion |
|-------|------|-----------|---------|-------------|
| id | UUID | Si | Auto | Identificador unico |
| cuenta_origen_id | UUID | Si | - | Cuenta de donde sale el dinero |
| cuenta_destino_id | UUID | Si | - | Cuenta a donde llega el dinero |
| monto | Decimal | Si | - | Cantidad transferida (positivo) |
| fecha | Date | Si | - | Fecha de la transferencia |
| descripcion | String | No | null | Descripcion opcional |
| tags | String[] | No | [] | Etiquetas para identificar transferencias |
| created_at | Timestamp | Si | Auto | Fecha de creacion |
| updated_at | Timestamp | Si | Auto | Fecha de ultima modificacion |

**Notas:**
- No tiene categoria (no es ingreso ni gasto real)
- Ambas cuentas deben tener la misma divisa (restriccion MVP)
- cuenta_origen_id != cuenta_destino_id (validacion requerida)
- El campo `tags` permite identificar tipos de transferencias (ej: "pago tarjeta", "fondo inversion")

---

## 4. Features del MVP

### Orden de Implementacion Sugerido

#### Fase 1: Fundamentos

| # | Feature | Descripcion | Prioridad |
|---|---------|-------------|-----------|
| 1.1 | CRUD Cuentas | Crear, leer, actualizar y archivar cuentas | Critica |
| 1.2 | CRUD Categorias | Gestionar categorias y subcategorias | Critica |
| 1.3 | Categorias predefinidas | Seed de categorias comunes | Alta |

#### Fase 2: Core

| # | Feature | Descripcion | Prioridad |
|---|---------|-------------|-----------|
| 2.1 | CRUD Transacciones | Registrar ingresos y gastos | Critica |
| 2.2 | Calculo de balance | Balance por cuenta | Critica |
| 2.3 | Lista de transacciones | Visualizar transacciones con filtros basicos | Critica |

#### Fase 3: Transferencias

| # | Feature | Descripcion | Prioridad |
|---|---------|-------------|-----------|
| 3.1 | CRUD Transferencias | Mover dinero entre cuentas | Alta |
| 3.2 | Balance con transferencias | Incluir transferencias en calculo | Alta |

#### Fase 4: Vistas Consolidadas

| # | Feature | Descripcion | Prioridad |
|---|---------|-------------|-----------|
| 4.1 | Dashboard | Vista resumen con patrimonio neto | Alta |
| 4.2 | Vista por cuenta | Detalle y movimientos de una cuenta | Alta |
| 4.3 | Filtros avanzados | Por fecha, categoria, cuenta, tags | Media |

---

## 5. Reglas de Negocio

### 5.1 Calculo de Balance

El balance de una cuenta se calcula dinamicamente con la siguiente formula:

```
Balance = SUM(transacciones WHERE tipo = 'ingreso')
        - SUM(transacciones WHERE tipo = 'gasto')
        + SUM(transferencias WHERE cuenta_destino_id = cuenta.id)
        - SUM(transferencias WHERE cuenta_origen_id = cuenta.id)
```

**Nota:** Toda cuenta inicia con balance 0. El balance inicial real se establece registrando una transaccion de tipo ingreso (ej: "Balance inicial" o "Ajuste inicial").

**Patrimonio neto total:**

```
Patrimonio = SUM(balance de todas las cuentas activas)
```

### 5.2 Comportamiento por Tipo de Cuenta

| Tipo | Balance Positivo | Balance Negativo | Uso Tipico |
|------|------------------|------------------|------------|
| debito | Dinero disponible | Sobregiro (advertencia) | Cuenta de ahorros, corriente |
| credito | Saldo a favor | Deuda pendiente | Tarjeta de credito |
| efectivo | Dinero en mano | Error (advertencia) | Cartera, caja chica |

### 5.3 Transacciones vs Transferencias

| Aspecto | Transaccion | Transferencia |
|---------|-------------|---------------|
| Cuentas involucradas | Una | Dos |
| Categoria | Requerida | No aplica |
| Efecto en patrimonio | Si (aumenta o disminuye) | No (suma cero) |
| Ejemplo | Pagar supermercado | Pagar tarjeta de credito |

### 5.4 Categorias y Tipos de Transaccion

- Una categoria tipo `ingreso` solo puede usarse en transacciones tipo `ingreso`
- Una categoria tipo `gasto` solo puede usarse en transacciones tipo `gasto`
- Una categoria tipo `ambos` puede usarse en cualquier transaccion

---

## 6. Casos de Uso Principales

### CU-01: Registrar un Gasto

**Actor:** Usuario
**Precondicion:** Existe al menos una cuenta y una categoria tipo gasto

**Flujo:**
1. Usuario selecciona "Nuevo gasto"
2. Sistema muestra formulario
3. Usuario ingresa: monto, fecha, cuenta, categoria
4. Usuario opcionalmente agrega: titulo, descripcion, tags
5. Sistema valida datos
6. Sistema guarda transaccion
7. Sistema actualiza balance de la cuenta

### CU-02: Registrar un Ingreso

**Actor:** Usuario
**Precondicion:** Existe al menos una cuenta y una categoria tipo ingreso

**Flujo:**
1. Usuario selecciona "Nuevo ingreso"
2. Sistema muestra formulario
3. Usuario ingresa: monto, fecha, cuenta, categoria
4. Usuario opcionalmente agrega: titulo, descripcion, tags
5. Sistema valida datos
6. Sistema guarda transaccion
7. Sistema actualiza balance de la cuenta

### CU-03: Transferir entre Cuentas

**Actor:** Usuario
**Precondicion:** Existen al menos dos cuentas con la misma divisa

**Flujo:**
1. Usuario selecciona "Nueva transferencia"
2. Sistema muestra formulario
3. Usuario selecciona cuenta origen y cuenta destino
4. Usuario ingresa monto y fecha
5. Sistema valida que sean cuentas diferentes y misma divisa
6. Sistema guarda transferencia
7. Sistema actualiza balance de ambas cuentas

### CU-04: Consultar Balance

**Actor:** Usuario
**Precondicion:** Existe al menos una cuenta

**Flujo:**
1. Usuario accede al dashboard
2. Sistema calcula balance de cada cuenta
3. Sistema calcula patrimonio neto total
4. Sistema muestra resumen con balances

### CU-05: Crear Nueva Cuenta

**Actor:** Usuario

**Flujo:**
1. Usuario selecciona "Nueva cuenta"
2. Sistema muestra formulario
3. Usuario ingresa: nombre, tipo, divisa
4. Usuario opcionalmente agrega: descripcion, tags
5. Sistema valida datos
6. Sistema guarda cuenta (balance inicial = 0)
7. Cuenta aparece en lista de cuentas
8. Si la cuenta tiene saldo existente, usuario registra transaccion de tipo ingreso como "Ajuste inicial"

### CU-06: Archivar Cuenta

**Actor:** Usuario
**Precondicion:** Existe una cuenta activa

**Flujo:**
1. Usuario selecciona cuenta a archivar
2. Sistema solicita confirmacion
3. Usuario confirma
4. Sistema marca cuenta como inactiva (activa = false)
5. Cuenta desaparece de vistas principales pero se conserva historial

---

## 7. Consideraciones Tecnicas

### 7.1 Almacenamiento de Montos

- Usar tipo `Decimal` con precision adecuada (ej: DECIMAL(15,2))
- Nunca usar `Float` para dinero (errores de precision)
- Almacenar siempre como valor positivo
- El tipo de transaccion determina la operacion (+/-)

### 7.2 Manejo de Fechas

- Almacenar fechas en UTC
- Mostrar en zona horaria local del usuario
- Formato de almacenamiento: ISO 8601

### 7.3 Divisas

- Almacenar codigo ISO 4217 (3 caracteres)
- MVP: No soportar conversion entre divisas
- MVP: Transferencias solo entre cuentas de misma divisa

### 7.4 IDs

- Usar UUIDs para identificadores
- Evita problemas de colision y exposicion de secuencias

### 7.5 Soft Delete

- Cuentas: Usar campo `activa` en lugar de borrar
- Categorias: Considerar soft delete si tiene transacciones asociadas
- Transacciones/Transferencias: Permitir borrado fisico (con confirmacion)

### 7.6 Indices Sugeridos

```
CUENTA:
  - id (PK)
  - activa (para filtrar cuentas activas)

CATEGORIA:
  - id (PK)
  - tipo (para filtrar por tipo)
  - categoria_padre_id (para consultar subcategorias)

TRANSACCION:
  - id (PK)
  - cuenta_id (FK, para calcular balance)
  - fecha (para ordenar y filtrar)
  - categoria_id (FK, para reportes)
  - (cuenta_id, fecha) compuesto

TRANSFERENCIA:
  - id (PK)
  - cuenta_origen_id (FK)
  - cuenta_destino_id (FK)
  - fecha (para ordenar)
```

---

## 8. Restricciones y Validaciones

### 8.1 Cuenta

| Campo | Validacion |
|-------|------------|
| nombre | No vacio, max 100 caracteres |
| tipo | Debe ser: `debito`, `credito`, `efectivo` |
| divisa | Codigo ISO 4217 valido (3 caracteres) |

### 8.2 Categoria

| Campo | Validacion |
|-------|------------|
| nombre | No vacio, max 50 caracteres |
| tipo | Debe ser: `ingreso`, `gasto`, `ambos` |
| color | Formato hexadecimal valido si se proporciona |
| categoria_padre_id | Debe existir y no crear ciclos |

### 8.3 Transaccion

| Campo | Validacion |
|-------|------------|
| tipo | Debe ser: `ingreso`, `gasto` |
| monto | Mayor que 0 |
| fecha | Fecha valida, no futura (opcional) |
| cuenta_id | Debe existir y estar activa |
| categoria_id | Debe existir y ser compatible con tipo |

### 8.4 Transferencia

| Campo | Validacion |
|-------|------------|
| monto | Mayor que 0 |
| fecha | Fecha valida |
| cuenta_origen_id | Debe existir y estar activa |
| cuenta_destino_id | Debe existir y estar activa |
| cuenta_origen_id != cuenta_destino_id | No puede transferir a si misma |
| Misma divisa | Ambas cuentas deben tener la misma divisa |

---

## 9. Categorias Predefinidas Sugeridas

### Ingresos

- Salario
- Freelance / Trabajo independiente
- Inversiones
- Reembolsos
- Regalos recibidos
- Otros ingresos

### Gastos

- Alimentacion
  - Supermercado
  - Restaurantes
  - Delivery
- Transporte
  - Gasolina
  - Transporte publico
  - Taxi / Uber
  - Estacionamiento
- Hogar
  - Renta / Hipoteca
  - Servicios (luz, agua, gas)
  - Internet / Telefono
  - Mantenimiento
- Entretenimiento
  - Streaming
  - Cine / Eventos
  - Videojuegos
- Salud
  - Medicos
  - Farmacia
  - Gimnasio
- Educacion
- Ropa y accesorios
- Regalos
- Impuestos
  - Fees de transferencia
- Otros gastos

---

## 10. Glosario

| Termino | Definicion |
|---------|------------|
| Balance | Cantidad de dinero disponible (o deuda) en una cuenta, calculado a partir de transacciones y transferencias |
| Patrimonio neto | Suma de balances de todas las cuentas activas |
| Transaccion | Movimiento de dinero que entra o sale del ecosistema del usuario |
| Transferencia | Movimiento de dinero entre cuentas propias (no afecta patrimonio) |
| Categoria | Clasificacion que describe el proposito de una transaccion |
| Tag | Etiqueta flexible para agrupar o filtrar elementos |

---

## 11. Proximos Pasos Post-MVP

Una vez completado el MVP, las siguientes funcionalidades estan priorizadas para desarrollo futuro:

1. **Transacciones recurrentes** - Automatizar registro de gastos/ingresos periodicos
2. **Presupuestos** - Establecer limites por categoria
3. **Reportes y graficos** - Visualizacion de tendencias y distribucion de gastos
4. **Alertas** - Notificaciones de limites alcanzados
5. **Exportacion** - CSV y PDF de datos
6. **Multi-divisa** - Soporte para transferencias entre divisas con tipo de cambio
7. **Metas de ahorro** - Objetivos financieros con seguimiento
8. **Multi-usuario** - Cuentas compartidas y permisos

---

*Documento generado: Enero 2026*
*Version: 1.1 - MVP*
