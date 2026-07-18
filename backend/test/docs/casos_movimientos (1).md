# Casos de prueba — Movimientos

Espejo en lenguaje humano de `test/test_movimientos.py`. Mapeado a
`docs/spec/module_movimientos.md`. Si cambias una regla de negocio ahí,
actualiza el caso correspondiente aquí y el test real.

> Todo lo de Apartado (creación, consulta de abierto, cancelar artículo
> individual y cancelar el lote completo) vive en `test_apartados.py` /
> `casos_apartados.md` — separación limpia por módulo, ahora que existe
> `app/api/v1/endpoints/apartados.py`. Este archivo no cubre Apartado.

Helpers compartidos:
- `_crear_producto(...)`: inserta un producto de inventario directo vía `db_session` (Inventario no tiene endpoint todavía en el alcance de este módulo).
- `_fijar_saldo(...)`: fija el saldo de un cliente directo en la base, para partir de un estado conocido sin simular abonos previos.

Nota: `app/api/v1/endpoints/movimientos.py` expone `registrar_movimiento()`,
`obtener_movimientos_cliente()` y `cancelar_movimiento()` vía HTTP. Todos los
casos de este archivo pasan por `/api/v1/movimientos` vía `client` +
`auth_headers`.

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

> Gap cerrado en una sesión anterior: `cancelar_movimiento()` no revertía inventario al cancelar un contado.

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
