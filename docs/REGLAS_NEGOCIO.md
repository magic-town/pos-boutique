# Reglas de Negocio y Modelo de Datos — pos-boutique

> Este documento responde **qué hace el sistema y bajo qué reglas**, independientemente
> de cómo se ve la UI (eso vive en `00_FULLSTACK_DEVELOPMENT.md`) y de cómo está
> construido técnicamente (eso vive en `ARQUITECTURA.md`).
>
> **Estado:** el modelo de datos aquí descrito está implementado en
> `backend/app/models/models.py` y migrado a `pos.db` (`a1b2c3d4e5f6_esquema_inicial.py`).
> La tabla `precios_catalogo` está diseñada y cerrada pero pendiente de agregar
> a `models.py` + migración Alembic.
> El §6 (Módulo Shein) fue rediseñado — `shein_pedidos` cambia de estructura y se
> agrega `shein_pedidos_articulos`. Ambas están diseñadas y cerradas, pendientes de
> reflejarse en `models.py` + migración Alembic (esquema anterior aún vive en `pos.db`).

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
| `shein_pedidos` | Shein | Cabecera de un pedido Shein (1 a 4 artículos) |
| `shein_pedidos_articulos` | Shein | Artículos individuales de un pedido Shein (1 a 4 por pedido) |
| `shein_cortes` | Shein | Cortes periódicos que concentran pedidos y registran el `cupon` obtenido de Shein |
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
| `dia_pago_especifico` | Integer, nullable | 1-31. Obligatorio solo si `frecuencia_pago = dia_especifico_mes`. Se define una sola vez al registrar y persiste mientras la cuenta esté activa |
| `frecuencia_pago_detalle` | String(60), nullable | Obligatorio solo si `frecuencia_pago = otro`. Texto libre con el acuerdo especial |
| `ref_nombre` | String(40) | Obligatorio |
| `ref_colonia` | String(40) | Obligatorio |
| `ref_telefono` | Integer, nullable | 10 dígitos, opcional |
| `saldo` | Float | Default `0`. Deuda acumulada del cliente |
| `estatus` | Enum: `activo`, `inactivo` | Default `inactivo`. Derivado del `saldo`, siempre automático, nunca editable manualmente |
| `fecha_registro` | Date | Autogenerado al crear |
| `fecha_pago_programada` | Date, nullable | `NULL` hasta el primer abono. Ver regla de ciclo abajo |

### Reglas de negocio

1. **`estatus` es un campo derivado del `saldo`, nunca una decisión operativa.** El cliente nace `inactivo` con `saldo = 0`. Pasa a `activo` en automático en cuanto recibe y acepta un producto que impacta su `saldo`. Regresa a `inactivo` en automático en cuanto liquida su `saldo` a `0` — sin bloquear ninguna operación ni requerir acción de la operadora.
2. **Ciclo de `fecha_pago_programada` — cálculo diferenciado por `frecuencia_pago`:**
   Se instancia en el primer abono y se recalcula en cada abono subsiguiente
   (nunca al registrar al cliente). La **fórmula** de cálculo depende del tipo
   de frecuencia:
   - **`semanal`:** rodante, sin cambios. `fecha_pago_programada = fecha_abono + 7 días`,
     recalculada desde la fecha real de cada abono (no desde la fecha programada anterior).
   - **`quincenal`:** deja de ser rodante. Se fija a **fechas de calendario**: el
     día `15` de cada mes y el **último día del mes** (28, 29, 30 o 31 según
     corresponda). `fecha_pago_programada` = la próxima de esas dos fechas
     posterior a la fecha del abono.
   - **`dia_especifico_mes`:** se fija al día capturado en `dia_pago_especifico`
     al registrar al cliente. `fecha_pago_programada` = la próxima ocurrencia
     de ese día posterior a la fecha del abono. Si el día no existe en un mes
     dado (p. ej. `31` en febrero), se aplica el mismo *clamp* al último día
     del mes que usa `quincenal`.
   - **`otro`:** sin cambios — el sistema nunca calcula esta fecha;
     `fecha_pago_programada` permanece `NULL` siempre. El acuerdo se documenta
     en `frecuencia_pago_detalle`, capturado una sola vez al registrar.
   > Implementación pendiente: la fórmula vive en `movimiento_service.py`
   > (ver docs/REPORT.md, ajuste de Movimientos) — hoy solo se documenta la
   > regla y se captura el dato de origen (`dia_pago_especifico` /
   > `frecuencia_pago_detalle`) en el alta del cliente.
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
2. **Cada principal puede tener 0 o 1 alternativa**, salvo cuando
   `proveedor = Price_Shoes` en el **principal**, en cuyo caso puede tener
   **hasta 3 alternativas** (1 principal + 3 alternativas = 4 artículos en
   ese renglón). La condición se evalúa sobre el proveedor del principal, no
   de cada alternativa individual — si el principal es Price_Shoes, las
   alternativas heredan el límite de 3, sin importar su propio proveedor. La
   alternativa (o alternativas) es una buena práctica operativa (se ofrece si
   el principal no está disponible en el proveedor), pero nunca es
   obligatoria para guardar el pedido.
3. **El saldo del cliente NO se carga al registrar el pedido.** Se carga únicamente cuando el artículo se marca `en_almacen`. Solo se cobra lo que efectivamente se surtió.
4. **Resolución de `monto`:**
   - `formal` + proveedor con catálogo (`Price_Shoes`, `Pakar`, `Cklass`): lookup automático en `precios_catalogo` por `id_producto`, gana `MAX(fecha_catalogo)`. Si no existe el ID, campo queda vacío y editable.
   - `formal` + `proveedor = otro`: captura manual obligatoria.
   - `informal`: captura libre, opcional.
5. **`estatus_articulo` y su efecto en saldo:**
   - `vigente` → sin efecto en saldo.
   - `vigente` → `en_almacen`: `saldo += monto` (el artículo llegó al piso). Si el `estatus` del cliente era `inactivo`, cambia a `activo` en la misma transacción.
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
  3. `saldo_resultante = precio_producto - primer_pago`, se **suma** al saldo existente del cliente (`saldo += saldo_resultante`). Nunca se sobrescribe. Si el `estatus` del cliente era `inactivo`, cambia a `activo` en la misma transacción.
  4. `inventario.estatus` cambia a `apartado` en la misma transacción.
  5. Cancelación del apartado: `inventario.estatus` vuelve a `disponible`; el saldo pendiente se resta (el primer pago no se devuelve salvo decisión de la operadora).
- **Abono:** `saldo_resultante = saldo_actual - monto`. Rechazado si `monto > saldo_actual`. Recalcula `fecha_pago_programada` del cliente. Si `saldo_resultante` llega a `0`, el `estatus` del cliente cambia a `inactivo` en la misma transacción.
- **Gasto:** sin cliente ni producto. `descripcion` obligatoria. `saldo_resultante = NULL`. Representa salida de caja.

> El saldo agregado del negocio no es un campo en base de datos — se deriva por consulta agregada sobre `movimientos`.

---

## 6. Módulo Shein

> La boutique actúa como intermediaria: compra en la app de Shein a nombre del cliente y cobra el mismo precio, siempre de contado, sin devoluciones.
>
> **Corrección de diseño:** `shein_pedidos` deja de ser una tabla plana de un artículo por
> renglón. Adopta la misma estructura cabecera-detalle que `pedidos` / `pedidos_articulos`
> (§3): un `shein_pedido` es una cabecera con 1 a 4 artículos en `shein_pedidos_articulos`.
> A diferencia de Pedidos, **Shein no maneja el concepto de artículo alternativo** — no
> aplica `rol` ni `id_articulo_principal`.

### Modelo de datos

**`shein_clientes`** (independiente de `clientes` — sin saldo, sin garante, sin frecuencia de pago):

| Campo | Tipo | Regla |
|---|---|---|
| `id_shein_cliente` | Integer, PK | — |
| `nombre` | String(20) | Obligatorio |
| `colonia` | String(12) | Obligatorio |
| `telefono` | Integer | 10 dígitos, obligatorio |

**`shein_pedidos`** (cabecera — equivalente a `pedidos` en §3):

| Campo | Tipo | Regla |
|---|---|---|
| `id_shein_pedido` | Integer, PK | Nunca aparece en UI |
| `id_shein_cliente` | FK → `shein_clientes` | Obligatorio |
| `id_shein_corte` | FK → `shein_cortes`, nullable | `NULL` hasta asignarse a un corte |
| `estatus_pago` | Enum: `pago_pendiente`, `pagado`, nullable | `NULL` hasta que el corte se guarda. Ver regla 5 |
| `fecha` | Date | Autogenerado al crear |

**`shein_pedidos_articulos`** (detalle, 1 a 4 artículos por pedido, sin alternativa):

| Campo | Tipo | Regla |
|---|---|---|
| `id_shein_articulo` | Integer, PK | Nunca aparece en UI |
| `id_shein_pedido` | FK → `shein_pedidos` | Obligatorio |
| `id_articulo` | String(20), nullable | Referencia libre al ID del artículo en la app Shein. Informativo, sin catálogo ni FK real |
| `producto` | String(60) | Obligatorio. Descripción libre del artículo |
| `tipo_producto` | Enum: `Nacional`, `Importado` | Obligatorio. Informativo, sin impacto operativo en MVP |
| `monto` | Float | Obligatorio. Precio en la app al momento en que el cliente solicita el artículo |
| `monto_vigente` | Float, nullable | Se llena únicamente si el precio cambió al momento del corte (subida o bajada) |
| `estatus_articulo` | Enum: `vigente`, `confirmado`, `cancelado` | Default `vigente`. Ver regla 6 |

**`shein_cortes`:**

| Campo | Tipo | Regla |
|---|---|---|
| `id_shein_corte` | Integer, PK | — |
| `fecha_corte` | Date | Obligatorio |
| `total_pedidos` | Integer | Cantidad de `shein_pedidos` incluidos en el corte. Calculado por backend |
| `suma_pedidos` | Float | Suma de los montos confirmados de todos los pedidos incluidos (ver regla 8). Calculado por backend |
| `total_ticket` | Float | Lo efectivamente pagado en caja OXXO. Captura manual, dato de Shein |
| `cupon` | Float | `suma_pedidos - total_ticket`. Calculado por backend al guardar |

> `porcentaje_bono` / `bono_monto` del diseño anterior quedan obsoletos: el bono
> (ahora `cupon`) no se estima con un porcentaje interno, lo determina Shein y se
> obtiene junto con `total_ticket` al pagar en OXXO.

### Reglas de negocio

1. **Por qué `shein_clientes` es independiente:** forzar estos clientes en `clientes` introduciría campos obligatorios que no aplican (garante, saldo, frecuencia de pago) y contaminaría la cartera de crédito real.
2. **Un `shein_pedido` tiene de 1 a 4 artículos.** Solo el primero es obligatorio al crear; los demás se pueden agregar mientras el pedido siga editable (`id_shein_corte IS NULL`, con al menos un artículo en `vigente`).
3. **Sin saldo, sin cartera de crédito.** A diferencia de Pedidos, ningún artículo Shein impacta el `saldo` de ningún cliente en ningún momento del ciclo — el cliente Shein siempre paga de contado en OXXO. `estatus_pago` en `shein_pedidos` es el único mecanismo de seguimiento de cobro.
4. **Variación de precios (corregido):** ya sea que el precio **baje o suba** entre el momento del pedido y el momento del corte, se notifica al cliente y este debe confirmar el artículo con el precio actualizado. No existe el caso "la tienda absorbe la diferencia en silencio" del diseño anterior.
5. **Resolución de `estatus_articulo` en el corte:**
   - Si el precio no cambió: el artículo pasa automáticamente a `confirmado` (con `monto_vigente = NULL`, se usa `monto`).
   - Si el precio cambió y el cliente confirma: `estatus_articulo = 'confirmado'`, `monto_vigente` se llena con el nuevo precio.
   - Si el precio cambió y el cliente cancela: `estatus_articulo = 'cancelado'`.
6. **Cascada de cancelación a nivel pedido:**
   - Si **todos** los artículos de un `shein_pedido` quedan `cancelado`, el pedido completo se considera cancelado: no se le asigna `id_shein_corte` ni `estatus_pago`. Sin ningún otro impacto en la operación.
   - Si el pedido conserva **al menos un** artículo `confirmado`, el pedido continúa: se le asigna `id_shein_corte` y `estatus_pago = 'pago_pendiente'`, usando solo los artículos `confirmado` para los cálculos de monto.
7. **Ciclo de `estatus_pago`:** al guardar un `shein_corte`, todos los `shein_pedidos` incluidos (con al menos un artículo `confirmado`) pasan de `NULL` a `pago_pendiente`. Conforme cada cliente paga en OXXO, su pedido pasa individualmente a `pagado`. `estatus_pago` vive en `shein_pedidos`, no en `shein_clientes` ni en `shein_cortes` — dos pedidos del mismo cliente en cortes distintos pueden tener estatus de pago diferentes.
8. **Cálculo de montos:**
   - `monto_pedido` (por pedido): suma de `COALESCE(monto_vigente, monto)` de los artículos `confirmado` de ese pedido. No es una columna almacenada — se deriva por consulta.
   - `suma_pedidos` (por corte): suma de `monto_pedido` de todos los pedidos incluidos en el corte. Sí se almacena en `shein_cortes`, igual que `bono_monto` en el diseño anterior.
9. **`cupon` no se calcula internamente.** Shein lo determina externamente y la tienda lo obtiene junto con `total_ticket` al momento de pagar en caja OXXO — ambos se capturan en la misma acción de guardar el corte. `cupon = suma_pedidos - total_ticket`.
10. **El pago de la tienda al proveedor (OXXO) es informativo y no se registra en el sistema** — no existe un estatus "confirmado → pagado" a nivel `shein_corte`. Lo único que el sistema rastrea después de `fecha_corte` es el cobro al cliente (`estatus_pago` en `shein_pedidos`).

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

Tres consultas de solo lectura sobre datos agregados (no reemplazan la Consulta Historial por cliente individual ni la Consulta de Cortes del Módulo Shein — ver §6):

1. **Ventas totales por período** — suma de `movimientos` (excluyendo `gasto`) agrupada por operación, con total consolidado.
2. **Ventas por segmento** — distribución entre Caja (movimientos), Shein y Recargas en un período.
3. **Cartera de clientes por segmento** — clientes con saldo activo agrupados por colonia, con saldo total y promedio.

> El seguimiento de `pago_pendiente` / `pagado` por corte Shein vive en su propia
> consulta dentro del Módulo Shein (Opción 5 — Consulta de Cortes), no aquí — es
> información operativa del módulo, no un agregado transversal del negocio.

---

## 11. Invariantes globales del sistema

Reglas que aplican transversalmente y que cualquier servicio nuevo debe respetar:

- El saldo de un cliente **nunca se sobrescribe** — siempre `saldo += monto` o `saldo -= monto`. Nunca `saldo = monto`.
- Ninguna operación de caja se registra sin `forma_pago`.
- Ningún cambio de `estatus` en `inventario` ocurre sin actualizar `changed_status` en la misma transacción.
- Toda fecha de negocio se almacena en `YYYY-MM-DD` (o timestamp completo cuando la tabla lo requiere) y se muestra al usuario en `DD-MM-YYYY`.
- `id_articulo_sustituye` solo se llena en artículos sustitutos de devolución. En todos los demás casos es `NULL`.
- El script `importar_precios.py` solo hace `INSERT`. Nunca borra ni sobreescribe filas existentes en `precios_catalogo`.
- `estatus_pago` (Shein) vive en `shein_pedidos`, nunca en `shein_clientes` — el estatus de cobro es por pedido, no global al cliente.
- `cupon` (Shein) nunca se calcula por porcentaje interno — siempre se deriva de `suma_pedidos - total_ticket`, con `total_ticket` capturado manualmente al pagar en OXXO.
