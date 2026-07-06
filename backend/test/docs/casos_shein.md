# Casos de prueba — Shein

Espejo en lenguaje humano de `test/test_shein.py`. Mapeado a
`docs/FULL_STACK/module_shein.md`. Reemplaza la versión anterior de este
documento, que excluía a propósito los casos de `INC-15/16/17` porque
todavía no estaban corregidos — ya lo están, así que aquí sí se cubren.

Naturaleza del módulo: la tienda compra en Shein a nombre del cliente y le
cobra al mismo precio de la app, siempre de contado, sin devoluciones. Sin
concepto de "alternativa" como en Pedidos — cada artículo es un renglón
independiente, hasta 4 por pedido.

Dos montos por pedido que **no deben confundirse** (aparecen juntos en cada
caso de abajo donde aplica):
- `monto_pedido_vigente` — suma de lo capturado en artículos aún `vigente`
  (pre-corte, "cuánto se ve que va a costar").
- `monto_pedido` — suma de artículos ya `confirmado` (post-corte, "cuánto
  realmente se cobra"). Antes de pasar por Corte, este campo vale `0`
  aunque el pedido ya tenga precio — no es un error, es el estado esperado.

---

## Flujo 1 — Registrar Cliente Shein

### `test_alta_basica`
Da de alta un cliente con nombre, colonia y teléfono. Confirma que regresa con `id_shein_cliente` asignado.

### `test_nombre_vacio_rechazado`
Un nombre de puros espacios en blanco no cuenta como capturado — se rechaza (422).

### `test_telefono_9_digitos_rechazado` / `test_telefono_11_digitos_rechazado`
El teléfono debe tener exactamente 10 dígitos — ni menos ni más (422 en ambos casos).

### `test_listar_clientes`
La lista de clientes Shein regresa ordenada alfabéticamente por nombre.

---

## Flujo 2 — Registrar Pedido Shein

### `test_cliente_inexistente_404`
No se puede registrar un pedido para un `id_shein_cliente` que no existe.

### `test_pedido_sin_articulos_rechazado`
Un pedido necesita mínimo 1 artículo — con la lista vacía se rechaza (422).

### `test_pedido_con_4_articulos_aceptado`
El máximo permitido (4 artículos) se acepta sin problema.

### `test_pedido_con_5_articulos_rechazado`
Un 5º artículo en la misma creación se rechaza (422) — el límite es un techo real, no una sugerencia.

### `test_articulo_nace_vigente_sin_monto_vigente`
Cada artículo, al crearse, nace en `vigente` con `monto_vigente = null` — nada llega "pre-resuelto".

### `test_monto_debe_ser_positivo`
Un artículo con `monto = 0` se rechaza (422) — un pedido sin precio no tiene sentido.

### `test_producto_vacio_rechazado`
El nombre del producto no puede ser solo espacios en blanco.

---

## Agregar artículo a un pedido existente

*(Antes de esta sesión, esta funcionalidad no existía — era el hallazgo `INC-15`. Corregido: ver `REPORT.md §4.3`.)*

### `test_agregar_articulo_sube_conteo_y_monto_vigente`
**Qué prueba:** un pedido ya creado con 1 artículo puede recibir un 2º artículo después, sin tener que recrear el pedido completo.
**Pasos:**
1. Crear un pedido con 1 artículo de $300.
2. Agregarle un 2º artículo de $450 vía el endpoint de "agregar artículo".
3. Confirmar que el pedido ahora tiene 2 artículos.
4. Confirmar `monto_pedido_vigente = 750` (ambos siguen `vigente`) y `monto_pedido = 0` (nada `confirmado` todavía).

### `test_agregar_5to_articulo_rechazado`
Un pedido que ya tiene 4 artículos no puede recibir un 5º — se rechaza (409), consistente con el límite de creación.

### `test_agregar_articulo_pedido_inexistente_404`
No se puede agregar un artículo a un `id_shein_pedido` que no existe.

### `test_agregar_articulo_pedido_ya_en_corte_rechazado`
**Qué prueba:** un pedido deja de ser editable en cuanto entra a un corte — coincide con el mismo criterio de "editable" del Módulo Pedidos.
**Pasos:**
1. Crear un pedido y llevarlo a un corte.
2. Intentar agregarle un artículo después.
3. Debe **rechazarse (409)**.

---

## Flujo 3 — Lista de Pedidos

### `test_filtrar_por_cliente`
La lista se puede acotar a un solo cliente vía `id_shein_cliente`.

### `test_monto_pedido_vigente_antes_de_corte`
**Qué prueba:** el hallazgo `INC-16` — antes de esta corrección, el monto de un pedido pendiente siempre se veía en `$0` en esta vista, aunque ya tuviera precio capturado.
**Pasos:**
1. Crear un pedido con un artículo de $250, sin tocarlo (sigue `vigente`).
2. Consultar la lista filtrando por su cliente.
3. Confirmar `monto_pedido_vigente = 250` (el monto real capturado) y `monto_pedido = 0` (correcto, todavía no pasa por corte).

### `test_sin_corte_filtra_pendientes`
Pasando `sin_corte=true`, la lista solo regresa pedidos que aún no tienen `id_shein_corte` — un pedido ya cortado desaparece de esta vista.

---

## Resolución de artículo (soporte del flujo de Corte)

### `test_articulo_inexistente_404`
No se puede resolver un `id_shein_articulo` que no existe.

### `test_variacion_de_precio_conserva_monto_original`
**Qué prueba:** cuando el precio cambia, se guarda el nuevo valor sin perder el original capturado — para poder auditar después qué se cotizó vs. qué se cobró.
**Pasos:**
1. Crear un pedido con un artículo de $300.
2. Resolverlo a `confirmado` con `monto_vigente = 350`.
3. Confirmar que `monto` sigue en `300` (intacto) y `monto_vigente` quedó en `350`.

### `test_no_se_puede_resolver_articulo_de_pedido_ya_en_corte`
Un pedido ya cortado congela sus artículos — no se pueden volver a tocar (409).

---

## Flujo 4 — Registrar Corte

### `test_autoconfirma_vigente_sin_tocar`
**Qué prueba:** el hallazgo `INC-17` — antes de esta corrección, el corte se rechazaba por completo (409) si cualquier artículo seguía `vigente`, obligando a resolver a mano el 100%, incluso lo que no cambió de precio.
**Pasos:**
1. Crear un pedido con 2 artículos ($300 y $450).
2. Resolver a mano **solo** el segundo (cambió de precio, ahora $500) — el primero se deja intencionalmente sin tocar, todavía `vigente`.
3. Registrar el corte incluyendo ese pedido.
4. Debe **aceptarse (201)** — ya no se rechaza.
5. Confirmar `suma_pedidos = 800` ($300 autoconfirmado + $500 resuelto a mano) y `cupon = suma_pedidos - total_ticket`.
6. Confirmar que **ambos** artículos terminan `confirmado` — el primero se autoconfirmó solo, sin intervención manual.

### `test_pedido_todos_cancelados_queda_fuera_sin_castigo`
**Qué prueba:** cancelar todos los artículos de un pedido no rompe el corte de los demás pedidos incluidos.
**Pasos:**
1. Dos pedidos, cada uno con 1 artículo: uno se cancela, el otro se confirma.
2. Incluir ambos en el mismo corte.
3. Confirmar que el corte se crea exitosamente.
4. El pedido cancelado **no** recibe `id_shein_corte` ni `estatus_pago` (quedan `null`); el otro sí.

### `test_pedido_no_encontrado_404`
Incluir un `id_shein_pedido` inexistente en el corte se rechaza, listando el id faltante.

### `test_pedido_ya_en_corte_previo_rechazado`
Un pedido no puede incluirse dos veces en cortes distintos (409).

### `test_total_ticket_no_positivo_rechazado`
`total_ticket = 0` (o negativo) se rechaza (422) — el corte necesita el dato real de caja.

---

## Flujo 5 — Consulta de Cortes

### `test_listar_y_detalle`
Un corte recién creado aparece en el listado general y su detalle individual trae `suma_pedidos`/`cupon` correctos.

### `test_corte_inexistente_404`
Consultar un `id_shein_corte` que no existe se rechaza.

---

## Escenario integral

### `test_escenario_shein_ciclo_completo`
Reproduce, en un solo test, la misma secuencia que se verificó manualmente con `curl` antes de dar por cerrados los 3 hallazgos: crear pedido → agregarle un artículo (`INC-15`) → variar precio de uno solo, dejando el otro sin tocar → cortar (autoconfirmando el que no se tocó, `INC-17`) → confirmar que `monto_pedido`/`monto_pedido_vigente` quedan correctos al final (`INC-16`). Sirve como red de seguridad: si alguno de los 3 fixes se rompe por un cambio futuro, este test lo detecta aunque los tests aislados de cada uno sigan pasando por separado.
