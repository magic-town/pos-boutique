# Casos de prueba — Inventario

Espejo en lenguaje humano de `test/test_inventario.py`. Mapeado a
`docs/FULL_STACK/module_inventario.md`. Si cambias una regla de negocio ahí,
actualiza el caso correspondiente aquí y el test real.

Helper compartido por todos los casos: `_crear_producto(client, headers, **overrides)`
— crea un producto con valores por defecto razonables (categoría `dama`,
`informal`, marca `Aspik`, precio 500, stock 10) y permite sobreescribir
cualquier campo. Se usa como punto de partida en casi todos los casos de abajo.

---

## Opción 1 — Agregar Producto

### `test_alta_basica`
**Qué prueba:** dar de alta un producto nuevo deja todo en su estado inicial correcto.
**Pasos:**
1. Crear un producto con descripción "Blusa dama".
2. Verificar que nace con `estatus = disponible`.
3. Verificar que `precio_descuento` nace en `null` (nadie captura descuento al dar de alta).

---

## Opción 2 — Cambiar Estatus

### `test_transicion_a_en_ruta_requiere_descripcion`
**Qué prueba:** `descripcion_ruta` es obligatoria para mandar un producto "en ruta" (a exhibición/feria), y si se manda, se guarda bien.
**Pasos:**
1. Crear un producto.
2. Intentar cambiar su estatus a `en_ruta` **sin** `descripcion_ruta` → debe **rechazarse (422)**.
3. Repetir el cambio, esta vez **con** `descripcion_ruta = "Exhibición en feria"` → debe **aceptarse (200)**.
4. Confirmar que el producto guardó exactamente esa descripción.

### `test_transicion_invalida_rechazada`
**Qué prueba:** el sistema no permite "resucitar" un producto ya vendido.
**Pasos:**
1. Crear un producto (nace `disponible`).
2. Marcarlo como `vendido`.
3. Intentar regresarlo a `disponible` → debe **rechazarse (400)**, porque `vendido` es un estado final: no hay transición válida de vuelta a `disponible`.

### `test_precio_descuento_debe_ser_menor_a_precio_venta`
**Qué prueba:** no se puede poner un "descuento" que en realidad sea más caro que el precio normal.
**Pasos:**
1. Crear un producto con `precio_venta = 500`.
2. Intentar marcarlo `disponible_c/descuento` con `precio_descuento = 600` (más caro, no más barato).
3. Debe **rechazarse (400)** — un descuento nunca puede ser mayor o igual al precio de venta.

---

## Opción 4 / 5 — Descuento Masivo (aplicar / retirar)

> **Nota — "descuento individual" no es una función aparte.** No existe (ni
> hace falta) un endpoint separado para descontar un solo producto por
> porcentaje. `SegmentoDescuento.ids_producto` acepta una lista; pasar una
> lista de un solo elemento (`ids_producto: [111111]`) usa el mismo endpoint
> de descuento masivo (`POST /inventario/descuento-masivo`) para afectar
> exactamente ese producto — mismo cálculo, mismo código. "Individual" es
> "masivo con `n = 1`", no un caso aparte que necesite su propia lógica. La
> única vía realmente distinta para tocar `precio_descuento` de un producto
> es la Opción 2 (`cambiar_estatus` → `disponible_c/descuento`), pero ahí se
> captura el precio final ya calculado a mano, no un porcentaje.
>
> **`pct` y `precio_fijo` nunca se combinan ni se apilan.**
> `AplicarDescuentoMasivoRequest` exige exactamente uno de los dos
> (`schemas/inventario.py`, `_exactamente_una_forma_de_descuento`) — son dos
> formas alternas de llegar al mismo campo `precio_descuento`, nunca
> simultáneas. Enviar ambos o ninguno debe rechazarse con `422`; sin test
> que lo cubra todavía.

### `test_aplicar_por_marca_y_retirar`
**Qué prueba:** aplicar un descuento por porcentaje a todos los productos de una marca, y luego poder quitarlo, sin afectar otras marcas.
**Pasos:**
1. Crear 2 productos de la marca "MarcaTestUnica" (precios 1000 y 2000) y 1 producto de "OtraMarca" (precio 500) que **no** debe tocarse.
2. Aplicar descuento masivo del 20% filtrando por marca = "MarcaTestUnica".
3. Confirmar que se afectaron exactamente **2** productos (no el de "OtraMarca").
4. Confirmar los precios con descuento calculados: 1000 → 800, 2000 → 1600 (ambos 80% del original).
5. Retirar el descuento masivo de esa misma marca.
6. Confirmar que se revirtieron exactamente esos mismos **2** productos.

### `test_precio_fijo_mayor_a_venta_se_omite`
**Qué prueba:** al aplicar un descuento masivo por *precio fijo* (en vez de porcentaje), el sistema se salta automáticamente cualquier producto donde ese precio fijo terminaría siendo **más caro** que el precio normal — no revienta la operación completa, solo omite ese producto.
**Pasos:**
1. Crear 2 productos de la misma marca: uno "barato" (precio 50) y uno "caro" (precio 500).
2. Aplicar descuento masivo con `precio_fijo = 99` a esa marca.
3. Confirmar que solo se afectó **1** producto (el "caro" — 99 sí es menor a 500).
4. Confirmar que el "barato" quedó en la lista de **omitidos** (99 sería más caro que sus 50 originales, así que no tendría sentido como "descuento").

### `test_segmento_vacio_rechazado`
**Qué prueba:** no se puede lanzar un descuento masivo sin decir a qué productos aplica — evita que alguien descuente sin querer *todo* el inventario por accidente.
**Pasos:**
1. Intentar aplicar un descuento del 10% con un segmento completamente vacío (sin marca, categoría, talla, color, ni lista de ids).
2. Debe **rechazarse (422)** — se exige al menos un criterio de filtro.

### `test_no_afecta_productos_vendidos`
**Qué prueba:** un descuento masivo nunca toca productos que ya se vendieron.
**Pasos:**
1. Crear un producto y marcarlo como `vendido`.
2. Aplicar un descuento masivo del 50% filtrando por su marca.
3. Confirmar que se afectaron **0** productos — el descuento masivo solo opera sobre productos actualmente `disponible`, `vendido` queda fuera aunque coincida con el filtro de marca.
