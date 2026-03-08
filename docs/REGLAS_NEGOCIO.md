# Reglas de Negocio
## pos-boutique — Sistema de Gestión POS (Crédito Local)

> Este documento es la fuente de verdad del negocio.
> Cualquier decisión técnica debe ser consistente con lo aquí definido.
> Se versiona junto con el código — si una regla cambia, se registra en Git.

---

## Tabla de contenidos

- [Contexto](#contexto)
- [Modelo de datos](#modelo-de-datos)
- [Módulos del sistema](#módulos-del-sistema)
- [Panel Principal](#panel-principal--registro-de-operaciones)
- [Reglas de negocio](#reglas-de-negocio)
- [Stack tecnológico](#stack-tecnológico)
- [Despliegue](#despliegue)
- [Estado del proyecto](#estado-del-proyecto)

---

## Contexto

Tienda de ropa en pueblo pequeño. El negocio opera actualmente con **lápiz y papel**,
con inconsistencias derivadas del registro manual. El objetivo es digitalizar y
consistir un proceso que ya funciona: registrar clientes, pedidos, proveedores y
movimientos financieros.

El modelo de negocio está basado en **crédito local**. Se requiere una solución
inmediata, sostenible y escalable.

---

## Modelo de datos

Las siguientes tablas conforman la base de datos. Están relacionadas entre sí
mediante claves foráneas `(FK)`, lo que garantiza integridad y trazabilidad
de cada operación.

| Tabla | Rol | Relaciones |
|---|---|---|
| `Clientes` | Tabla maestra de clientes registrados | — |
| `Pedidos` | Pedidos de catálogo formal e informal | FK → Clientes |
| `Pedidos_Shein` | Pedidos vía app Shein; cuenta separada | FK → Clientes |
| `Inventario` | Stock físico (Piso de Venta) | — |
| `Movimientos` | Tabla central de operaciones de caja | FK → Clientes (opcional), FK → Inventario (opcional) |

### Relaciones clave

- Todo movimiento queda registrado en `Movimientos`.
- Si el movimiento involucra un cliente, se vincula a `Clientes`.
- Si el movimiento involucra un producto de Piso de Venta, se vincula a `Inventario` y descuenta el stock.
- `Pedidos` y `Pedidos_Shein` son flujos independientes que generan un registro en `Movimientos` al concretarse.

---

## Módulos del sistema

Cada módulo es una operación que **lee o escribe** en la base de datos.
Son accesibles desde botones en el panel principal.

### 1. Agregar Cliente

> Escribe en: `Clientes`

| Campo | Descripción |
|---|---|
| Nombre | Nombre completo |
| Colonia | Referencia geográfica principal. Calle y número no son relevantes. |
| Teléfono | Contacto directo |
| Referencia | Nombre, colonia y teléfono de una persona conocida del cliente |
| No_cliente | ID autoincremental con prefijo de colonia (ej. `JAR-001`). Reemplaza asignación manual. |

### 2. Pedido (Catálogo)

> Escribe en: `Pedidos` → genera registro en `Movimientos` al concretarse

Aplica a proveedores formales e informales. No existe base de productos en el MVP;
el campo Producto es **texto libre** con ID opcional para versiones futuras.

| Campo | Descripción |
|---|---|
| Cliente | Vinculado a `Clientes` |
| Producto / ID | Texto libre; ID opcional si el proveedor lo tiene |
| Marca | — |
| Talla | — |
| Opción | Alternativa al producto principal (mismos campos: Marca, Talla, Opción) |

### 3. Shein (Proveedor especial)

> Escribe en: `Pedidos_Shein` → genera registro en `Movimientos` al concretarse

Cuenta y flujo **separados** del negocio general.

- El cliente selecciona el producto desde la app de Shein.
- La tienda ejecuta la compra directamente en la app.
- La ganancia proviene de **bonos de descuento por volumen** de pedidos.

### 4. Piso de Venta

> Lee y escribe en: `Inventario` → genera registro en `Movimientos` al vender

Stock físico, mayormente artículos únicos. La integración con el spreadsheet
externo actual es un objetivo de **v0.2**.

Funcionalidad MVP:
- Buscar y seleccionar producto en stock
- Registrar venta (descuenta `Inventario`, escribe en `Movimientos`)

### 5. Consulta

> Lee de: `Clientes` + `Movimientos`

Vista tipo tabla, solo lectura, filtrada por cliente. Muestra:
- Historial de compras y pagos
- Saldo actual

---

## Panel Principal — Registro de Operaciones

> Escribe en: `Movimientos`

> ⚠️ Los módulos **Pedido** y **Shein** son independientes y no se operan desde aquí.

### Paso 1 — Seleccionar operación

| Operación | Descripción |
|---|---|
| **Contado** | Venta inmediata. Sin saldo. Cliente opcional. |
| **Apartado** | Primer pago + reserva de producto. Abre modal. Genera saldo. |
| **Abono** | Pago parcial al saldo existente del cliente. Sin producto. |
| **Gasto** | Salida de dinero (insumos, gastos operativos). Sin cliente. |

> **Nota sobre Crédito:** no es una operación independiente. El saldo a crédito
> se genera automáticamente cuando un Pedido o un Apartado se convierte en deuda
> activa. El cambio de estatus del cliente (`Apartado → Crédito`) se gestiona
> desde su historial en **Consulta**.

### Paso 2 — Origen del producto

Solo aplica para **Contado** y **Apartado**:

- Catálogo informal (texto libre)
- Piso de Venta (busca en `Inventario`)

### Paso 3 — Campos activos por operación

| Operación | Cliente | Producto | Monto | Forma de pago | Saldo |
|---|---|---|---|---|---|
| Contado | Opcional | ✅ | ✅ | ✅ | ❌ |
| Apartado | Obligatorio | ✅ | ✅ (1er pago) | ✅ | ✅ |
| Abono | Obligatorio | ❌ | ✅ | ✅ | ✅ |
| Gasto | ❌ | ❌ | ✅ | ✅ | ❌ |

### Modal de Apartado

Ventana emergente con:
- Cliente y Producto
- Primer pago y fecha
- Saldo pendiente
- Historial de pagos del apartado

---

## Reglas de negocio

1. **Digitalización, no reinvención.** El sistema digitaliza un proceso existente. Prioridad: consistencia y simplicidad.
2. **Referencia geográfica:** Colonia + Teléfono. Sin calle ni número.
3. **Saldo global:** los abonos aplican al saldo total del cliente, no a productos individuales.
4. **Saldo acotado:** el campo Saldo solo aplica en operaciones vinculadas a cliente — `Apartado` y `Abono`.
5. **Inventario externo:** Piso de Venta se integra con spreadsheet externo en v0.2.
6. **Shein separado:** sus movimientos no mezclan con la caja general del negocio.
7. **Sin catálogo formal en MVP:** el campo Producto es texto libre con ID opcional. Una tabla `Productos` es objetivo de versiones futuras.
8. **Operaciones no contempladas** (devoluciones, préstamos de exhibición, etc.) se incorporan a partir de **v0.3** una vez que el sistema base esté estable.

---

## Stack tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Frontend | React + Vite | Ligero, ampliamente documentado, ideal para formularios y tablas |
| Backend | FastAPI (Python) | Simple, moderno, genera docs de API automáticamente |
| Base de datos | SQLite | Sin servidor, archivo `.db` respaldable con copiar y pegar |
| Despliegue | Local en PC ejecutiva | Sin dependencia de internet ni infraestructura externa |
| Actualizaciones | Git pull desde GitHub | Push desde desarrollo, pull en producción |

Escalable: migración futura a PostgreSQL + hosting en nube **sin cambios de arquitectura**.

---

## Despliegue

- **Desarrollo y pruebas:** máquina del desarrollador (`actuary`)
- **Producción:** PC de la ejecutiva en tienda, sin dependencia de internet

```
Desarrollador  →  git push → GitHub → git pull  →  PC ejecutiva
```

Mantenimiento remoto vía SSH desde máquina del desarrollador.
Requisitos en PC ejecutiva: Python y Node.js (instalación única).

---

## Estado del proyecto

| Ítem | Estado |
|---|---|
| Repositorio `pos-boutique` | ✅ Creado |
| `.gitignore` | ✅ Configurado (template Node + venv) |
| Estructura de carpetas | ✅ Commiteada |
| `README.md` | ✅ |
| `docs/ARQUITECTURA.md` | ✅ |
| `docs/REGLAS_NEGOCIO.md` | ✅ |
| `backend/requirements.txt` | ✅ |
| `backend/venv` | ✅ (no commiteado) |
| Esquema de base de datos | 🔲 Siguiente |
| API REST base (FastAPI) | 🔲 Pendiente |
| Interfaz base (React + Vite) | 🔲 Pendiente |
