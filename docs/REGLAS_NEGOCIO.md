# Reglas de Negocio y Modelo de Datos — pos-boutique

> Este documento responde **qué hace el sistema y bajo qué reglas**, independientemente
> de cómo se ve la UI (eso vive en `docs/spec/module_*.md`) y de cómo está
> construido técnicamente (eso vive en `ARQUITECTURA.md`).
>
> **Estado:** el modelo de datos aquí descrito está implementado en
> `backend/app/models/models.py` y migrado a `pos.db` (head `d4e5f6a7b8c9`).
> Las tablas `cartera_vencida`, `familiares` y `shein_movimientos`, así como las
> columnas nuevas en `shein_clientes`, están especificadas aquí pero pendientes de
> migración Alembic y actualización en `models.py`.

---

## 1. Glosario de entidades

| Tabla                     | Módulo          | Resumen de una línea                                                        |
|---------------------------|-----------------|-----------------------------------------------------------------------------|
| `clientes`                | Clientes        | Cartera de crédito de la boutique                                           |
| `cartera_vencida`         | Clientes        | Archivo de clientes morosos cancelados; tabla independiente sin FKs         |
| `familiares`              | Clientes        | Vínculos familiares entre pares de clientes de la cartera                   |
| `pedidos`                 | Pedidos         | Cabecera de un pedido a proveedor                                           |
| `pedidos_articulos`       | Pedidos         | Artículos individuales de un pedido (1 a 4 por pedido)                      |
| `precios_catalogo`        | Pedidos         | Catálogo de precios importado desde `tabla_precios.ods`                     |
| `inventario`              | Inventario      | Existencias propias de la boutique (piso de venta)                          |
| `movimientos`             | Panel Principal | Registro de toda operación de caja (contado, apartado, abono, gasto)        |
| `apartados`               | Panel Principal | Cabecera de un apartado: cliente, fecha semilla y saldo pendiente del lote  |
| `apartados_articulos`     | Panel Principal | Artículos individuales de un apartado (1 a N por lote)                      |
| `shein_clientes`          | Shein           | Clientes con cartera de crédito propia, independientes de `clientes`        |
| `shein_movimientos`       | Shein           | Abonos a la cartera de crédito Shein                                        |
| `shein_pedidos`           | Shein           | Cabecera de un pedido Shein (1 a 4 artículos)                               |
| `shein_pedidos_articulos` | Shein           | Artículos individuales de un pedido Shein (1 a 4 por pedido)                |
| `shein_cortes`            | Shein           | Cortes periódicos que concentran pedidos y registran el `cupon`             |
| `recargas`                | Recargas        | Registro de recargas telefónicas vendidas                                   |
| `usuarios`                | Autenticación   | Cuentas de acceso al sistema                                                |
| `configuracion`           | Configuración   | Parámetros del sistema (métodos de pago activos, etc.)                      |

---

## 2. Módulo Clientes

### Modelo de datos

| Campo                    | Tipo                                    | Regla                                                                              |
|--------------------------|-----------------------------------------|------------------------------------------------------------------------------------|
| `id_cliente`             | Integer, PK                             | Nunca aparece en UI. No cambia aunque se reutilice el `no_cliente`.                |
| `no_cliente`             | String, único                           | Slot reutilizable. Formato: `{Colonia}-{consecutivo:03d}`                         |
| `nombre`                 | String(40)                              | Obligatorio                                                                        |
| `colonia`                | String(20)                              | Obligatorio                                                                        |
| `telefono`               | Integer                                 | 10 dígitos, obligatorio                                                            |
| `frecuencia_pago`        | Enum: `semanal`, `quincenal`, `dia_especifico_mes`, `otro` | Obligatorio                                              |
| `dia_pago_especifico`    | Integer, nullable                       | 1-31. Obligatorio solo si `frecuencia_pago = dia_especifico_mes`                   |
| `frecuencia_pago_detalle`| String(60), nullable                    | Obligatorio solo si `frecuencia_pago = otro`                                       |
| `ref_nombre`             | String(40)                              | Obligatorio                                                                        |
| `ref_colonia`            | String(40)                              | Obligatorio                                                                        |
| `ref_telefono`           | Integer, nullable                       | 10 dígitos, opcional                                                               |
| `saldo`                  | Float                                   | Default `0`. Deuda acumulada del cliente                                           |
| `estatus`                | Enum: `activo`, `inactivo`              | Default `inactivo`. Derivado del `saldo`, siempre automático, nunca editable       |
| `fecha_registro`         | Date                                    | Autogenerado al crear                                                              |
| `fecha_pago_programada`  | Date, nullable                          | `NULL` hasta el primer abono                                                       |

### Tabla `cartera_vencida`

| Campo                    | Tipo        | Regla                                                      |
|--------------------------|-------------|------------------------------------------------------------|
| `id_cartera_vencida`     | Integer, PK | —                                                          |
| `no_cliente_original`    | String      | `no_cliente` del slot al momento de la cancelación        |
| `nombre`                 | String      | Datos del cliente moroso                                   |
| `colonia`                | String      | —                                                          |
| `telefono`               | Integer     | —                                                          |
| `ref_nombre`             | String      | —                                                          |
| `ref_colonia`            | String      | —                                                          |
| `ref_telefono`           | Integer, nullable | —                                                   |
| `saldo_cancelado`        | Float       | Deuda perdonada al momento de cancelación                  |
| `fecha_registro_original`| String      | `fecha_registro` del registro en `clientes`               |
| `fecha_cancelacion`      | String      | Fecha de la operación `Cancelar Cliente`                   |

Sin llaves foráneas. Tabla de archivo independiente; no se relaciona con ninguna otra tabla.

### Tabla `familiares`

| Campo          | Tipo        | Regla                                                                  |
|----------------|-------------|------------------------------------------------------------------------|
| `id_vinculo`   | Integer, PK | —                                                                      |
| `id_cliente_a` | Integer, FK → `clientes` | Siempre el menor de los dos `id_cliente`            |
| `id_cliente_b` | Integer, FK → `clientes` | Siempre el mayor de los dos `id_cliente`            |

`CHECK (id_cliente_a < id_cliente_b)` + índice único en `(id_cliente_a, id_cliente_b)`
garantizan que cada par familiar se almacene en un único orden sin duplicados invertidos.

### Reglas de negocio

1. **`estatus` es un campo derivado del `saldo`, nunca una decisión operativa.** El cliente nace `inactivo` con `saldo = 0`. Pasa a `activo` automáticamente cuando un movimiento impacta su `saldo` al alza. Regresa a `inactivo` automáticamente cuando su `saldo` llega a `0`.
2. **`no_cliente` es un slot reutilizable.** La `PRIMARY KEY` no cambia. Cuando el slot queda disponible (saldo = 0 e inactivo), la operadora puede asignarlo a un nuevo cliente reescribiendo los campos del registro. El historial de movimientos, pedidos y apartados del cliente anterior queda vinculado al mismo `id_cliente`.
3. **`Cancelar Cliente`** se aplica a clientes en `bandera_roja`. La operación: (1) copia los datos del cliente a `cartera_vencida`, (2) pone `saldo = 0` y limpia los campos del slot en `clientes`. El agregado de cuentas por cobrar del negocio (`Σ clientes.saldo WHERE saldo > 0`) disminuye en el monto cancelado.
4. **Ciclo de `fecha_pago_programada`:** se instancia en el primer abono y se recalcula en cada abono subsiguiente. Fórmula diferenciada por `frecuencia_pago`:
   - **`semanal`:** rodante. `fecha_pago_programada = fecha_abono + 7 días`.
   - **`quincenal`:** fechas fijas de calendario: día `15` y último día del mes. `fecha_pago_programada` = la próxima de esas dos fechas posterior al abono.
   - **`dia_especifico_mes`:** se fija al día capturado en `dia_pago_especifico`. `fecha_pago_programada` = la próxima ocurrencia posterior al abono. Si el día no existe en el mes, se aplica *clamp* al último día del mes.
   - **`otro`:** el sistema nunca calcula. `fecha_pago_programada` permanece `NULL`. El acuerdo vive en `frecuencia_pago_detalle`.
5. **Sistema de banderas (visual, no bloqueante):**
   - 🟡 Amarilla: `fecha_pago_programada - hoy <= 2 días`
   - 🔴 Roja: `hoy > fecha_pago_programada`
   - 🟠 Naranja: cliente tiene apartado abierto (`apartados.estatus = 'abierto'`) y faltan ≤ 5 días para cumplirse un mes desde `apartados.fecha_apartado`
   - ⚫ Negra: el cliente tiene `bandera_roja` **Y** al menos un familiar (vía tabla `familiares`) también tiene `bandera_roja` simultáneamente. Se calcula al vuelo.
   - Sin bandera: ninguna de las anteriores, o `fecha_pago_programada = NULL`, o `saldo = 0`.
6. **Tabla `familiares` sin transitividad.** Solo pares declarados explícitamente. Un cliente puede tener múltiples vínculos. La operadora los gestiona desde **Editar Cliente**.

---

## 3. Módulo Pedidos (cabecera-detalle)

### Modelo de datos

**`pedidos`** (cabecera): `id_pedido`, `id_cliente` (FK), `fecha`.

**`pedidos_articulos`** (detalle, 1 a 4 artículos principales por pedido):

| Campo                     | Tipo                                                          | Regla                                                                                                                     |
|---------------------------|---------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `id_articulo`             | Integer, PK                                                   | Nunca aparece en UI                                                                                                       |
| `id_pedido`               | FK → `pedidos`                                                | Obligatorio                                                                                                               |
| `rol`                     | Enum: `principal`, `alternativa`                              | Default `principal`                                                                                                       |
| `id_articulo_principal`   | FK → `pedidos_articulos`, nullable                            | Solo si `rol = alternativa`                                                                                               |
| `tipo_producto`           | Enum: `formal`, `informal`                                    | Obligatorio                                                                                                               |
| `proveedor`               | Enum: `Price_Shoes`, `Pakar`, `Cklass`, `otro`, nullable      | Solo si `tipo_producto = formal`. NULL si informal                                                                        |
| `id_producto`             | String(12), nullable                                          | Sin FK real. Solo si formal                                                                                               |
| `producto`                | String(40)                                                    | Obligatorio                                                                                                               |
| `marca`, `talla`          | String, nullable                                              | Opcionales                                                                                                                |
| `monto`                   | Float, nullable                                               | Ver regla de resolución                                                                                                   |
| `estatus_articulo`        | Enum: `vigente`, `en_almacen`, `devuelto`, `cancelado`        | Default `vigente`                                                                                                         |
| `id_articulo_sustituye`   | FK → `pedidos_articulos`, nullable                            | Solo en artículo sustituto de una devolución                                                                              |

**`precios_catalogo`** (catálogo importado desde `tabla_precios.ods`):

| Campo           | Tipo                                | Regla                                                                     |
|-----------------|-------------------------------------|---------------------------------------------------------------------------|
| `id_precio`     | Integer, PK                         | Interno                                                                   |
| `proveedor`     | Enum: `Price_Shoes`, `Pakar`, `Cklass` | Sin `otro`                                                             |
| `id_producto`   | String(12)                          | Lookup por `proveedor` + `id_producto`, gana `MAX(fecha_catalogo)`        |
| `precio_venta`  | Integer                             | Precio final de venta                                                     |
| `fecha_catalogo`| Date                                | Determina qué precio gana cuando hay duplicados                           |
| `catalogo`, `temporada`, `pagina`, `precio_base` | varios | Preservados del .ods, no usados por el POS                |

### Reglas de negocio

1. Un pedido tiene de 1 a 4 artículos principales. Solo el primero es obligatorio al crear.
2. Cada principal puede tener 0 o 1 alternativa, salvo `proveedor = Price_Shoes` (hasta 3 alternativas).
3. **El saldo del cliente NO se carga al registrar el pedido.** Solo cuando el artículo se marca `en_almacen`.
4. **Resolución de `monto`:** formal con catálogo → lookup automático por `MAX(fecha_catalogo)`; formal con `otro` → captura manual; informal → captura libre, opcional.
5. **`estatus_articulo` y su efecto en saldo:**
   - `vigente` → sin efecto.
   - `vigente` → `en_almacen`: `saldo += monto`. Si el cliente era `inactivo`, cambia a `activo`.
   - `en_almacen` → `devuelto`: `saldo -= monto`. Se abre pedido sustituto pre-cargado.
   - `vigente` → `cancelado`: sin efecto.
   - `en_almacen` → `cancelado`: `saldo -= monto` si `monto IS NOT NULL`. Artículo pasa a inventario.
6. **Lista de Surtido:** vista global de artículos en `vigente` dentro del período de corte configurable (default: miércoles a martes). Desde aquí la operadora marca artículos como `en_almacen`.
7. El script `importar_precios.py` solo hace `INSERT`. Nunca borra ni sobreescribe.

---

## 4. Módulo Inventario

### Modelo de datos

| Campo               | Tipo                                                                           | Regla                                   |
|---------------------|--------------------------------------------------------------------------------|-----------------------------------------|
| `id_producto`       | Integer, PK                                                                    | No se reutiliza                         |
| `categoria`         | Enum: `dama`, `caballero`, `infantil`, `accesorio`, `calzado`                  | Obligatorio                             |
| `tipo_producto`     | Enum: `formal`, `informal`                                                     | Obligatorio                             |
| `descripcion`       | String(40)                                                                     | Obligatorio                             |
| `talla`, `color`, `marca` | String, nullable                                                         | Opcionales                              |
| `precio_venta`      | Integer                                                                        | Obligatorio                             |
| `precio_descuento`  | Integer, nullable                                                              | `NULL` = sin descuento                  |
| `stock`             | Integer                                                                        | Default `0`                             |
| `estatus`           | Enum: `disponible`, `disponible_c/descuento`, `en_ruta`, `apartado`, `vendido` | Default `disponible`                    |
| `descripcion_ruta`  | String, nullable                                                               | Obligatorio solo si `estatus = en_ruta` |
| `created`           | Date                                                                           | Autogenerado                            |
| `changed_status`    | Date, nullable                                                                 | Se actualiza en cada cambio de `estatus`|

### Reglas de negocio

1. **Transiciones válidas:** `disponible` → `en_ruta`, `disponible_c/descuento`, `apartado`, `vendido`. `disponible_c/descuento` → `disponible`, `en_ruta`, `apartado`, `vendido`. `en_ruta` → `disponible`, `vendido`. `apartado` → `disponible` (cancelación), `vendido` (liquidación). `vendido` → terminal.
2. `precio_descuento` no tiene columna de porcentaje — se calcula al vuelo: `(1 - precio_descuento / precio_venta) * 100`.
3. Todo cambio de `estatus` debe actualizar `changed_status` en la misma transacción.

---

## 5. Panel Principal — Movimientos de caja

> El Panel Principal es la pantalla de operación cotidiana. Cubre cuatro operaciones —
> `contado`, `apartado`, `abono`, `gasto` — y escribe en `movimientos`, y adicionalmente
> en `apartados` / `apartados_articulos` cuando la operación es `apartado`.

### Modelo de datos

**`movimientos`** (registro de todo evento de caja):

| Campo            | Tipo                                                  | Regla                                                          |
|------------------|-------------------------------------------------------|----------------------------------------------------------------|
| `id_movimiento`  | Integer, PK                                           | —                                                              |
| `operacion`      | Enum: `contado`, `apartado`, `abono`, `gasto`         | Obligatorio                                                    |
| `id_cliente`     | FK → `clientes`, nullable                             | Obligatorio en `apartado`/`abono`. `NULL` en `gasto`           |
| `id_producto`    | FK → `inventario`, nullable                           | Solo en `contado` con coincidencia en inventario               |
| `id_apartado`    | FK → `apartados`, nullable                            | Solo en `apartado`                                             |
| `monto`          | Float                                                 | Obligatorio, > 0                                               |
| `forma_pago`     | Enum: `efectivo`, `transferencia`, `tarjeta`          | Depende de `configuracion`                                     |
| `saldo_resultante`| Float, nullable                                      | `NULL` en `contado`/`gasto`. Calculado en `apartado`/`abono`   |
| `descripcion`    | String(60), nullable                                  | Obligatoria únicamente en `gasto`                              |
| `fecha`          | DateTime                                              | Autogenerado                                                   |

**`apartados`** (cabecera de un lote de apartado):

| Campo               | Tipo                       | Regla                                           |
|---------------------|----------------------------|-------------------------------------------------|
| `id_apartado`       | Integer, PK                | —                                               |
| `id_cliente`        | FK → `clientes`            | Obligatorio                                     |
| `fecha_apartado`    | DateTime                   | Autogenerado. Semilla de la bandera naranja      |
| `monto_primer_pago` | Float                      | Mínimo $100.00. Por lote, no por artículo        |
| `saldo_pendiente`   | Float                      | `Σ(precio_producto) - monto_primer_pago`         |
| `estatus`           | Enum: `abierto`, `liquidado`| Default `abierto`                              |

**`apartados_articulos`** (detalle, 1 a N artículos por lote):

| Campo                  | Tipo                               | Regla                                                     |
|------------------------|------------------------------------|-----------------------------------------------------------|
| `id_apartado_articulo` | Integer, PK                        | Nunca aparece en UI                                       |
| `id_apartado`          | FK → `apartados`                   | Obligatorio                                               |
| `id_producto`          | FK → `inventario`, nullable        | Opcional. `NULL` si no hay coincidencia en inventario     |
| `precio_producto`      | Float                              | Autollenado desde inventario o capturado a mano. Siempre persistido |
| `estatus_articulo`     | Enum: `vigente`, `vendido`, `cancelado` | Default `vigente`                                   |

### Reglas de negocio por operación

- **Contado:** no impacta saldo de cliente. `id_producto` opcional; si hay coincidencia en `inventario`, se descuenta `stock` y se actualiza `estatus`. Sin coincidencia: descripción y precio manual, sin efecto en inventario.
- **Apartado:** cliente obligatorio, un solo apartado abierto por cliente a la vez. `id_producto` opcional por artículo. Primer pago mínimo $100.00 por lote. `saldo_pendiente = Σ(precio_producto) - monto_primer_pago` se suma al saldo del cliente. Liquidación: cuando `saldo_pendiente = 0`, `estatus → liquidado`, artículos vigentes con inventario → `vendido`. Cancelación de artículo: `estatus_articulo → cancelado`; inventario regresa a disponible. **No ajusta `saldo_pendiente` ni `clientes.saldo`**.
- **Abono:** `saldo_resultante = saldo_actual - monto`. Rechazado si `monto > saldo_actual`. Recalcula `fecha_pago_programada`. Si el cliente tiene apartado abierto, el abono reduce también `apartados.saldo_pendiente`; si llega a `0`, se aplica liquidación. Si `saldo_resultante = 0`, `estatus → inactivo`.
- **Gasto:** sin cliente ni producto. `descripcion` obligatoria. `saldo_resultante = NULL`. Salida de caja.

> El saldo agregado del negocio no es un campo en base de datos — se deriva por consulta agregada sobre `movimientos`.

---

## 6. Módulo Shein

> La boutique actúa como intermediaria. El cliente solicita artículos en la app de Shein,
> la tienda ejecuta la compra y cobra al mismo precio. Los clientes tienen cartera de
> crédito propia en `shein_clientes`, independiente de la cartera principal. Sin
> devoluciones.

### Modelo de datos

**`shein_clientes`** (independiente de `clientes` — con saldo, frecuencia de pago, banderas):

| Campo                    | Tipo                                                   | Regla                                                           |
|--------------------------|--------------------------------------------------------|-----------------------------------------------------------------|
| `id_shein_cliente`       | Integer, PK                                            | —                                                               |
| `nombre`                 | String(20)                                             | Obligatorio                                                     |
| `colonia`                | String(12)                                             | Obligatorio                                                     |
| `telefono`               | Integer                                                | 10 dígitos, obligatorio                                         |
| `frecuencia_pago`        | Enum: `semanal`, `quincenal`, `dia_especifico_mes`, `otro` | Obligatorio                                                 |
| `dia_pago_especifico`    | Integer, nullable                                      | 1-31. Solo si `frecuencia_pago = dia_especifico_mes`            |
| `frecuencia_pago_detalle`| String(60), nullable                                   | Solo si `frecuencia_pago = otro`                                |
| `saldo`                  | Float                                                  | Default `0`. Deuda acumulada                                    |
| `estatus`                | Enum: `activo`, `inactivo`                             | Default `inactivo`. Derivado del `saldo`, nunca manual          |
| `fecha_pago_programada`  | Date, nullable                                         | `NULL` hasta el primer abono                                    |

**`shein_movimientos`** (abonos a la cartera Shein):

| Campo                 | Tipo                                                  | Regla                                               |
|-----------------------|-------------------------------------------------------|-----------------------------------------------------|
| `id_shein_movimiento` | Integer, PK                                           | —                                                   |
| `id_shein_cliente`    | FK → `shein_clientes`                                 | Obligatorio                                         |
| `monto`               | Float                                                 | > 0, no puede exceder `shein_clientes.saldo`         |
| `forma_pago`          | Enum: `efectivo`, `transferencia`, `tarjeta`          | Depende de `configuracion`                          |
| `saldo_resultante`    | Float                                                 | `saldo - monto` al momento del abono                |
| `fecha`               | DateTime                                              | Autogenerado                                        |

**`shein_pedidos`** (cabecera):

| Campo             | Tipo                                         | Regla                                                                |
|-------------------|----------------------------------------------|----------------------------------------------------------------------|
| `id_shein_pedido` | Integer, PK                                  | —                                                                    |
| `id_shein_cliente`| FK → `shein_clientes`                        | Obligatorio                                                          |
| `id_shein_corte`  | FK → `shein_cortes`, nullable                | `NULL` hasta asignarse a un corte                                    |
| `estatus_pago`    | Enum: `pago_pendiente`, `pagado`, nullable   | `NULL` hasta que el corte se guarda                                  |
| `fecha`           | Date                                         | Autogenerado al crear                                                |

**`shein_pedidos_articulos`** (detalle, 1 a 4 artículos por pedido, sin alternativa):

| Campo               | Tipo                                             | Regla                                                              |
|---------------------|--------------------------------------------------|--------------------------------------------------------------------|
| `id_shein_articulo` | Integer, PK                                      | —                                                                  |
| `id_shein_pedido`   | FK → `shein_pedidos`                             | Obligatorio                                                        |
| `id_articulo`       | String(20), nullable                             | Referencia libre al ID en la app Shein. Informativo                |
| `producto`          | String(60)                                       | Obligatorio                                                        |
| `tipo_producto`     | Enum: `Nacional`, `Importado`                    | Obligatorio. Informativo en MVP                                    |
| `monto`             | Float                                            | Precio al momento de la solicitud                                  |
| `monto_vigente`     | Float, nullable                                  | Solo si el precio cambió en el corte                               |
| `estatus_articulo`  | Enum: `vigente`, `confirmado`, `cancelado`       | Default `vigente`                                                  |

**`shein_cortes`:**

| Campo           | Tipo    | Regla                                                                  |
|-----------------|---------|------------------------------------------------------------------------|
| `id_shein_corte`| Integer, PK | —                                                               |
| `fecha_corte`   | Date    | Obligatorio                                                            |
| `total_pedidos` | Integer | Pedidos con al menos 1 artículo `confirmado`. Calculado por backend    |
| `suma_pedidos`  | Float   | Suma de `monto_pedido` de pedidos incluidos. Calculado por backend     |
| `total_ticket`  | Float   | Lo pagado en caja OXXO. Captura manual                                 |
| `cupon`         | Float   | `suma_pedidos - total_ticket`. Calculado por backend al guardar        |

### Reglas de negocio

1. **Por qué `shein_clientes` es independiente:** forzar estos clientes en `clientes` introduciría dependencias sobre la cartera principal y campos que no aplican.
2. **Un `shein_pedido` tiene de 1 a 4 artículos.** Solo el primero es obligatorio al crear.
3. **Cartera de crédito.** Al guardar el corte, el `monto_pedido` de cada pedido incluido se carga al `saldo` del `shein_cliente` (`saldo += monto_pedido`). Los clientes liquidan vía abonos en `shein_movimientos` (`saldo -= monto_abono`). `estatus` derivado automáticamente de `saldo`.
4. **Ciclo de `fecha_pago_programada`.** Misma lógica que `clientes` (§2, regla 4). Se instancia y recalcula en cada abono de `shein_movimientos`.
5. **Sistema de banderas.** 🟡 Amarilla y 🔴 Roja calculadas al vuelo con la misma semántica que en `clientes`. Visuales, no bloqueantes.
6. **Variación de precios.** Cualquier variación (sube o baja) exige notificación y confirmación explícita del cliente.
7. **Resolución de `estatus_articulo` en el corte:**
   - Sin cambio de precio: `confirmado` automático.
   - Con cambio y cliente confirma: `confirmado` + `monto_vigente = nuevo_precio`.
   - Con cambio y cliente cancela: `cancelado`.
8. **Cascada de cancelación a nivel pedido:**
   - Todos `cancelado` → el pedido no recibe `id_shein_corte` ni `estatus_pago`. Saldo no impactado.
   - Al menos uno `confirmado` → `id_shein_corte` asignado, `estatus_pago = 'pago_pendiente'`, saldo cargado.
9. **`cupon`** no se calcula internamente. Se obtiene junto con `total_ticket` al pagar en OXXO. `cupon = suma_pedidos - total_ticket`.
10. **`estatus_pago`** vive en `shein_pedidos`, no en `shein_clientes`. Dos pedidos del mismo cliente en cortes distintos pueden tener estatus de pago diferente.
11. **Sin script de migración.** No existe tabla ODS para Shein. Todos los clientes se registran directamente mediante `Registrar Cliente Shein`.

---

## 7. Módulo Recargas Telefónicas

Tabla independiente, sin relaciones:

| Campo       | Tipo                                              | Regla         |
|-------------|---------------------------------------------------|---------------|
| `id_recarga`| Integer, PK                                       | —             |
| `compania`  | Enum: `Telcel`, `Movistar`, `Unefon`, `AT&T`      | Obligatorio   |
| `monto`     | Float                                             | Obligatorio   |
| `fecha`     | DateTime                                          | Autogenerado  |

Sin validación de tope de monto. Sin impacto en saldo de clientes ni inventario — solo trazabilidad de ingresos.

---

## 8. Autenticación

**`usuarios`:**

| Campo           | Tipo     | Regla                                                         |
|-----------------|----------|---------------------------------------------------------------|
| `id_usuario`    | Integer, PK | —                                                          |
| `usuario`       | String, único | 4 a 16 caracteres, sin espacios                          |
| `password_hash` | String   | bcrypt. Nunca texto plano                                     |
| `rol`           | String   | `estandar` o `admin`. Default `estandar`                      |
| `activo`        | Integer  | `1` = activo, `0` = desactivado. Default `1`                  |
| `fecha_registro`| DateTime | Autogenerado                                                  |

- Autenticación **activa** en todos los endpoints vía JWT. Sin flag `AUTH_ENABLED`.
- `password` (entrada, no persiste): 4 a 10 caracteres, al menos una mayúscula.
- Sin recuperación de contraseña por correo (sistema offline).

---

## 9. Configuración

**`configuracion`**: tabla clave-valor (`clave` PK, `valor`). Controla qué métodos de pago están activos, CLABEs registradas, zona horaria (informativa).

- Efectivo: siempre activo, no desactivable.
- Transferencia, tarjeta débito/crédito: activos por defecto, se pueden desactivar.
- MSI y vales: bloqueados por defecto, se pueden activar.

---

## 10. Módulo Consulta Finanzas

Tres consultas de solo lectura sobre datos agregados. No reemplazan la Consulta Historial
por cliente individual (Módulo Clientes) ni la Consulta de Cortes del Módulo Shein.

1. **Cortes por periodo** — suma de `movimientos` segmentada por `operacion` (`abono`, `contado`, `apartado`, `gasto`), agrupada por rango de fechas con drill-down por colonia y tipo de producto.
2. **Ventas por segmento** — distribución entre Tienda (`saldo_tienda = ingresos_tienda - egresos_tienda`), Shein (`ingresos_shein = Σ shein_movimientos`) y Recargas (`ingresos_recargas = Σ recargas`), con `total_caja = saldo_tienda + ingresos_shein + ingresos_recargas`. También expone `total_acreedores = Σ clientes.saldo + Σ shein_clientes.saldo` como snapshot al momento de consulta.
3. **Detalle tienda** — desglose de ingresos de `movimientos` por `forma_pago` (`efectivo`, `transferencia`, `tarjeta`) en un período.

> El seguimiento de `pago_pendiente` / `pagado` por corte Shein vive en Consulta de
> Cortes del Módulo Shein (Opción 6), no aquí.

---

## 11. Invariantes globales del sistema

Reglas que aplican transversalmente y que cualquier servicio nuevo debe respetar:

- El saldo de un cliente **nunca se sobrescribe** — siempre `saldo += monto` o `saldo -= monto`. Nunca `saldo = monto`. La misma regla aplica a `shein_clientes.saldo`.
- `apartados.saldo_pendiente` solo se reduce mediante abonos — nunca se ajusta por la cancelación de artículos individuales del lote.
- Ninguna operación de caja se registra sin `forma_pago`.
- Ningún cambio de `estatus` en `inventario` ocurre sin actualizar `changed_status` en la misma transacción.
- Toda fecha de negocio se almacena en `YYYY-MM-DD` (o timestamp completo cuando la tabla lo requiere) y se muestra al usuario en `DD-MM-YYYY`.
- `id_articulo_sustituye` solo se llena en artículos sustitutos de devolución. En todos los demás casos es `NULL`.
- El script `importar_precios.py` solo hace `INSERT`. Nunca borra ni sobreescribe filas existentes en `precios_catalogo`.
- `estatus_pago` (Shein) vive en `shein_pedidos`, nunca en `shein_clientes` — el estatus de cobro es por pedido, no global al cliente.
- `cupon` (Shein) siempre es `suma_pedidos - total_ticket`, con `total_ticket` capturado manualmente al pagar en OXXO.
- La tabla `cartera_vencida` no tiene llaves foráneas. Es un archivo independiente; no se relaciona con ninguna tabla del sistema.
- La bandera negra no bloquea operaciones — es visual, misma política que todas las demás banderas.
