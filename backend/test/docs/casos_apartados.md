# Casos de prueba — Apartado

Espejo en lenguaje humano de `test/test_apartados.py`. Mapeado a
`docs/spec/module_movimientos.md` (sección "Módulo Apartado") y
`REGLAS_NEGOCIO.md §5`. Si cambias una regla de negocio ahí, actualiza el
caso correspondiente aquí y el test real.

Apartado no es un módulo independiente — es una operación del Panel
Principal, igual que Contado/Abono/Gasto (ver `casos_movimientos.md`), pero
con su propia cabecera+detalle (`apartados` / `apartados_articulos`) y su
propio endpoint (`app/api/v1/endpoints/apartados.py`), por eso vive en su
propio archivo de casos.

Helpers compartidos:
- `_crear_producto(...)`: inserta un producto de inventario directo vía `db_session`.
- `_fijar_saldo(...)`: fija el saldo de un cliente directo en la base, para partir de un estado conocido.
- `_crear_apartado_simple(...)`: atajo a nivel service — llama directo a `crear_apartado()` con 1 solo artículo.
- `_payload_apartado(...)`: arma el body JSON de `POST /apartados` para los casos que pegan vía HTTP.
- `_movimiento_de_apartado(...)`: busca el movimiento de caja asociado a un apartado, para poder cancelarlo vía `DELETE /movimientos/{id}/cancelar`.

`app/api/v1/endpoints/apartados.py` expone 3 rutas:
- `POST /apartados` — crear el lote.
- `GET /apartados/abierto?id_cliente=` — consultar el apartado abierto de un cliente.
- `DELETE /apartados/articulos/{id_apartado_articulo}/cancelar` — cancelar un artículo suelto del lote.

La cancelación del **lote completo** (deshacer el primer pago como si nunca
hubiera pasado) no vive en `/apartados` — se hace deshaciendo el movimiento
de caja que lo originó, vía `DELETE /movimientos/{id}/cancelar` (mismo
mecanismo que cancelar un abono o un contado). Por eso esos casos, aunque
viven en este archivo por ser 100% de Apartado, pegan contra
`/api/v1/movimientos`.

---

## Validaciones de schema

### `test_articulo_sin_id_producto_ni_precio_rechaza`
**Qué prueba:** sin `id_producto` no hay lookup posible en inventario — el precio manual pasa a ser obligatorio.
**Pasos:**
1. Construir un `ApartadoArticuloCreate` sin `id_producto` ni `precio_producto`.
2. Debe **rechazarse a nivel de schema** (`ValueError`).

### `test_articulo_con_id_producto_sin_precio_manual_es_valido`
**Qué prueba:** con `id_producto` presente, `precio_producto` puede venir `None` a nivel de schema — la resolución real ocurre en el service.
**Pasos:**
1. Construir un `ApartadoArticuloCreate` con `id_producto`=1 y `precio_producto`=`None`.
2. Confirmar que el schema se construye sin error y conserva ambos valores.

### `test_lista_articulos_vacia_rechaza`
**Qué prueba:** un apartado necesita al menos 1 artículo.
**Pasos:**
1. Construir un `ApartadoCreate` con `articulos`=[].
2. Debe **rechazarse a nivel de schema** (`ValueError`).

---

## Resolución de precio (crear_apartado — nivel service)

### `test_id_producto_sin_match_sin_precio_manual_rechaza`
**Qué prueba:** un `id_producto` que no existe en inventario y sin `precio_producto` manual no tiene forma de resolver el precio.
**Pasos:**
1. Crear un apartado con un artículo `id_producto`=999999 (inexistente) y sin precio manual.
2. Debe **rechazarse (422)**.

### `test_producto_no_disponible_usa_precio_manual_y_no_se_liga`
**Qué prueba:** un `id_producto` que existe pero ya está `vendido` no cuenta como coincidencia (`_DISPONIBLES`). Si se manda precio manual, se respeta, y el artículo del apartado NO queda ligado a ese `id_producto` — para no terminar apartando un producto ya vendido.
**Pasos:**
1. Crear un producto en estatus `vendido`.
2. Crear un apartado con ese `id_producto` y `precio_producto` manual=250.
3. Confirmar que el precio guardado es 250 y que el artículo del apartado quedó con `id_producto` nulo.
4. Confirmar que el producto de inventario no se tocó (sigue `vendido`).

---

## Apartado — creación (nivel service)

> Reglas de negocio de `crear_apartado()`, llamada directa a `db_session`.

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
**Qué prueba:** el `saldo_resultante` guardado en el movimiento de un apartado debe ser el saldo TOTAL del cliente tras la operación, no el delta que aportó el lote.
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

## Apartado — creación (HTTP, `POST /apartados`)

> Mismas reglas de arriba, verificadas ahora en el contrato HTTP: status codes, forma del body y serialización de la respuesta.

### `test_crea_y_devuelve_201`
**Qué prueba:** el endpoint crea el apartado y devuelve 201 con el body esperado.
**Pasos:**
1. `POST /apartados` con 1 artículo manual de $450 y primer pago de $100.
2. Confirmar 201, `id_cliente` correcto, `saldo_pendiente`=350, `estatus`='abierto', 1 artículo con `precio_producto`=450.

### `test_varios_articulos_suma_precios`
**Qué prueba:** igual que el caso equivalente a nivel service, pero por HTTP.
**Pasos:**
1. Crear un producto de $300 en inventario.
2. `POST /apartados` con ese producto + un artículo manual de $200, primer pago de $100.
3. Confirmar 201 y `saldo_pendiente`=400.

### `test_monto_primer_pago_menor_a_100_rechaza_422`
**Qué prueba:** la validación del mínimo de $100 también se aplica al pegarle al endpoint (no solo construyendo el schema en memoria).
**Pasos:**
1. `POST /apartados` con `monto_primer_pago`=50.
2. Debe **rechazarse (422)**.

### `test_cliente_ya_tiene_apartado_abierto_rechaza_409`
**Qué prueba:** el rechazo de un segundo apartado abierto también aplica por HTTP.
**Pasos:**
1. `POST /apartados` una vez (201).
2. Repetir el mismo `POST /apartados` para el mismo cliente.
3. El segundo debe **rechazarse (409)**.

### `test_cliente_inexistente_404`
**Qué prueba:** crear un apartado para un cliente que no existe falla.
**Pasos:**
1. `POST /apartados` con `id_cliente`=999999.
2. Debe **rechazarse (404)**.

---

## Apartado — consultar abierto (nivel service)

> `obtener_apartado_abierto()`, usado por Abono para mostrar `saldo_pendiente` en vivo al buscar cliente.

### `test_devuelve_el_apartado_abierto_del_cliente`
**Qué prueba:** si el cliente tiene un apartado abierto, la función lo encuentra.
**Pasos:**
1. Crear un apartado simple para el cliente.
2. Llamar `obtener_apartado_abierto()`.
3. Confirmar que devuelve ese mismo apartado.

### `test_none_si_no_tiene_apartado_abierto`
**Qué prueba:** si el cliente no tiene apartado abierto, la función devuelve `None` (no truena).
**Pasos:**
1. Llamar `obtener_apartado_abierto()` sobre un cliente sin apartados.
2. Confirmar que devuelve `None`.

---

## Apartado — consultar abierto (HTTP, `GET /apartados/abierto`)

### `test_devuelve_200_con_saldo_pendiente`
**Qué prueba:** el endpoint expone el mismo dato que el service, en formato HTTP.
**Pasos:**
1. Crear un apartado de $300 con primer pago de $100 (`saldo_pendiente`=200).
2. `GET /apartados/abierto?id_cliente=...`.
3. Confirmar 200, `id_apartado` correcto y `saldo_pendiente`=200.

### `test_404_si_no_tiene_apartado_abierto`
**Qué prueba:** consultar el apartado abierto de un cliente que no tiene ninguno responde 404, no una lista vacía ni un 200 con `null` — es el estado normal de la mayoría de los clientes, pero el contrato es explícito.
**Pasos:**
1. `GET /apartados/abierto?id_cliente=...` para un cliente sin apartado abierto.
2. Debe **responder (404)**.

---

## Apartado — cancelar artículo individual (nivel service)

> `cancelar_articulo_apartado()`, REGLAS_NEGOCIO.md §5 regla 6.

### `test_no_ajusta_saldo_pendiente_ni_saldo_cliente`
**Qué prueba:** la deuda permanece — cancelar 1 artículo del lote no reduce lo que el cliente debe ni lo que ya se le cargó.
**Pasos:**
1. Crear un apartado con 2 productos ($300 y $200).
2. Anotar `saldo_pendiente` del apartado y `saldo` del cliente antes de cancelar.
3. Cancelar el artículo del primer producto.
4. Confirmar que `saldo_pendiente` y `saldo` del cliente no cambiaron, y que el apartado sigue `abierto`.

### `test_regresa_producto_a_disponible`
**Qué prueba:** cancelar un artículo con `id_producto` ligado regresa ese producto a `disponible` en inventario.
**Pasos:**
1. Crear un apartado de 1 artículo ligado a un producto de inventario.
2. Cancelar ese artículo.
3. Confirmar que el producto quedó `disponible`.

### `test_rechaza_cancelar_articulo_ya_cancelado`
**Qué prueba:** solo se pueden cancelar artículos en estatus `vigente` — no se puede cancelar dos veces el mismo.
**Pasos:**
1. Crear un apartado de 1 artículo y cancelarlo.
2. Intentar cancelarlo otra vez.
3. Debe **rechazarse (400)**.

### `test_404_si_articulo_no_existe`
**Qué prueba:** cancelar un `id_apartado_articulo` que no existe falla.
**Pasos:**
1. Llamar `cancelar_articulo_apartado()` con un id inventado (999999).
2. Debe **rechazarse (404)**.

### `test_lote_sigue_abierto_aunque_se_cancelen_todos_los_articulos_uno_por_uno`
**Qué prueba:** el lote nunca se da de baja como unidad por esta vía — sigue `abierto` hasta que `saldo_pendiente` llegue a 0 vía abonos, sin importar cuántos artículos se hayan cancelado.
**Pasos:**
1. Crear un apartado con 2 productos.
2. Cancelar ambos artículos, uno por uno.
3. Confirmar que el apartado (cabecera) sigue `abierto`.
4. Confirmar que ambos artículos quedaron `cancelado`.

---

## Apartado — cancelar artículo individual (HTTP, `DELETE /apartados/articulos/{id}/cancelar`)

### `test_cancela_y_regresa_producto_a_disponible`
**Qué prueba:** el endpoint cancela el artículo y refleja el cambio tanto en la respuesta como en inventario.
**Pasos:**
1. Crear un apartado de 1 artículo ligado a un producto de inventario.
2. `DELETE /apartados/articulos/{id}/cancelar`.
3. Confirmar 200 y `estatus_articulo`='cancelado' en la respuesta.
4. Confirmar que el producto quedó `disponible` en inventario.

### `test_rechaza_cancelar_articulo_ya_cancelado_400`
**Qué prueba:** el rechazo de doble cancelación también aplica por HTTP.
**Pasos:**
1. Crear un apartado de 1 artículo y cancelarlo vía endpoint.
2. Repetir el mismo `DELETE .../cancelar`.
3. El segundo debe **rechazarse (400)**.

### `test_articulo_inexistente_404`
**Qué prueba:** cancelar un artículo que no existe falla también por HTTP.
**Pasos:**
1. `DELETE /apartados/articulos/999999/cancelar`.
2. Debe **rechazarse (404)**.

---

## Apartado — cancelar el lote completo (vía `DELETE /movimientos/{id}/cancelar`)

> Gap cerrado en una sesión anterior: `cancelar_movimiento()` no contemplaba que el último movimiento del cliente fuera un apartado. No existe, ni tiene por qué existir, una puerta de cancelación de lote dentro de `/apartados` — el lote se deshace deshaciendo el movimiento de caja que lo originó, mismo criterio que abono/contado.

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
**Qué prueba:** si el cliente ya había cancelado 1 de los 2 artículos del lote a mano (vía `DELETE /apartados/articulos/{id}/cancelar`) antes de deshacer todo el movimiento, ese artículo no se vuelve a tocar — solo los que seguían `vigente` entran a la cancelación masiva.
**Pasos:**
1. Crear un apartado con 2 productos.
2. Cancelar manualmente el artículo del primer producto.
3. Cancelar el movimiento completo del apartado.
4. Confirmar 200 y que ambos artículos (el que ya estaba cancelado y el que seguía vigente) terminan en estatus `cancelado`.
