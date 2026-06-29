# Reglas de Negocio y Modelo de Datos — pos-boutique

> Este documento responde **qué hace el sistema y bajo qué reglas**, independientemente
> de cómo se ve la UI (eso vive en `00_FULLSTACK_DEVELOPMENT.md`) y de cómo está
> construido técnicamente (eso vive en `ARQUITECTURA.md`).
>
> **Estado:** el modelo de datos aquí descrito refleja la propuesta de `models.py`
> generada a partir de `00_FULLSTACK_DEVELOPMENT.md`, **pendiente de validación e
> implementación**. No asumas que esto ya existe en el código — revisa `AUDITORIA.md`
> para el estado real.

---

## 1. Glosario de entidades

| Tabla | Módulo | Resumen de una línea |
|---|---|---|
| `clientes` | Clientes | Cartera de crédito de la boutique |
| `pedidos` | Pedidos | Cabecera de un pedido a proveedor |
| `pedidos_articulos` | Pedidos | Artículos individuales de un pedido (1 a 4 por pedido) |
| `inventario` | Inventario | Existencias propias de la boutique (piso de venta) |
| `movimientos` | Panel Principal | Registro de toda operación de caja (contado, apartado, abono, gasto) |
| `shein_clientes` | Shein | Clientes transaccionales de Shein, independientes de `clientes` |
| `shein_pedidos` | Shein | Pedidos individuales de Shein |
| `shein_cortes` | Shein | Cortes periódicos que calculan el bono por volumen |
| `recargas` | Recargas | Registro de recargas telefónicas vendidas |
| `usuarios` | Autenticación | Cuentas de acceso al sistema |
| `configuracion` | Configuración | Parámetros del sistema (métodos de pago activos, etc.) |

---

## 2. Módulo Clientes

### Modelo de datos

| Campo | Tipo | Regla |
|---|---|---|
| `id_cliente` | Integer, PK | — |
| `no_cliente` | String, único | Autogenerado: `{Colonia}-{consecutivo:03d}` |
| `nombre` | String(40) | Obligatorio |
| `colonia` | String(20) | Obligatorio |
| `telefono` | Integer | 10 dígitos, obligatorio |
| `frecuencia_pago` | Enum: `semanal`, `quincenal`, `dia_especifico_mes`, `otro` | Obligatorio |
| `ref_nombre` | String(40) | Obligatorio |
| `ref_colonia` | String(40) | Obligatorio |
| `ref_telefono` | Integer, nullable | 10 dígitos, opcional |
| `saldo` | Float | Default `0`. Deuda acumulada |
| `estatus` | Enum: `activo`, `inactivo` | Default `activo`. Cambio manual, nunca automático |
| `fecha_registro` | Date | Autogenerado al crear |
| `fecha_pago_programada` | Date, nullable | `NULL` hasta el primer abono. Ver regla de ciclo abajo |

### Reglas de negocio

1. **`saldo = 0` no implica baja automática.** El cambio a `inactivo` siempre es una decisión operativa explícita de la operadora.
2. **Ciclo de `fecha_pago_programada`:** se instancia en el primer abono (`fecha_abono + frecuencia_pago`) y se recalcula en cada abono subsiguiente desde la fecha real del abono, no desde la fecha programada anterior. Si `frecuencia_pago = otro`, el sistema nunca calcula esta fecha.
3. **Sistema de banderas (visual, no bloqueante):**
   - 🟡 Amarilla: `fecha_pago_programada - hoy <= 2 días`
   - 🔴 Roja: `hoy > fecha_pago_programada`
   - Sin bandera: cualquier otro caso, o `fecha_pago_programada = NULL`, o `saldo = 0`

---

## 3. Módulo Pedidos (cabecera-detalle)

### Modelo de datos

**`pedidos`** (cabecera): `id_pedido`, `id_cliente` (FK), `fecha`.

**`pedidos_articulos`** (detalle, 1 a 4 filas por pedido):

| Campo | Tipo | Regla |
|---|---|---|
| `id_articulo` | Integer, PK | — |
| `id_pedido` | FK → `pedidos` | Obligatorio |
| `rol` | Enum: `principal`, `alternativa` | Default `principal` |
| `id_articulo_principal` | FK → `pedidos_articulos`, nullable | Solo se llena si `rol = alternativa` |
| `tipo_producto` | Enum: `formal`, `informal` | Obligatorio |
| `proveedor` | Enum: `Price_Shoes`, `Pakar`, `Cklass`, `otro`, nullable | Solo si `tipo_producto = formal` |
| `id_producto` | String(12), nullable | Referencia libre al catálogo del proveedor, sin FK real |
| `producto` | String(40) | Obligatorio |
| `marca`, `talla` | String, nullable | Opcionales |
| `monto` | Float, nullable | Ver regla de resolución abajo |
| `estatus_articulo` | Enum: `vigente`, `en_almacen`, `devuelto`, `cancelado` | Default `vigente` |
| `id_articulo_sustituye` | FK → `pedidos_articulos`, nullable | Solo en artículos sustitutos de una devolución |

### Reglas de negocio

1. **El saldo del cliente NO se carga al registrar el pedido.** Se carga únicamente cuando el artículo se marca `en_almacen` (es decir, cuando llega físicamente). Esta es la regla de negocio más importante del módulo: refleja que solo se cobra lo que efectivamente se surtió.
2. **Resolución de `monto`:** si `proveedor` tiene lista de precios (`Price_Shoes`, `Pakar`, `Cklass`), el sistema hace lookup automático por `id_producto`. Si `proveedor = otro`, el monto se captura manualmente.
3. **Devolución:** el artículo pasa a `devuelto`, se revierte su monto del saldo del cliente, y se abre un pedido sustituto vinculado vía `id_articulo_sustituye`.
4. **Cancelación:** el artículo pasa a `cancelado`. Si su estatus previo era `en_almacen` (ya había impactado saldo), se revierte el monto. Si era `vigente`, no hay nada que revertir porque nunca impactó el saldo.

---

## 4. Módulo Inventario

### Modelo de datos

| Campo | Tipo | Regla |
|---|---|---|
| `id_producto` | Integer, PK | No se reutiliza aunque el producto se venda |
| `categoria` | Enum: `dama`, `caballero`, `infantil`, `accesorio`, `calzado` | Obligatorio |
| `tipo_producto` | Enum: `formal`, `informal` | Obligatorio |
| `descripcion` | String(40) | Obligatorio |
| `talla`, `color`, `marca` | String, nullable | Opcionales |
| `precio_venta` | Integer | Obligatorio |
| `precio_descuento` | Integer, nullable | `NULL` = sin descuento. Con valor = precio vigente |
| `stock` | Integer | Default `0` |
| `estatus` | Enum: `disponible`, `disponible_c/descuento`, `en_ruta`, `apartado`, `vendido` | Default `disponible` |
| `descripcion_ruta` | String, nullable | Obligatorio solo si `estatus = en_ruta` |
| `created` | Date | Autogenerado |
| `changed_status` | Date, nullable | Se actualiza en cada cambio de `estatus` |

### Reglas de negocio

1. **Transiciones de estatus válidas (no es una lista plana, depende del estado actual):**
   - `disponible` → `en_ruta`, `disponible_c/descuento`, `apartado`, `vendido`
   - `disponible_c/descuento` → `disponible`, `en_ruta`, `apartado`, `vendido`
   - `en_ruta` → `disponible`, `vendido`
   - `apartado` → `disponible` (cancelación), `vendido` (liquidación)
   - `vendido` → sin transición posible
2. **`precio_descuento` no tiene columna de porcentaje** — se calcula al vuelo: `(1 - precio_descuento / precio_venta) * 100`.

---

## 5. Panel Principal — Movimientos de caja

### Modelo de datos

| Campo | Tipo | Regla |
|---|---|---|
| `id_movimiento` | Integer, PK | — |
| `operacion` | Enum: `contado`, `apartado`, `abono`, `gasto` | Obligatorio |
| `id_cliente` | FK → `clientes`, nullable | Obligatorio en `apartado`/`abono`. `NULL` en `gasto` |
| `id_producto` | FK → `inventario`, nullable | Solo cuando aplica (contado/apartado desde inventario) |
| `monto` | Float | Obligatorio, > 0 |
| `forma_pago` | Enum: `efectivo`, `transferencia`, `tarjeta` | Depende de `configuracion` (métodos activos) |
| `saldo_resultante` | Float, nullable | `NULL` en `contado`/`gasto`. Calculado en `apartado`/`abono` |
| `descripcion` | String(60), nullable | **Obligatoria únicamente en `gasto`** |
| `fecha` | DateTime | Autogenerado |

### Reglas de negocio por operación

- **Contado:** no impacta saldo de cliente. Si el producto viene de `inventario`, descuenta `stock` y marca `vendido` si llega a 0.
- **Apartado:**
  1. Cliente obligatorio. Producto debe existir en `inventario` con estatus `disponible` o `disponible_c/descuento`.
  2. **Primer pago mínimo: $100.00.** El backend rechaza montos menores.
  3. `saldo_resultante = precio_producto - primer_pago`, se **suma** al saldo existente del cliente (nunca se sobrescribe).
  4. `inventario.estatus` cambia a `apartado` en la misma transacción.
  5. Cancelación del apartado: `inventario.estatus` vuelve a `disponible`; el saldo pendiente se resta (el primer pago no se devuelve salvo decisión de la operadora).
- **Abono:** `saldo_resultante = saldo_actual - monto`. Rechazado si `monto > saldo_actual`. Recalcula `fecha_pago_programada` del cliente. Si el saldo llega a 0, el cliente **no** cambia de estatus automáticamente.
- **Gasto:** sin cliente ni producto. `descripcion` obligatoria. `saldo_resultante = NULL`. Representa salida de caja.

> El saldo agregado del negocio no es un campo en base de datos — se deriva por consulta agregada sobre `movimientos` (ver Módulo Consulta Global).

---

## 6. Módulo Shein

> La boutique actúa como intermediaria: compra en la app de Shein a nombre del cliente y cobra el mismo precio, siempre de contado, sin devoluciones.

### Modelo de datos

**`shein_clientes`** (independiente de `clientes` — sin saldo, sin garante, sin frecuencia de pago): `id_shein_cliente`, `nombre` (20), `colonia` (12), `telefono` (Integer, 10 dígitos).

**`shein_pedidos`**: `id_shein_pedido`, `id_shein_cliente` (FK), `id_shein_corte` (FK, nullable hasta asignarse a un corte), `producto`, `monto` (precio al momento del pedido), `monto_vigente` (nullable, se llena si el precio cambió al cerrar el corte), `fecha`.

**`shein_cortes`**: `id_shein_corte`, `fecha_corte`, `total_pedidos`, `suma_montos`, `porcentaje_bono`, `bono_monto` (= `suma_montos * porcentaje_bono`, calculado por backend).

### Reglas de negocio

1. **Por qué `shein_clientes` es independiente:** forzar estos clientes en `clientes` introduciría campos obligatorios que no aplican (garante, saldo, frecuencia de pago) y contaminaría la cartera de crédito real.
2. **Variación de precios:** si el precio de un artículo bajó entre el pedido y el corte, la tienda absorbe la diferencia sin notificar. Si subió, debe notificarse al cliente antes de ejecutar la compra — el campo `monto_vigente` es el mecanismo de control en MVP.
3. El bono no pertenece a ningún cliente o artículo individual — es resultado agregado de un corte.

---

## 7. Módulo Recargas Telefónicas

Tabla independiente, sin relaciones: `id_recarga`, `compania` (Enum: `Telcel`, `Movistar`, `Unefon`, `AT&T`), `monto`, `fecha` (timestamp completo, autogenerado). Sin validación de tope de monto. Sin impacto en saldo de clientes ni inventario — solo trazabilidad de ingresos.

---

## 8. Autenticación

**`usuarios`**: `id_usuario`, `usuario` (único), `password_hash` (bcrypt), `rol` (Enum: `estandar`, `admin`), `activo` (booleano/entero).

- Login construido pero desactivado en MVP (`AUTH_ENABLED = False`).
- Sin recuperación de contraseña por correo (sistema offline) — la hace el desarrollador directamente en la base de datos.
- Permisos diferenciados por rol: pendientes de implementación futura, sin cambio de esquema cuando llegue ese momento.

---

## 9. Configuración

**`configuracion`**: tabla clave-valor (`clave` PK, `valor`). Controla qué métodos de pago están activos (`pago_efectivo_activo`, `pago_transferencia_activo`, etc.), CLABEs registradas, y zona horaria (informativa, solo lectura).

- Efectivo: siempre activo, no desactivable.
- Transferencia, tarjeta débito/crédito: activos por defecto, se pueden desactivar.
- MSI y vales: bloqueados por defecto, se pueden activar.

---

## 10. Módulo Consulta Global

Tres consultas de solo lectura sobre datos agregados (no reemplazan la Consulta Historial por cliente individual):

1. **Ventas totales por período** — suma de `movimientos` (excluyendo `gasto`) agrupada por operación, con total consolidado.
2. **Ventas por segmento** — distribución entre Caja (movimientos), Shein y Recargas en un período.
3. **Cartera de clientes por segmento** — clientes con saldo activo agrupados por colonia, con saldo total y promedio.

---

## 11. Invariantes globales del sistema

Reglas que aplican transversalmente y que cualquier servicio nuevo debe respetar:

- El saldo de un cliente nunca se sobrescribe directamente — siempre se suma o resta (`saldo += monto` / `saldo -= monto`), nunca `saldo = monto`.
- Ninguna operación de caja se registra sin `forma_pago`.
- Ningún cambio de estatus en `inventario` ocurre sin actualizar `changed_status`.
- Toda fecha de negocio se almacena en `YYYY-MM-DD` (o timestamp completo cuando la tabla lo requiere) y se muestra al usuario en `DD-MM-YYYY`.
