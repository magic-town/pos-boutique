# Reglas de Negocio y Modelo de Datos — pos-boutique

> Este documento responde **qué hace el sistema y bajo qué reglas**, independientemente
> de cómo se ve la UI (eso vive en `00_FULLSTACK_DEVELOPMENT.md`) y de cómo está
> construido técnicamente (eso vive en `ARQUITECTURA.md`).
>
> **Estado:** el modelo de datos aquí descrito está implementado en
> `backend/app/models/models.py` y migrado a `pos.db` (`a1b2c3d4e5f6_esquema_inicial.py`).
> La tabla `precios_catalogo` está diseñada y cerrada pero pendiente de agregar
> a `models.py` + migración Alembic.

---

## 1. Glosario de entidades

| Tabla | Módulo | Resumen de una línea |
|---|---|---|
| `clientes` | Clientes | Cartera de crédito de la boutique |
| `pedidos` | Pedidos | Cabecera de un pedido a proveedor |
| `pedidos_articulos` | Pedidos | Artículos individuales de un pedido (1 a 4 por pedido) |
| `precios_catalogo` | Pedidos | Catálogo de precios importado desde `tabla_precios.ods` |
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
| `id_cliente` | Integer, PK | Nunca aparece en UI |
| `no_cliente` | String, único | Autogenerado: `{Colonia}-{consecutivo:03d}` |
| `nombre` | String(40) | Obligatorio |
| `colonia` | String(20) | Obligatorio |
| `telefono` | Integer | 10 dígitos, obligatorio |
| `frecuencia_pago` | Enum: `semanal`, `quincenal`, `dia_especifico_mes`, `otro` | Obligatorio |
| `ref_nombre` | String(40) | Obligatorio |
| `ref_colonia` | String(40) | Obligatorio |
| `ref_telefono` | Integer, nullable | 10 dígitos, opcional |
| `saldo` | Float | Default `0`. Deuda acumulada del cliente |
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

**`pedidos_articulos`** (detalle, 1 a 4 artículos principales por pedido):

| Campo | Tipo | Regla |
|---|---|---|
| `id_articulo` | Integer, PK | Nunca aparece en UI |
| `id_pedido` | FK → `pedidos` | Obligatorio |
| `rol` | Enum: `principal`, `alternativa` | Default `principal` |
| `id_articulo_principal` | FK → `pedidos_articulos`, nullable | Solo se llena si `rol = alternativa`. Enlaza la alternativa con su principal |
| `tipo_producto` | Enum: `formal`, `informal` | Obligatorio |
| `proveedor` | Enum: `Price_Shoes`, `Pakar`, `Cklass`, `otro`, nullable | Solo si `tipo_producto = formal`. NULL si informal |
| `id_producto` | String(12), nullable | Referencia libre al catálogo del proveedor. Sin FK real. Solo si formal |
| `producto` | String(40) | Obligatorio |
| `marca`, `talla` | String, nullable | Opcionales en cualquier tipo |
| `monto` | Float, nullable | Ver regla de resolución abajo |
| `estatus_articulo` | Enum: `vigente`, `en_almacen`, `devuelto`, `cancelado` | Default `vigente`. Controla el ciclo de vida |
| `id_articulo_sustituye` | FK → `pedidos_articulos`, nullable | Solo en artículo sustituto de una devolución. Apunta al artículo original devuelto |

**`precios_catalogo`** (catálogo importado desde `tabla_precios.ods`):

| Campo | Tipo | Regla |
|---|---|---|
| `id_precio` | Integer, PK | Interno |
| `proveedor` | Enum: `Price_Shoes`, `Pakar`, `Cklass` | Sin `otro` — ese proveedor no tiene catálogo digitalizado |
| `id_producto` | String(12) | Normalizado desde `ID`/`CÓDIGO`/`modelo` según pestaña de origen |
| `precio_venta` | Integer | Precio final de venta que usa el POS |
| `fecha_catalogo` | Date | Normalizada a ISO. Determina qué precio gana cuando hay duplicados |
| `catalogo` | String, nullable | Nombre del catálogo/tomo — preservado del .ods, no usado por el POS |
| `temporada` | String, nullable | Temporada — preservado del .ods, no usado por el POS |
| `pagina` | Integer, nullable | Página en el catálogo físico — preservado del .ods |
| `precio_base` | Integer, nullable | Precio sugerido/base — preservado del .ods |

Sin restricción `UNIQUE`. El mismo `id_producto` puede repetirse en catálogos futuros (producto vigente temporada tras temporada). Lookup siempre por `MAX(fecha_catalogo)`.

### Reglas de negocio

1. **Un pedido tiene de 1 a 4 artículos principales.** Solo el primero es obligatorio al crear; los demás se pueden agregar mientras el pedido sea editable (artículos en `vigente`).
2. **Cada principal puede tener 0 o 1 alternativa.** La alternativa es una buena práctica operativa (se ofrece si el principal no está disponible en el proveedor), pero nunca es obligatoria para guardar el pedido.
3. **El saldo del cliente NO se carga al registrar el pedido.** Se carga únicamente cuando el artículo se marca `en_almacen`. Solo se cobra lo que efectivamente se surtió.
4. **Resolución de `monto`:**
   - `formal` + proveedor con catálogo (`Price_Shoes`, `Pakar`, `Cklass`): lookup automático en `precios_catalogo` por `id_producto`, gana `MAX(fecha_catalogo)`. Si no existe el ID, campo queda vacío y editable.
   - `formal` + `proveedor = otro`: captura manual obligatoria.
   - `informal`: captura libre, opcional.
5. **`estatus_articulo` y su efecto en saldo:**
   - `vigente` → sin efecto en saldo.
   - `vigente` → `en_almacen`: `saldo += monto` (el artículo llegó al piso).
   - `en_almacen` → `devuelto`: `saldo -= monto` (cliente devuelve). Se abre pedido sustituto pre-cargado. El sustituto nace `vigente` e impactará saldo cuando llegue a `en_almacen`.
   - `vigente` → `cancelado`: sin efecto en saldo (nunca se había cargado).
   - `en_almacen` → `cancelado`: `saldo -= monto` si `monto IS NOT NULL` (se revierte lo que se había cargado). El artículo pasa a inventario físico.
6. **`id_articulo_sustituye`** se llena únicamente en el artículo sustituto de una devolución, apuntando al `id_articulo` del original devuelto. En todos los demás casos es `NULL`.
7. **Lista de Surtido:** vista global de todos los artículos en `vigente` dentro de un período de corte configurable (default: miércoles a martes). Es la lista con la que se realizan las compras al proveedor. Desde esta vista la operadora marca artículos como `en_almacen` — ese es el momento en que el saldo se carga al cliente.
8. **Sincronización de `precios_catalogo`:** el script `backend/app/scripts/importar_precios.py` lee `tabla_precios.ods` y hace solo `INSERT` de filas nuevas (nunca borra ni sobreescribe). El usuario lo dispara manualmente desde el POS o terminal cuando el proveedor libera catálogo nuevo.

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
| `descripcion_ruta` | String, nullable | Obligatorio solo si `estatus = en_ruta` (validado en servicio) |
| `created` | Date | Autogenerado |
| `changed_status` | Date, nullable | Se actualiza en cada cambio de `estatus` |

### Reglas de negocio

1. **Transiciones de estatus válidas:**
   - `disponible` → `en_ruta`, `disponible_c/descuento`, `apartado`, `vendido`
   - `disponible_c/descuento` → `disponible`, `en_ruta`, `apartado`, `vendido`
   - `en_ruta` → `disponible`, `vendido`
   - `apartado` → `disponible` (cancelación), `vendido` (liquidación)
   - `vendido` → sin transición posible
2. **`precio_descuento` no tiene columna de porcentaje** — se calcula al vuelo: `(1 - precio_descuento / precio_venta) * 100`.
3. **Todo cambio de `estatus` debe actualizar `changed_status`** en la misma transacción — invariante global del sistema.

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
  3. `saldo_resultante = precio_producto - primer_pago`, se **suma** al saldo existente del cliente (`saldo += saldo_resultante`). Nunca se sobrescribe.
  4. `inventario.estatus` cambia a `apartado` en la misma transacción.
  5. Cancelación del apartado: `inventario.estatus` vuelve a `disponible`; el saldo pendiente se resta (el primer pago no se devuelve salvo decisión de la operadora).
- **Abono:** `saldo_resultante = saldo_actual - monto`. Rechazado si `monto > saldo_actual`. Recalcula `fecha_pago_programada` del cliente. Si el saldo llega a 0, el cliente **no** cambia de estatus automáticamente.
- **Gasto:** sin cliente ni producto. `descripcion` obligatoria. `saldo_resultante = NULL`. Representa salida de caja.

> El saldo agregado del negocio no es un campo en base de datos — se deriva por consulta agregada sobre `movimientos`.

---

## 6. Módulo Shein

> La boutique actúa como intermediaria: compra en la app de Shein a nombre del cliente y cobra el mismo precio, siempre de contado, sin devoluciones.

### Modelo de datos

**`shein_clientes`** (independiente de `clientes` — sin saldo, sin garante, sin frecuencia de pago):

| Campo | Tipo | Regla |
|---|---|---|
| `id_shein_cliente` | Integer, PK | — |
| `nombre` | String(20) | Obligatorio |
| `colonia` | String(12) | Obligatorio |
| `telefono` | Integer | 10 dígitos, obligatorio |

**`shein_pedidos`:**

| Campo | Tipo | Regla |
|---|---|---|
| `id_shein_pedido` | Integer, PK | — |
| `id_shein_cliente` | FK → `shein_clientes` | Obligatorio |
| `id_shein_corte` | FK → `shein_cortes`, nullable | `NULL` hasta asignarse a un corte |
| `producto` | String | Obligatorio |
| `monto` | Float | Precio al momento del pedido |
| `monto_vigente` | Float, nullable | Se llena si el precio cambió al cerrar el corte |
| `fecha` | Date | Autogenerado |

**`shein_cortes`:**

| Campo | Tipo | Regla |
|---|---|---|
| `id_shein_corte` | Integer, PK | — |
| `fecha_corte` | Date | Obligatorio |
| `total_pedidos` | Integer | Calculado por backend |
| `suma_montos` | Float | Calculado por backend |
| `porcentaje_bono` | Float | Ej. `0.08` para 8% |
| `bono_monto` | Float | `suma_montos * porcentaje_bono`, calculado por backend |

### Reglas de negocio

1. **Por qué `shein_clientes` es independiente:** forzar estos clientes en `clientes` introduciría campos obligatorios que no aplican (garante, saldo, frecuencia de pago) y contaminaría la cartera de crédito real.
2. **Variación de precios:** si el precio bajó entre pedido y corte, la tienda absorbe la diferencia. Si subió, se notifica al cliente antes de ejecutar la compra — `monto_vigente` es el mecanismo de control en MVP.
3. El bono no pertenece a ningún cliente o artículo individual — es resultado agregado de un corte.

---

## 7. Módulo Recargas Telefónicas

Tabla independiente, sin relaciones:

| Campo | Tipo | Regla |
|---|---|---|
| `id_recarga` | Integer, PK | — |
| `compania` | Enum: `Telcel`, `Movistar`, `Unefon`, `AT&T` | Obligatorio |
| `monto` | Float | Obligatorio |
| `fecha` | DateTime | Autogenerado (timestamp completo) |

Sin validación de tope de monto. Sin impacto en saldo de clientes ni inventario — solo trazabilidad de ingresos.

---

## 8. Autenticación

**`usuarios`:**

| Campo | Tipo | Regla |
|---|---|---|
| `id_usuario` | Integer, PK | — |
| `usuario` | String, único | 4 a 16 caracteres, sin espacios |
| `password_hash` | String | bcrypt. Nunca texto plano |
| `rol` | String | `estandar` o `admin`. Default `estandar` |
| `activo` | Integer | `1` = activo, `0` = desactivado. Default `1` |
| `fecha_registro` | DateTime | Autogenerado |

- Autenticación **activa** en todos los endpoints vía JWT (`python-jose`). Sin flag `AUTH_ENABLED` — no existe en `config.py`.
- Sin recuperación de contraseña por correo (sistema offline) — la hace el desarrollador directamente en la base de datos.
- Permisos diferenciados por rol: pendientes de implementación futura, sin cambio de esquema.

---

## 9. Configuración

**`configuracion`**: tabla clave-valor (`clave` PK, `valor`). Controla qué métodos de pago están activos (`pago_efectivo_activo`, `pago_transferencia_activo`, etc.), CLABEs registradas, zona horaria (informativa) y período de corte de la Lista de Surtido (día de inicio y fin, default miércoles a martes).

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

- El saldo de un cliente **nunca se sobrescribe** — siempre `saldo += monto` o `saldo -= monto`. Nunca `saldo = monto`.
- Ninguna operación de caja se registra sin `forma_pago`.
- Ningún cambio de `estatus` en `inventario` ocurre sin actualizar `changed_status` en la misma transacción.
- Toda fecha de negocio se almacena en `YYYY-MM-DD` (o timestamp completo cuando la tabla lo requiere) y se muestra al usuario en `DD-MM-YYYY`.
- `id_articulo_sustituye` solo se llena en artículos sustitutos de devolución. En todos los demás casos es `NULL`.
- El script `importar_precios.py` solo hace `INSERT`. Nunca borra ni sobreescribe filas existentes en `precios_catalogo`.
