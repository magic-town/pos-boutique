# Casos de prueba — Apartado

Espejo en lenguaje humano de `test/test_apartados.py`. Mapeado a
`docs/FULL_STACK/module_movimientos.md` (Apartado no es módulo independiente,
ver ese spec). Si cambias una regla de negocio ahí, actualiza el caso
correspondiente aquí y el test real.

Este archivo **no duplica** los casos de Apartado que ya viven en
`casos_movimientos.md` / `test_movimientos.py` (suma de precios de varios
artículos, autollenado de `precio_venta`, mínimo de $100, `saldo_resultante`
= saldo total, rechazo de un segundo apartado abierto, y cancelación del
lote completo vía `cancelar_movimiento()`). Cubre lo que esos no cubren:
validaciones de schema por artículo, resolución de precio sin coincidencia
en inventario, `obtener_apartado_abierto()`, y el ciclo completo de
`cancelar_articulo_apartado()`.

Helpers compartidos:
- `_crear_producto(...)`: inserta un producto de inventario directo vía `db_session`.
- `_crear_apartado_simple(...)`: atajo para crear un apartado de 1 solo artículo, llamando directo a `crear_apartado()`.

Nota: no existe endpoint HTTP para `crear_apartado()` ni para
`cancelar_articulo_apartado()` todavía — todos los casos llaman directo al
service con `db_session`.

---

## Validaciones de schema

### `test_articulo_sin_id_producto_ni_precio_rechaza`
**Qué prueba:** sin `id_producto` no hay lookup posible en inventario — el precio manual pasa a ser obligatorio.
**Pasos:**
1. Intentar construir un `ApartadoArticuloCreate` sin `id_producto` ni `precio_producto`.
2. Debe **rechazarse** (`ValueError`).

### `test_articulo_con_id_producto_sin_precio_manual_es_valido`
**Qué prueba:** con `id_producto` presente, `precio_producto` puede venir vacío a nivel de schema — la resolución real (¿hay coincidencia en inventario?) ocurre después, en el service.
**Pasos:**
1. Construir un `ApartadoArticuloCreate` con `id_producto`=1 y `precio_producto`=None.
2. Confirmar que se construye sin error.

### `test_lista_articulos_vacia_rechaza`
**Qué prueba:** un apartado necesita al menos 1 artículo.
**Pasos:**
1. Intentar construir un `ApartadoCreate` con `articulos=[]`.
2. Debe **rechazarse** (`ValueError`).

---

## Resolución de precio (con/sin coincidencia en inventario)

### `test_id_producto_sin_match_sin_precio_manual_rechaza`
**Qué prueba:** un `id_producto` que no existe en inventario y sin `precio_producto` manual no tiene forma de resolver el precio.
**Pasos:**
1. Intentar crear un apartado con un `id_producto` inventado (999999) y sin precio manual.
2. Debe **rechazarse (422)**.

### `test_producto_no_disponible_usa_precio_manual_y_no_se_liga`
**Qué prueba:** un `id_producto` que existe pero ya está `vendido` no cuenta como coincidencia. Si se manda un precio manual, se respeta — pero el artículo del apartado no queda ligado a ese producto, para no terminar apartando algo que ya se vendió.
**Pasos:**
1. Crear un producto en estatus `vendido`.
2. Crear un apartado mandando ese `id_producto` junto con un `precio_producto` manual de $250.
3. Confirmar que el precio guardado es 250 y que el artículo del apartado quedó **sin** `id_producto` ligado.
4. Confirmar que el producto original sigue `vendido` (no se tocó).

---

## Consultar apartado abierto

### `test_devuelve_el_apartado_abierto_del_cliente`
**Qué prueba:** `obtener_apartado_abierto()` encuentra el apartado abierto de un cliente (usado por Abono para mostrar `saldo_pendiente` en vivo).
**Pasos:**
1. Crear un apartado simple para el cliente.
2. Consultar `obtener_apartado_abierto()`.
3. Confirmar que devuelve ese mismo apartado.

### `test_none_si_no_tiene_apartado_abierto`
**Qué prueba:** si el cliente no tiene ningún apartado abierto, la consulta devuelve vacío.
**Pasos:**
1. Consultar `obtener_apartado_abierto()` para un cliente sin apartados.
2. Confirmar que devuelve `None`.

---

## Cancelar artículo de un apartado

> REGLAS_NEGOCIO.md §5, regla 6: cancelar 1 artículo del lote no afecta
> `saldo_pendiente` ni `clientes.saldo` — la deuda permanece. El lote nunca
> se da de baja como unidad por esta vía.

### `test_no_ajusta_saldo_pendiente_ni_saldo_cliente`
**Qué prueba:** cancelar un artículo del lote no reduce lo que el cliente debe ni lo que ya se le cargó.
**Pasos:**
1. Crear un apartado con 2 productos ($300 y $200).
2. Registrar el `saldo_pendiente` del apartado y el `saldo` del cliente antes de cancelar.
3. Cancelar el artículo del primer producto.
4. Confirmar que `saldo_pendiente` y `cliente.saldo` no cambiaron, y que el apartado sigue `abierto`.

### `test_regresa_producto_a_disponible`
**Qué prueba:** cancelar un artículo ligado a inventario regresa ese producto a `disponible`.
**Pasos:**
1. Crear un apartado con 1 producto de inventario.
2. Cancelar ese artículo.
3. Confirmar que el producto quedó `disponible`.

### `test_rechaza_cancelar_articulo_ya_cancelado`
**Qué prueba:** solo se pueden cancelar artículos en estatus `vigente` — no se puede cancelar dos veces el mismo.
**Pasos:**
1. Crear un apartado con 1 artículo y cancelarlo.
2. Intentar cancelarlo de nuevo.
3. Debe **rechazarse (400)**.

### `test_404_si_articulo_no_existe`
**Qué prueba:** cancelar un artículo de apartado que no existe falla.
**Pasos:**
1. Intentar cancelar el id 999999.
2. Debe **rechazarse (404)**.

### `test_lote_sigue_abierto_aunque_se_cancelen_todos_los_articulos_uno_por_uno`
**Qué prueba:** el lote (`apartados`) nunca se da de baja como unidad al cancelar artículos individuales — sigue `abierto` hasta que `saldo_pendiente` llegue a 0 vía abonos, sin importar cuántos artículos se hayan cancelado. (Cancelar el lote completo como unidad es responsabilidad de `cancelar_movimiento()`, cubierto en `casos_movimientos.md`.)
**Pasos:**
1. Crear un apartado con 2 productos.
2. Cancelar ambos artículos, uno por uno.
3. Confirmar que el apartado sigue en estatus `abierto` (no `cancelado` ni `liquidado`).
4. Confirmar que ambos artículos quedaron `cancelado`.
