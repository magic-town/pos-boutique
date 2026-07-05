# Casos de prueba — Pedidos

Espejo en lenguaje humano de `test/test_pedidos.py`. Mapeado a
`docs/FULL_STACK/module_pedidos.md`. Si cambias una regla de negocio ahí,
actualiza el caso correspondiente aquí y el test real.

Helpers compartidos:
- `_crear_pedido_informal(...)`: registra un pedido de 1 solo artículo `informal` con monto libre — atajo para los casos que no necesitan catálogo.
- `_saldo(...)`: consulta directo a la base el saldo actual del cliente (bypass de la API, para verificar el efecto real en `clientes.saldo`).

Regla de fondo que casi todos estos casos protegen (`module_pedidos.md`,
línea 537): **el saldo del cliente NO se mueve al registrar el pedido.** Se
mueve (`saldo += monto`) exactamente en el momento en que la operadora marca
un artículo como `en_almacen` (acción: "surtir").

---

## Registrar Pedido

### `test_formal_con_catalogo_autollena_monto`
**Qué prueba:** para un artículo `formal` de un proveedor con catálogo importado (ej. Price_Shoes), el precio lo decide el catálogo, no lo que mande quien registra el pedido.
**Pasos:**
1. Buscar en la base el precio de catálogo más reciente de Price_Shoes (si no hay ninguno importado, el caso se salta con aviso — necesita correr `importar_precios.py` primero).
2. Registrar un pedido `formal` con ese proveedor, mandando un `monto = 1` (un valor absurdo, a propósito).
3. Confirmar que el sistema **ignoró** ese `1` y guardó el precio real del catálogo.
4. Confirmar que el artículo nace en estatus `vigente`.

### `test_informal_respeta_monto_libre`
**Qué prueba:** lo contrario al caso anterior — un artículo `informal` (sin catálogo detrás) sí respeta el monto que se capture a mano.
**Pasos:**
1. Registrar un pedido `informal` con `monto = 350` y sin proveedor.
2. Confirmar que el `proveedor` queda vacío (`null`).
3. Confirmar que el monto guardado es exactamente `350`, tal cual se mandó.

### `test_cliente_inexistente_devuelve_404`
**Qué prueba:** no se puede registrar un pedido para un cliente que no existe.
**Pasos:**
1. Intentar registrar un pedido usando un `no_cliente` inventado que no está en la base.
2. Debe **rechazarse (404)**.

---

## Límite de alternativas (`REGLAS_NEGOCIO.md` §3, regla 2)

### `test_price_shoes_acepta_3_alternativas`
**Qué prueba:** para Price_Shoes, un artículo principal puede traer hasta 3 alternativas (por si no hay talla/existencia del principal).
**Pasos:**
1. Registrar un pedido con 1 artículo principal + 3 alternativas, todas Price_Shoes.
2. Debe **aceptarse (201)**.
3. Confirmar que la respuesta trae los 4 artículos (1 principal + 3 alternativas).

### `test_price_shoes_rechaza_4_alternativas`
**Qué prueba:** el límite de 3 alternativas para Price_Shoes es un tope duro, no una sugerencia.
**Pasos:**
1. Intentar registrar el mismo tipo de pedido, pero con **4** alternativas.
2. Debe **rechazarse (422)**.

### `test_otro_proveedor_rechaza_2_alternativas`
**Qué prueba:** el límite de 3 alternativas es exclusivo de Price_Shoes — para cualquier otro proveedor (aquí, Pakar) el límite es más estricto.
**Pasos:**
1. Intentar registrar un pedido con proveedor "Pakar", con 2 alternativas.
2. Debe **rechazarse (422)** — para proveedores distintos a Price_Shoes el máximo permitido es 1 alternativa, no 2.

---

## Lista de Surtido / Devolución / Cancelación

### `test_surtir_sube_saldo`
**Qué prueba:** el ciclo completo del saldo alrededor del momento de "surtir" — no solo que suba, sino que **no suba antes de tiempo**.
**Pasos:**
1. Registrar un pedido informal por $200.
2. Confirmar que el saldo del cliente sigue en **$0** — aunque el artículo ya tiene precio, todavía está `vigente`, no se ha cobrado nada.
3. Marcar el artículo como surtido (`PATCH .../surtir`, pasa a `en_almacen`).
4. Confirmar que el saldo ahora sí subió a **$200**.

### `test_devolucion_revierte_saldo`
**Qué prueba:** devolver un artículo ya surtido cancela la deuda que había generado, y dispara un artículo sustituto.
**Pasos:**
1. Registrar un pedido informal por $150 y surtirlo (saldo sube a $150).
2. Registrar una devolución de ese artículo.
3. Confirmar que la respuesta trae un artículo nuevo cuyo campo `id_articulo_sustituye` apunta de vuelta al artículo original devuelto.
4. Confirmar que el saldo del cliente regresó a **$0**.

### `test_cancelar_vigente_no_afecta_saldo`
**Qué prueba:** cancelar un artículo que **todavía no ha llegado** (sigue `vigente`) no tiene ningún efecto en el saldo, porque nunca se había cobrado.
**Pasos:**
1. Registrar un pedido informal por $300, sin surtirlo.
2. Cancelarlo directamente desde `vigente`.
3. Confirmar que el saldo sigue en **$0** — nunca hubo cargo que revertir.

### `test_cancelar_en_almacen_revierte_saldo`
**Qué prueba:** cancelar un artículo que **ya llegó** (`en_almacen`) sí revierte el cargo, igual que una devolución, pero sin generar artículo sustituto.
**Pasos:**
1. Registrar un pedido informal por $400 y surtirlo (saldo sube a $400).
2. Cancelarlo (ya estando `en_almacen`, no `vigente`).
3. Confirmar que el saldo regresa a **$0**.

---

## Escenario integral: pedido de 3 artículos, cada uno con un desenlace distinto

### `test_escenario_pedido_de_tres_articulos_mixto`
**Qué prueba:** reproduce un caso real completo — un cliente encarga 3 prendas en un mismo pedido, y cada una termina de forma diferente. Verifica el saldo en **cada paso del camino**, no solo el resultado final, para que ningún efecto colateral entre artículos pase desapercibido.

**Narrativa paso a paso:**
1. El cliente encarga 3 blusas en un solo pedido: **A** ($300, se va a aceptar), **B** ($250, se va a devolver), **C** ($180, se va a cancelar antes de que llegue).
2. Saldo inicial: **$0** (nada ha llegado todavía, aunque las 3 ya tienen precio).
3. El cliente cambia de opinión sobre **C** antes de que llegue → se cancela estando `vigente`. Saldo sigue en **$0** (cancelar algo que nunca llegó no cobra nada).
4. Llegan **A** y **B** a la tienda → ambas se marcan `en_almacen` (surtidas). Saldo sube a **$550** ($300 + $250 — nótese que **C**, cancelada, nunca contó).
5. El cliente se queda con **A** (no requiere ninguna acción adicional — aceptar es simplemente "no hacer nada más") y devuelve **B**.
6. Tras la devolución de **B**, el saldo baja a **$300** — queda únicamente el cargo de **A**, la única que el cliente conservó.
7. Verificación final de estados en la base: **A** terminó `en_almacen` (la conservó), **B** terminó `devuelto`, **C** terminó `cancelado`.
