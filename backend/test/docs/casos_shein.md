# Casos de prueba — Módulo Shein

Espejo en lenguaje humano de `test/test_shein.py` (Bloque C, tarea 27).
63 casos, agrupados en las mismas 7 clases del archivo de test. Cada fila
describe qué hace el caso y qué se espera del sistema — no el código.

Convención: todos los casos parten de un cliente Shein y/o pedido creados
al vuelo (sufijo único por corrida), corriendo contra la API real
(`TestClient` + login admin de `conftest.py`).

---

## 1. Cliente Shein (`TestClienteShein` — 7 casos)

| # | Caso | Qué se espera |
|---|------|----------------|
| 1 | Crear cliente con datos válidos | Se crea con `saldo=0`, `estatus=inactivo`, sin `fecha_pago_programada` y sin `bandera`. |
| 2 | Frecuencia "día específico del mes" sin indicar el día | La API rechaza la solicitud (422): el día es obligatorio en ese caso. |
| 3 | Frecuencia "otro" sin indicar el detalle | La API rechaza la solicitud (422): el detalle es obligatorio en ese caso. |
| 4 | Teléfono que no tiene 10 dígitos | La API rechaza la solicitud (422). |
| 5 | Nombre vacío (solo espacios) | La API rechaza la solicitud (422). |
| 6 | Listar clientes después de crear uno | El cliente recién creado aparece en el listado. |
| 7 | Un cliente Shein no requiere ni expone `id_cliente` | Confirma que `shein_clientes` es independiente del catálogo de `clientes` — no hay relación entre ambos. |

## 2. Pedido Shein (`TestPedidoShein` — 9 casos)

| # | Caso | Qué se espera |
|---|------|----------------|
| 1 | Crear pedido con 1 artículo | Se crea correctamente, sin corte asignado (`id_shein_corte=null`) y sin estatus de pago aún. |
| 2 | Crear pedido con 4 artículos (máximo permitido) | Se crea correctamente con los 4 artículos. |
| 3 | Intentar crear pedido con 5 artículos | La API rechaza la solicitud (422): supera el máximo de 4. |
| 4 | Intentar crear pedido sin artículos | La API rechaza la solicitud (422): se requiere al menos 1. |
| 5 | Crear pedido para un cliente que no existe | La API responde 404. |
| 6 | Crear pedido con un artículo sin `sku` | La API rechaza la solicitud (422): el SKU es obligatorio en cada renglón. |
| 7 | Consultar el monto de un pedido recién creado, antes del corte | `monto_pedido` debe ser 0 (nada está "confirmado" todavía), pero `monto_pedido_vigente` sí refleja el monto capturado en los artículos. |
| 8 | Listar pedidos filtrando por `sin_corte=true` | El pedido recién creado (que aún no tiene corte) aparece en el listado. |
| 9 | Listar pedidos filtrando por cliente | Solo aparecen los pedidos de ese cliente, ninguno de otro. |

## 3. Artículo Shein — agregar y resolver estatus (`TestArticuloShein` — 9 casos)

| # | Caso | Qué se espera |
|---|------|----------------|
| 1 | Agregar un artículo adicional a un pedido editable (sin corte) | Se agrega y el pedido queda con 2 artículos. |
| 2 | Intentar agregar un 5º artículo a un pedido que ya tiene 4 | La API rechaza (409): se alcanzó el límite. |
| 3 | Intentar agregar un artículo a un pedido que ya pasó por corte | La API rechaza (409): un pedido cortado ya no es editable. |
| 4 | Agregar artículo a un pedido que no existe | La API responde 404. |
| 5 | Confirmar manualmente un artículo indicando su nuevo precio (`monto_vigente`) | El artículo queda `confirmado` con ese monto vigente registrado. |
| 6 | Cancelar manualmente un artículo | El artículo queda `cancelado`. |
| 7 | Confirmar un artículo con `monto_vigente` negativo | La API rechaza la solicitud (422). |
| 8 | Intentar resolver el estatus de un artículo cuyo pedido ya fue cortado | La API rechaza (409). |
| 9 | Resolver el estatus de un artículo que no existe | La API responde 404. |

## 4. Corte Shein (`TestCorteShein` — 13 casos)

| # | Caso | Qué se espera |
|---|------|----------------|
| 1 | Cortar un pedido cuyo artículo nunca cambió de precio (nadie lo resolvió manualmente) | El artículo se autoconfirma en el corte con su monto original; el corte queda con 1 pedido y la suma correcta; se calcula el cupón (`suma_pedidos − total_ticket`); el saldo del cliente sube por ese monto y su estatus pasa a `activo`; el pedido queda enlazado al corte con `estatus_pago=pago_pendiente` y su `monto_pedido` ya refleja lo cobrado. |
| 2 | Cortar un pedido cuyo artículo fue confirmado manualmente con un precio distinto | El corte usa el `monto_vigente` capturado en la confirmación, no el monto original del pedido. |
| 3 | **Cascada de cancelación total**: cortar un pedido cuyos artículos fueron todos cancelados a mano | El corte se crea igualmente pero con `total_pedidos=0` y `suma_pedidos=0`; el pedido **no** queda enlazado al corte (`id_shein_corte` sigue vacío) y por eso sigue apareciendo en el listado `sin_corte=true`; el saldo del cliente no se toca y su estatus permanece `inactivo`. |
| 4 | *(comportamiento derivado del caso anterior)* Reenviar a un segundo corte el mismo pedido ya totalmente cancelado | Como nunca quedó "en corte" la primera vez, la API lo acepta de nuevo (no da 409) — se documenta este comportamiento actual, sin calificarlo de correcto o incorrecto, y se confirma que no duplica ningún cargo al saldo. |
| 5 | Cortar un pedido con 2 artículos, uno cancelado y otro dejado sin resolver (autoconfirma) | Solo el artículo que terminó `confirmado` cuenta en la suma del corte; el cancelado se excluye. |
| 6 | Cortar dos pedidos del mismo cliente en un mismo corte | El corte agrupa ambos; el saldo del cliente se carga **una sola vez** con la suma total, no se duplica por pedido. |
| 7 | Cortar pedidos de dos clientes distintos en el mismo corte | El saldo de cada cliente se actualiza de forma independiente, sin mezclarse entre ellos. |
| 8 | Intentar incluir en un corte un pedido que ya fue cortado antes | La API rechaza (409). |
| 9 | Intentar cortar un pedido que no existe | La API responde 404. |
| 10 | Enviar una lista mixta de pedidos (uno real + uno inexistente) a un corte | La API responde 404 — el chequeo de existencia tiene prioridad sobre el de "ya cortado". |
| 11 | Registrar un corte con `total_ticket` en 0 (o negativo) | La API rechaza la solicitud (422). |
| 12 | Registrar un corte sin ningún pedido en la lista | La API rechaza la solicitud (422): se requiere al menos uno. |
| 13 | Registrar un corte donde el ticket pagado es mayor a la suma de los pedidos | El cupón calculado puede salir **negativo** — no hay ninguna validación que lo impida, se confirma que el backend no lo bloquea silenciosamente. |

## 5. Consulta de cortes (`TestConsultaCortes` — 3 casos)

| # | Caso | Qué se espera |
|---|------|----------------|
| 1 | Listar todos los cortes después de registrar uno | El corte recién creado aparece en el listado general. |
| 2 | Consultar el detalle de un corte por su id | Devuelve la información de ese corte específico. |
| 3 | Consultar el detalle de un corte que no existe | La API responde 404. |

## 6. Abono Shein (`TestAbonoShein` — 15 casos)

*Todos parten de un cliente con saldo ya cargado (vía pedido + corte), para poder probar el abono sobre una deuda real.*

| # | Caso | Qué se espera |
|---|------|----------------|
| 1 | Abonar un monto menor al saldo | El saldo baja exactamente en ese monto; el movimiento devuelve el `saldo_resultante` correcto; el estatus del cliente sigue `activo` (aún debe). |
| 2 | Intentar abonar más de lo que el cliente debe | La API rechaza (409): el abono no puede exceder el saldo. |
| 3 | Abonar un monto en 0 (o negativo) | La API rechaza la solicitud (422). |
| 4 | Abonar exactamente el saldo total (liquidar la deuda) | El saldo llega a 0 y el estatus del cliente vuelve a `inactivo`. |
| 5 | Abonar a un cliente que no existe | La API responde 404. |
| 6 | Abonar indicando la forma de pago (ej. transferencia) | El movimiento queda registrado con esa forma de pago. |
| 7 | Frecuencia **semanal**: abonar hoy | La próxima fecha de pago programada queda en **hoy + 7 días**. |
| 8 | Frecuencia **quincenal**, abonando antes del día 15 del mes | La próxima fecha programada cae en el **día 15 de ese mismo mes**. |
| 9 | Frecuencia **quincenal**, abonando después del día 15 | La próxima fecha programada cae en el **último día de ese mismo mes**. |
| 10 | Frecuencia **quincenal**, abonando justo el último día del mes | La próxima fecha programada salta al **día 15 del mes siguiente** (ya no queda ningún corte quincenal disponible en el mes actual). |
| 11 | Frecuencia **día específico del mes** (ej. día 20), abonando antes de esa fecha | La próxima fecha programada cae en ese mismo día del mes actual. |
| 12 | Frecuencia **día específico del mes**, abonando después de que ese día ya pasó | La próxima fecha programada salta al mismo día pero del **mes siguiente**. |
| 13 | Frecuencia **día específico = 31**, abonando justo el 31 de enero (mes que sí tiene día 31, pero ya no queda margen dentro del mes) | La fecha debe saltar a febrero y **recortarse (clamp) al día 28** — último día real de ese mes — en vez de fallar. |
| 14 | *(caso de contraste con el anterior)* Frecuencia **día específico = 31**, abonando el 25 de enero | Como el día 31 de enero sí existe y todavía no pasó, la fecha programada se queda en **31 de enero**, sin saltar de mes. |
| 15 | Frecuencia **"otro"** | El abono se registra con normalidad, pero la fecha de pago programada **nunca** se calcula — se mantiene vacía en cualquier escenario, porque esta frecuencia no sigue una regla fija. |
| — | Dos abonos consecutivos en fechas distintas | La fecha de pago programada se **recalcula en cada abono** (no se queda fija desde el primero); el segundo abono la actualiza según la fecha en que se realiza. |

## 7. Banderas de cobranza — amarilla / roja (`TestBanderaShein` — 6 casos)

*Campo calculado al vuelo en cada consulta, no se guarda en base de datos. Los casos manipulan directamente `saldo` y `fecha_pago_programada` para aislar la regla de la bandera, sin depender de cómo se llegó a ese estado.*

| # | Caso | Qué se espera |
|---|------|----------------|
| 1 | Cliente sin saldo pendiente | No muestra ninguna bandera. |
| 2 | Cliente con saldo pero cuya fecha de pago programada aún está lejos (10 días) | No muestra ninguna bandera todavía. |
| 3 | Fecha de pago programada dentro de los próximos 2 días | Bandera **amarilla**. |
| 4 | Fecha de pago programada es hoy mismo | Bandera **amarilla**. |
| 5 | Fecha de pago programada ya pasó (vencida) | Bandera **roja**. |
| 6 | Fecha de pago programada muy vencida (un año) | Sigue siendo **roja** (o vacía) — nunca debe aparecer "naranja" ni "negra", porque esas banderas son exclusivas de apartados y familiares, conceptos que Shein no maneja. |

---

## Notas de cobertura

- **Endpoint agregado en esta ronda:** `POST /shein/abono` no existía en el router aunque el servicio y el schema ya estaban implementados (ver REPORT.md §4.1). Se agregó como parte de este trabajo; los 15 casos de la sección 6 dependen de él.
- **Comportamiento documentado, no corregido:** el caso 4 de la sección 4 (Corte) deja constancia de que un pedido totalmente cancelado puede reenviarse a un corte futuro sin bloqueo, porque nunca queda formalmente "en corte". Es intencional dejarlo como documentación de comportamiento actual — decidir si se bloquea es un cambio de negocio, no un bug de test.
- **Lo que este archivo no cubre:** carga de datos vía SQL directo fuera de los endpoints, condiciones de carrera (dos abonos simultáneos sobre el mismo cliente), ni límites de longitud de los demás campos de texto más allá de `nombre`/`colonia` (ya validados indirectamente por los helpers de creación).
