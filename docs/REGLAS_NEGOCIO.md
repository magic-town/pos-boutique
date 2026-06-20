# Reglas de Negocio
## pos-boutique — Sistema de Gestión POS (Crédito Local)

> Este documento es la fuente de verdad del negocio.
> Cualquier decisión técnica debe ser consistente con lo aquí definido.
> Se versiona junto con el código — si una regla cambia, se registra en Git.

---

## Tabla de contenidos

- [Contexto](#contexto)
- [Enums del sistema](#enums-del-sistema)
- [Modelo de datos](#modelo-de-datos)
- [Módulos del sistema](#módulos-del-sistema)
- [Panel Principal](#panel-principal--registro-de-operaciones)
- [Ciclo de vida del cliente](#ciclo-de-vida-del-cliente)
- [Reglas de negocio](#reglas-de-negocio)
- [Stack tecnológico](#stack-tecnológico)
- [Despliegue](#despliegue)
- [Estado del proyecto](#estado-del-proyecto)

---

## Contexto

Micronegocio de tienda de ropa. El negocio opera actualmente con **lápiz y papel**, con inconsistencias derivadas del registro manual. El objetivo es digitalizar y consistir un proceso que ya funciona: registrar clientes, pedidos, proveedores y movimientos financieros.

El modelo de negocio está basado en **crédito local**. Se requiere una solución inmediata, sostenible y escalable.

---

## Enums del sistema

Los siguientes valores son los únicos válidos para sus respectivos campos.
Cualquier valor fuera de esta lista debe ser rechazado por el backend (Pydantic).

### `Operacion`

| Valor | Descripción |
|---|---|
| `contado` | Venta inmediata al momento de la compra. No genera saldo. |
| `apartado` | Reserva de producto con primer pago parcial. Genera saldo pendiente. |
| `abono` | Pago parcial al saldo existente de un cliente. Sin producto asociado. |
| `gasto` | Salida de dinero operativa (insumos, gastos). Sin cliente ni producto. |

### `FormaPago`

| Valor | Descripción |
|---|---|
| `efectivo` | Pago en efectivo |
| `transferencia` | Transferencia bancaria o SPEI |
| `tarjeta` | Pago con tarjeta (débito o crédito) |

---

## Modelo de datos

Las siguientes tablas conforman la base de datos. Se presentan con sus tipos de datos
SQLite exactos para que el modelo ORM (SQLAlchemy) y el esquema físico sean consistentes.

### Relaciones entre tablas

| Tabla | Rol | Relaciones |
|---|---|---|
| `clientes` | Tabla maestra de clientes registrados | — |
| `pedidos` | Pedidos de catálogo formal e informal | FK → `clientes` |
| `pedidos_shein` | Pedidos vía app Shein; flujo y caja separados | FK → `clientes` |
| `inventario` | Stock físico disponible en Piso de Venta | — |
| `movimientos` | Tabla central de operaciones de caja | FK → `clientes` (nullable), FK → `inventario` (nullable) |

### `clientes`

```sql
CREATE TABLE clientes (
    id_cliente      INTEGER PRIMARY KEY AUTOINCREMENT,
    no_cliente      TEXT    NOT NULL UNIQUE,   -- Formato: {Colonia}-{consecutivo}, ej. Carrillos-001
    nombre          TEXT    NOT NULL,
    colonia         TEXT    NOT NULL,
    telefono        TEXT    NOT NULL,
    ref_nombre      TEXT    NOT NULL,          -- Nombre completo del garante/referencia
    ref_colonia     TEXT    NOT NULL,          -- Colonia del garante/referencia
    ref_telefono    TEXT,                      -- Teléfono del garante (opcional)
    saldo           REAL    NOT NULL DEFAULT 0, -- Deuda activa del cliente. Positivo = debe.
    estatus         TEXT    NOT NULL DEFAULT 'activo', -- 'activo' | 'liquidado' | 'rehabilitar'
    fecha_registro  TEXT    NOT NULL           -- ISO 8601: YYYY-MM-DD
);
```

**Notas de campo:**
- `no_cliente` lo genera el sistema automáticamente al registrar: toma la colonia del cliente y el siguiente consecutivo disponible para esa colonia. La operadora no lo captura.
- `saldo` representa deuda activa. Valor positivo = el cliente debe ese monto. Cero = sin deuda.
- `estatus` sigue el ciclo de vida descrito en [§ Ciclo de vida del cliente](#ciclo-de-vida-del-cliente).
- `ref_telefono` acepta NULL — el teléfono del garante es opcional. `ref_nombre` y `ref_colonia` son obligatorios.

---

### `pedidos`

```sql
CREATE TABLE pedidos (
    id_pedido           INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente          INTEGER NOT NULL REFERENCES clientes(id_cliente),
    producto            TEXT    NOT NULL,   -- Texto libre; nombre del artículo principal
    id_producto_externo TEXT,               -- ID del proveedor si lo tiene (opcional)
    marca               TEXT,
    talla               TEXT,
    opcion_producto     TEXT,               -- Producto alternativo (si el principal no se consigue)
    opcion_marca        TEXT,               -- Marca del producto alternativo
    opcion_talla        TEXT,               -- Talla del producto alternativo
    fecha               TEXT    NOT NULL    -- ISO 8601: YYYY-MM-DD
);
```

**Notas de campo:**
- No existe catálogo de productos en el MVP. `producto` y `opcion_producto` son texto libre.
- Los campos `opcion_*` son el segundo producto que se entrega si el principal no se consigue. Tienen exactamente la misma estructura que el producto principal.
- Un `Pedido` genera registro en `movimientos` solo cuando el cliente acepta quedarse con el producto (concretación). Mientras está pendiente, vive solo en `pedidos`.

---

### `pedidos_shein`

```sql
CREATE TABLE pedidos_shein (
    id_pedido_shein INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente      INTEGER NOT NULL REFERENCES clientes(id_cliente),
    producto        TEXT    NOT NULL,   -- Descripción del artículo seleccionado en la app
    monto           REAL    NOT NULL,   -- Precio pagado al momento de confirmar la compra
    fecha           TEXT    NOT NULL    -- ISO 8601: YYYY-MM-DD
);
```

**Notas de campo:**
- El campo `bono_aplicado` que existía en el modelo ORM original ha sido **eliminado**. No corresponde a ninguna regla de negocio definida.
- El flujo Shein opera así: el cliente selecciona el artículo en la app de Shein, la tienda ejecuta la compra. El pago del cliente a la tienda es **siempre de contado** — Shein no genera saldo.
- Al concretarse la compra Shein, se genera un registro en `movimientos` con `operacion = 'contado'`. Esto registra el ingreso a caja de la tienda.
- El módulo Shein tiene su propia vista en el panel pero comparte la caja general a través de `movimientos`. No tiene base de datos separada en el MVP.

---

### `inventario`

```sql
CREATE TABLE inventario (
    id_producto     INTEGER PRIMARY KEY AUTOINCREMENT,
    descripcion     TEXT    NOT NULL,
    marca           TEXT,
    talla           TEXT,
    cantidad        INTEGER NOT NULL DEFAULT 0,
    precio          REAL    NOT NULL,
    fecha_registro  TEXT    NOT NULL   -- ISO 8601: YYYY-MM-DD
);
```

**Notas de campo:**
- En el MVP (v0.1), el Piso de Venta no está activo. La integración con el spreadsheet existente ocurre en **v0.2**.
- `cantidad` puede llegar a 0 pero no debe ser negativa. El backend debe rechazar una venta si `cantidad = 0`.

---

### `movimientos`

```sql
CREATE TABLE movimientos (
    id_movimiento    INTEGER PRIMARY KEY AUTOINCREMENT,
    operacion        TEXT    NOT NULL,   -- Enum: contado | apartado | abono | gasto
    id_cliente       INTEGER REFERENCES clientes(id_cliente),   -- NULL para 'gasto' y 'contado' sin cliente
    id_producto      INTEGER REFERENCES inventario(id_producto), -- NULL si no es venta de Piso de Venta
    monto            REAL    NOT NULL,
    forma_pago       TEXT    NOT NULL,   -- Enum: efectivo | transferencia | tarjeta
    saldo_resultante REAL,               -- NULL para 'contado' y 'gasto'. Saldo del cliente tras la operación.
    notas            TEXT,               -- Campo libre para observaciones (opcional)
    fecha            TEXT    NOT NULL    -- ISO 8601: YYYY-MM-DD
);
```

**Notas de campo:**
- `saldo_resultante` solo se registra cuando la operación modifica el saldo del cliente: `apartado` y `abono`. Para `contado` y `gasto` es NULL.
- Cuando se registra un `abono`: `saldo_resultante = clientes.saldo - monto`. El backend actualiza `clientes.saldo` en la misma transacción.
- Cuando se registra un `apartado`: `saldo_resultante = precio_producto - primer_pago`. El backend escribe ese valor en `clientes.saldo`.
- `id_producto` solo se vincula cuando el origen del artículo es Piso de Venta (tabla `inventario`). Para catálogo informal o Shein, es NULL.
- `notas` existe para casos excepcionales que la operadora necesite documentar. No es un campo visible en el flujo principal de la UI.

---

## Módulos del sistema

Cada módulo es una operación que **lee o escribe** en la base de datos.
Son accesibles desde el panel principal.

### 1. Agregar Cliente

> Escribe en: `clientes`

| Campo UI | Campo DB | Tipo | Requerido |
|---|---|---|---|
| Nombre | `nombre` | TEXT | ✅ |
| Colonia | `colonia` | TEXT | ✅ |
| Teléfono | `telefono` | TEXT | ✅ |
| Nombre del garante | `ref_nombre` | TEXT | ✅ |
| Colonia del garante | `ref_colonia` | TEXT | ✅ |
| Teléfono del garante | `ref_telefono` | TEXT | ❌ |
| No. cliente | `no_cliente` | TEXT | Autogenerado |

El campo `no_cliente` lo genera el sistema. La operadora no lo captura.
Formato: `{Colonia}-{consecutivo con ceros}` → `Carrillos-001`, `Carrillos-002`, `Centro-001`.

---

### 2. Pedido (Catálogo)

> Escribe en: `pedidos` → genera registro en `movimientos` al concretarse.

| Campo UI | Campo DB | Tipo | Requerido |
|---|---|---|---|
| Cliente | `id_cliente` | INTEGER (FK) | ✅ |
| Producto | `producto` | TEXT | ✅ |
| ID proveedor | `id_producto_externo` | TEXT | ❌ |
| Marca | `marca` | TEXT | ❌ |
| Talla | `talla` | TEXT | ❌ |
| Opción — Producto | `opcion_producto` | TEXT | ❌ |
| Opción — Marca | `opcion_marca` | TEXT | ❌ |
| Opción — Talla | `opcion_talla` | TEXT | ❌ |

La "Opción" es un segundo artículo que la tienda entrega si el producto principal no está disponible. No es una variante del mismo artículo — es un producto alternativo completo. Los campos `opcion_*` son opcionales en el registro pero deben llenarse juntos si se usan.

---

### 3. Shein (Proveedor especial)

> Escribe en: `pedidos_shein` → genera registro en `movimientos` al concretarse.

| Campo UI | Campo DB | Tipo | Requerido |
|---|---|---|---|
| Cliente | `id_cliente` | INTEGER (FK) | ✅ |
| Producto | `producto` | TEXT | ✅ |
| Monto | `monto` | REAL | ✅ |

El pago es siempre de **contado**. No genera saldo al cliente.
Al concretarse, se registra en `movimientos` con `operacion = 'contado'` e `id_cliente` vinculado.
El ingreso queda reflejado en caja como cualquier otro contado.

---

### 4. Piso de Venta

> Lee y escribe en: `inventario` → genera registro en `movimientos` al vender.

**Estado en MVP (v0.1):** No activo. El módulo existe en la UI como placeholder.
La integración con el spreadsheet de inventario existente ocurre en **v0.2**.

Funcionalidad planeada para v0.2:
- Buscar y seleccionar producto en `inventario`
- Registrar venta (descuenta `cantidad` en `inventario`, escribe en `movimientos`)
- El backend rechaza la venta si `cantidad = 0`

---

### 5. Consulta

> Lee de: `clientes` + `movimientos`

Vista de solo lectura, filtrada por cliente. Muestra:
- Datos del cliente (nombre, colonia, teléfono, `no_cliente`, estatus)
- Saldo actual (`clientes.saldo`)
- Historial de movimientos asociados (ordenado por fecha descendente)

---

## Panel Principal — Registro de Operaciones

> Escribe en: `movimientos`

> ⚠️ Los módulos **Pedido** y **Shein** tienen su propia vista y no se operan desde aquí.

### Paso 1 — Seleccionar operación

| Operación | Descripción |
|---|---|
| **Contado** | Venta inmediata. Sin saldo. Cliente opcional. |
| **Apartado** | Primer pago + reserva de producto. Abre modal. Genera saldo en el cliente. |
| **Abono** | Pago parcial al saldo existente del cliente. Sin producto. |
| **Gasto** | Salida de dinero (insumos, gastos operativos). Sin cliente. |

**Nota sobre Crédito:** no es una operación independiente. El saldo a crédito se genera automáticamente cuando un `Apartado` se convierte en deuda activa. Todo cliente que tenga `saldo > 0` tiene crédito activo. El estado se gestiona a través del ciclo de vida del cliente (ver sección siguiente).

### Paso 2 — Origen del producto

Solo aplica para **Contado** y **Apartado**:

- **Catálogo informal:** texto libre. No vincula `id_producto`.
- **Piso de Venta:** busca en `inventario`. Vincula `id_producto`. (Disponible en v0.2.)

### Paso 3 — Campos activos por operación

| Operación | Cliente | Producto | Monto | Forma de pago | `saldo_resultante` |
|---|---|---|---|---|---|
| Contado | Opcional | ✅ | ✅ | ✅ | NULL |
| Apartado | Obligatorio | ✅ | ✅ (1er pago) | ✅ | ✅ (precio − 1er pago) |
| Abono | Obligatorio | ❌ | ✅ | ✅ | ✅ (saldo anterior − monto) |
| Gasto | ❌ | ❌ | ✅ | ✅ | NULL |

### Modal de Apartado

Ventana emergente con:
- Cliente y producto seleccionados
- Monto del primer pago y fecha
- Saldo pendiente calculado (precio − primer pago)
- Historial de abonos previos del cliente (si los hay)

---

## Ciclo de vida del cliente

El campo `estatus` en `clientes` refleja el estado operativo del cliente en cualquier momento.

```
[Registro] ──▶ activo ──▶ liquidado ──▶ rehabilitar ──▶ activo
                │                              ▲
                │                              │
                └──── saldo llega a 0 ─────────┘
```

| Estatus | Condición | Acción del sistema |
|---|---|---|
| `activo` | Cliente con saldo > 0 o sin deuda pero en operación regular | Operación normal |
| `liquidado` | `saldo = 0` después de un abono que cierra la deuda | El sistema lanza bandera: cliente debe ser **rehabilitado** antes de operar de nuevo |
| `rehabilitar` | Operadora revisó el historial y reactivó al cliente | Regresa a `activo` manualmente desde `Consulta` |

**Regla clave:** Un cliente con `estatus = liquidado` no desaparece de la base de datos. Permanece en `clientes` con su historial completo. La rehabilitación es un paso manual que la operadora ejecuta desde la vista de `Consulta`.

El calendario de pagos (frecuencia esperada de abonos por cliente) es una funcionalidad planeada para versiones futuras. La base para implementarlo ya existe: `clientes.saldo` + historial en `movimientos`.

---

## Reglas de negocio

1. **Digitalización, no reinvención.** El sistema digitaliza un proceso existente. Prioridad: consistencia y simplicidad.
2. **Referencia geográfica:** colonia + teléfono. Sin calle ni número.
3. **Referencia del cliente (garante):** tres campos separados — `ref_nombre` (obligatorio), `ref_colonia` (obligatorio), `ref_telefono` (opcional).
4. **`no_cliente` autogenerado:** el sistema lo genera con formato `{Colonia}-{consecutivo}`. La operadora no lo captura manualmente.
5. **Saldo global:** los abonos aplican al saldo total del cliente, no a productos individuales.
6. **Saldo = deuda:** `clientes.saldo` es siempre positivo o cero. Positivo significa que el cliente debe ese monto. Nunca es negativo.
7. **`saldo_resultante` en movimientos:** solo se registra en `apartado` y `abono`. Es NULL para `contado` y `gasto`.
8. **Shein no genera saldo:** los pedidos Shein se pagan siempre de contado. El ingreso se registra en `movimientos` como `contado`.
9. **Inventario externo:** Piso de Venta se integra con spreadsheet existente en v0.2. No activo en MVP.
10. **Sin catálogo formal en MVP:** los campos `producto` y `opcion_producto` son texto libre. Una tabla `productos` es objetivo de versiones futuras.
11. **Opción en Pedidos:** es un segundo artículo alternativo completo (`opcion_producto`, `opcion_marca`, `opcion_talla`), no una variante del producto principal.
12. **Inventario con cantidad 0:** el backend rechaza cualquier venta de Piso de Venta si `inventario.cantidad = 0`.
13. **Cliente liquidado no se elimina:** `estatus = liquidado` es una bandera operativa. El registro permanece y debe ser rehabilitado para volver a operar.
14. **Operaciones no contempladas** (devoluciones, préstamos de exhibición, etc.) se incorporan a partir de **v0.3**.

---

## Stack tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Frontend | React + Vite | Ligero, ampliamente documentado, ideal para formularios y tablas |
| Backend | FastAPI (Python) | Simple, moderno, genera docs de API automáticamente |
| Base de datos | SQLite | Sin servidor, archivo `.db` respaldable con copiar y pegar |
| Despliegue | Local en PC ejecutiva | Sin dependencia de internet ni infraestructura externa |
| Actualizaciones | Git pull desde GitHub | Push desde desarrollo, pull en producción |

Escalable: migración futura a PostgreSQL + hosting en nube sin cambios de arquitectura.

---

## Despliegue

- **Desarrollo y pruebas:** máquina del desarrollador (`actuary`)
- **Producción:** PC de la ejecutiva en tienda, sin dependencia de internet

```
Desarrollador  →  git push → GitHub → git pull  →  PC ejecutiva
```

Mantenimiento remoto vía SSH desde máquina del desarrollador.
Requisitos en PC ejecutiva: Python 3.11+ y Node.js 20+ (instalación única).

---

## Estado del proyecto

| Ítem | Estado |
|---|---|
| Repositorio `pos-boutique` | ✅ Creado |
| `.gitignore` | ✅ Configurado (template Node + Python) |
| Estructura de carpetas | ✅ Commiteada |
| `README.md` | ✅ |
| `docs/ARQUITECTURA.md` | ✅ |
| `docs/REGLAS_NEGOCIO.md` | ✅ |
| `backend/requirements.txt` | ✅ |
| `backend/venv` | ✅ (no commiteado) |
| Esquema de base de datos (`models.py` + `pos.db`) | ✅ Modelos ORM creados, tablas generadas |
| Schemas Pydantic | 🔲 Pendiente |
| Endpoints API REST | 🔲 Pendiente |
| Servicios (lógica de negocio) | 🔲 Pendiente |
| Configuración centralizada (`core/`) | 🔲 Pendiente |
| CORS middleware | 🔲 Pendiente |
| Alembic (migraciones) | 🔲 Pendiente |
| Interfaz base (React + Vite) | 🔲 Pendiente |
