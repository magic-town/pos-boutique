# Casos de prueba — Movimientos

Espejo en lenguaje humano de `test/test_movimientos.py`. Mapeado a
`docs/FULL_STACK/module_movimientos.md`. Si cambias una regla de negocio ahí,
actualiza el caso correspondiente aquí y el test real.

Helpers compartidos:
- `_crear_producto(...)`: inserta un producto de inventario directo vía `db_session` (Inventario no tiene endpoint todavía en el alcance de este módulo).
- `_fijar_saldo(...)`: fija el saldo de un cliente directo en la base, para partir de un estado conocido sin simular abonos previos.
- `_crear_apartado_simple(...)`: atajo para crear un apartado de 1 solo artículo, llamando directo a `crear_apartado()` (Apartado no tiene endpoint HTTP todavía).
- `_movimiento_de_apartado(...)`: busca el movimiento de caja asociado a un apartado, para poder cancelarlo vía `DELETE /movimientos/{id}/cancelar`.

Nota: `app/api/v1/endpoints/movimientos.py` solo expone `registrar_movimiento()`,
`obtener_movimientos_cliente()` y `cancelar_movimiento()` vía HTTP. Los casos
de creación de Apartado llaman al service directo con `db_session`; el resto
pasa por `/api/v1/movimientos` vía `client` + `auth_headers`.

---

## Contado

### `test_con_producto_descuenta_stock_sin_agotar`
**Qué prueba:** un contado con producto de inventario descuenta 1 de stock sin agotarlo.
**Pasos:**
1. Crear un producto con stock=3.
2. Registrar un contado por $500 con ese `id_producto`.
3. Confirmar 201, `saldo_resultante` nulo (contado no toca saldo de cliente), y que el `id_producto` de la respuesta coincide.
4. Confirmar que el stock bajó a 2 y el producto sigue `disponible`.

### `test_agota_stock_pasa_a_vendido`
**Qué prueba:** cuando el contado deja el stock en 0, el producto pasa a `vendido` automáticamente.
**Pasos:**
1. Crear un producto con stock=1.
2. Registrar el contado.
3. Confirmar que el stock quedó en 0 y el estatus en `vendido`.

### `test_sin_coincidencia_en_inventario_captura_manual`
**Qué prueba:** un `id_producto` que no existe en inventario no rompe el contado — se captura manual (monto libre), sin ligar a inventario.
**Pasos:**
1. Registrar un contado con un `id_producto` inventado (999999) y `monto`=350.
2. Confirmar 201, `saldo_resultante` nulo, y que el `id_producto` de la respuesta es nulo (no se persiste el id enviado si no hubo match).

### `test_monto_no_positivo_rechaza`
**Qué prueba:** el monto de un contado debe ser positivo.
**Pasos:**
1. Registrar un contado con `monto`=0.
2. Debe **rechazarse (422)**.

---

## Cancelar Contado — revierte inventario

> Gap cerrado en esta sesión: `cancelar_movimiento()` no revertía inventario al cancelar un contado.

### `test_regresa_stock`
**Qué prueba:** cancelar un contado regresa el stock que había descontado.
**Pasos:**
1. Crear un producto con stock=2.
2. Registrar el contado.
3. Cancelar el movimiento.
4. Confirmar que el stock volvió a 2.

### `test_reactiva_producto_que_habia_quedado_vendido`
**Qué prueba:** si el contado había dejado al producto en `vendido` (stock llegó a 0), cancelarlo lo reactiva.
**Pasos:**
1. Crear un producto con stock=1.
2. Registrar el contado (precondición: el producto queda `vendido`).
3. Cancelar el movimiento.
4. Confirmar que el stock es 1 y el estatus `disponible`.

### `test_reactiva_preservando_descuento`
**Qué prueba:** al reactivar un producto cancelado, si tenía un descuento activo (`precio_descuento` no nulo), regresa a `disponible_c/descuento`, no a `disponible` a secas.
**Pasos:**
1. Crear un producto con stock=1 y `precio_descuento`=400.
2. Registrar el contado por $400.
3. Cancelar el movimiento.
4. Confirmar que el estatus quedó en `disponible_c/descuento`.

---

## Abono

### `test_descuenta_saldo_y_saldo_resultante`
**Qué prueba:** un abono resta del saldo del cliente, y el `saldo_resultante` de la respuesta ya refleja el saldo actualizado.
**Pasos:**
1. Fijar el saldo del cliente en $1000.
2. Registrar un abono de $300.
3. Confirmar 201 y `saldo_resultante`=700.
4. Confirmar en la base que `cliente.saldo`=700.

### `test_supera_saldo_rechaza`
**Qué prueba:** no se puede abonar más de lo que el cliente debe.
**Pasos:**
1. Fijar el saldo en $100.
2. Intentar abonar $500.
3. Debe **rechazarse (422)**.

### `test_sin_cliente_rechaza`
**Qué prueba:** un abono siempre requiere cliente.
**Pasos:**
1. Registrar un abono sin `id_cliente`.
2. Debe **rechazarse (422)**.

### `test_cliente_inexistente_404`
**Qué prueba:** abonar a un cliente que no existe falla.
**Pasos:**
1. Registrar un abono con `id_cliente`=999999.
2. Debe **rechazarse (404)**.

---

## Cancelar Abono

### `test_revierte_saldo_al_valor_anterior`
**Qué prueba:** cancelar un abono regresa el saldo del cliente al valor que tenía antes.
**Pasos:**
1. Fijar el saldo en $1000.
2. Registrar un abono de $300 (saldo baja a $700).
3. Cancelar ese movimiento.
4. Confirmar que el saldo regresó a $1000.

### `test_solo_se_puede_cancelar_el_ultimo_movimiento`
**Qué prueba:** no se puede cancelar un abono si después hubo otro movimiento del mismo cliente — solo el último es cancelable.
**Pasos:**
1. Fijar el saldo en $1000.
2. Registrar un primer abono de $100.
3. Registrar un segundo abono de $100.
4. Intentar cancelar el primero.
5. Debe **rechazarse (409)**.

---

## Gasto

### `test_sin_cliente_ni_producto`
**Qué prueba:** un gasto no lleva cliente ni afecta el saldo de nadie.
**Pasos:**
1. Registrar un gasto de $250 con descripción "Compra de bolsas".
2. Confirmar 201, `id_cliente` nulo y `saldo_resultante` nulo.

### `test_con_cliente_rechaza`
**Qué prueba:** un gasto no puede llevar cliente asociado.
**Pasos:**
1. Intentar registrar un gasto mandando un `id_cliente` válido.
2. Debe **rechazarse (422)**.

### `test_sin_descripcion_permite`
**Qué prueba:** la descripción de un gasto es opcional, no obligatoria (confirmado con el usuario como comportamiento intencional).
**Pasos:**
1. Registrar un gasto de $80 sin mandar descripción.
2. Confirmar 201 y que `descripcion` queda en `null`.

---

## Apartado — creación

> Sin endpoint HTTP todavía: estos casos llaman directo a `crear_apartado()` vía `db_session`.

### `test_un_articulo_manual_sin_id_producto`
**Qué prueba:** crear un apartado con 1 solo artículo capturado a mano (sin `id_producto`) calcula bien el saldo pendiente.
**Pasos:**
1. Crear un apartado con 1 artículo de $450 y primer pago de $100.
2. Confirmar `saldo_pendiente`=350, `estatus`='abierto', 1 artículo con ese precio y sin `id_producto`.

### `test_varios_articulos_suma_precios`
**Qué prueba:** con varios artículos, el saldo pendiente se calcula sobre la suma de todos los precios, no solo el primero.
**Pasos:**
1. Crear un producto de $300 en inventario y agregar un artículo manual de $200.
2. Crear el apartado con esos 2 artículos y primer pago de $100.
3. Confirmar `saldo_pendiente`=400 ((300+200)-100) y que trae los 2 artículos.
4. Confirmar que el producto de inventario quedó en estatus `apartado`.

### `test_producto_con_coincidencia_autollena_precio_venta`
**Qué prueba:** si el `id_producto` tiene coincidencia en inventario, el precio real del inventario gana sobre cualquier precio manual capturado (mismo criterio que Pedidos).
**Pasos:**
1. Crear un producto con `precio_venta`=777.
2. Crear el apartado mandando ese `id_producto` con un `precio_producto` manual absurdo (1.0).
3. Confirmar que el precio guardado es 777, no 1.

### `test_monto_primer_pago_menor_a_100_rechaza`
**Qué prueba:** el primer pago del apartado tiene un mínimo de $100, para todo el lote (no por artículo).
**Pasos:**
1. Intentar construir un `ApartadoCreate` con `monto_primer_pago`=50.
2. Debe **rechazarse a nivel de schema** (`ValueError`).

### `test_saldo_resultante_es_saldo_total_no_delta`
**Qué prueba:** regresión de un bug ya corregido — el `saldo_resultante` guardado en el movimiento de un apartado debe ser el saldo TOTAL del cliente tras la operación, no el delta que aportó el lote.
**Pasos:**
1. Fijar el saldo del cliente en $500.
2. Crear un apartado con 1 artículo de $300 y primer pago de $100 (`saldo_pendiente`=200).
3. Confirmar que el saldo del cliente ahora es $700 (500 previo + 200 del lote).
4. Confirmar que el movimiento asociado guardó `saldo_resultante`=700 (el total), no 200 (el delta).

### `test_cliente_ya_tiene_apartado_abierto_rechaza`
**Qué prueba:** un cliente no puede tener 2 apartados abiertos a la vez — debe liquidarse o cancelarse el que ya tiene antes de registrar otro.
**Pasos:**
1. Crear un apartado simple para el cliente.
2. Intentar crear un segundo apartado para el mismo cliente.
3. Debe **rechazarse (409)**.

---

## Apartado — cancelar

> Gap cerrado en esta sesión: `cancelar_movimiento()` no contemplaba que el último movimiento del cliente fuera un apartado.

### `test_cancela_lote_completo_varios_articulos`
**Qué prueba:** cancelar el movimiento de un apartado de varios artículos cancela el lote entero de una sola vez — cabecera, todos los artículos vigentes, y regresa cada producto a inventario.
**Pasos:**
1. Crear un apartado con 2 productos de inventario ($300 y $200).
2. Cancelar el movimiento asociado.
3. Confirmar 200.
4. Confirmar que la cabecera (`Apartado.estatus`) quedó `cancelado`.
5. Confirmar que ambos artículos quedaron `cancelado`.
6. Confirmar que ambos productos regresaron a `disponible` en inventario.

### `test_revierte_saldo_del_cliente`
**Qué prueba:** cancelar el movimiento de un apartado también revierte lo que ese apartado había sumado al saldo del cliente.
**Pasos:**
1. Fijar el saldo del cliente en $500.
2. Crear un apartado de $300 con primer pago de $100 (saldo sube a $700).
3. Cancelar el movimiento.
4. Confirmar que el saldo regresó a $500.

### `test_no_permite_cancelar_si_ya_hubo_abono`
**Qué prueba:** si ya se le abonó algo al apartado, ya no se puede deshacer como si nunca hubiera pasado — deja de ser el "último movimiento" del cliente.
**Pasos:**
1. Crear un apartado.
2. Registrar un abono de $50 sobre ese mismo cliente.
3. Intentar cancelar el movimiento original del apartado.
4. Debe **rechazarse (409)**.

### `test_no_reabre_articulos_ya_cancelados_manualmente`
**Qué prueba:** si el cliente ya había cancelado 1 de los 2 artículos del lote a mano (vía cancelar artículo individual) antes de deshacer todo el movimiento, ese artículo no se vuelve a tocar — solo los que seguían `vigente` entran a la cancelación masiva.
**Pasos:**
1. Crear un apartado con 2 productos.
2. Cancelar manualmente el artículo del primer producto.
3. Cancelar el movimiento completo del apartado.
4. Confirmar 200 y que ambos artículos (el que ya estaba cancelado y el que seguía vigente) terminan en estatus `cancelado`.

---

## Historial y cancelar — casos generales

### `test_get_historial_por_cliente`
**Qué prueba:** se puede consultar el historial de movimientos de un cliente específico.
**Pasos:**
1. Fijar el saldo del cliente en $200.
2. Registrar un abono de $50.
3. Consultar el historial filtrando por ese `id_cliente`.
4. Confirmar 200, al menos 1 resultado, y que todos los movimientos devueltos pertenecen a ese cliente.

### `test_cancelar_movimiento_inexistente_404`
**Qué prueba:** cancelar un movimiento que no existe falla.
**Pasos:**
1. Intentar cancelar el id 999999.
2. Debe **rechazarse (404)**.
