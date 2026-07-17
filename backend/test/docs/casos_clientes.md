# Casos de prueba — Módulo Clientes

Espejo en lenguaje humano de `test/test_clientes.py`. Cada punto describe
exactamente lo que el test correspondiente verifica, en el mismo orden en
que aparecen en el código. No es spec de negocio — es la traducción literal
de las 76 pruebas.

---

## Generar número de cliente (`generar_no_cliente`)

1. El primer cliente registrado en una colonia recibe `Centro-001`.
2. Si ya existe `Centro-001`, el siguiente cliente de esa misma colonia recibe `Centro-002` (el consecutivo sube).
3. El consecutivo es independiente por colonia: si `Centro` ya tiene un cliente, `Carrillos` igual empieza en `Carrillos-001`.
4. El nombre de la colonia se normaliza a formato título: `"SAN JUAN"` se convierte en `"San Juan-001"`.

## Sincronizar estatus (`sincronizar_estatus`)

5. Un cliente con saldo mayor a cero queda con estatus `"activo"`.
6. Un cliente con saldo en cero queda con estatus `"inactivo"`.

## Validaciones del formulario de alta (`ClienteCreate`)

7. Un payload con todos los campos válidos no lanza ningún error.
8. Los campos de texto `nombre`, `colonia`, `ref_nombre` y `ref_colonia` se rechazan si vienen vacíos o solo con espacios (se prueba cada uno por separado).
9. Los espacios al inicio y al final del `nombre` se recortan automáticamente (`"  Juan Pérez  "` queda como `"Juan Pérez"`).
10. Un teléfono que no tiene exactamente 10 dígitos se rechaza.
11. El teléfono de referencia (`ref_telefono`) puede omitirse (`None`) sin problema.
12. Si se da un teléfono de referencia, también debe tener 10 dígitos, o se rechaza.
13. Si `frecuencia_pago` es `"dia_especifico_mes"`, el `dia_pago_especifico` debe estar entre 1 y 31; se rechaza si es 32.
14. Si `frecuencia_pago` es `"dia_especifico_mes"` pero no se da ningún `dia_pago_especifico`, se rechaza.
15. Si `frecuencia_pago` es `"dia_especifico_mes"` y el día dado es válido (15), se acepta.
16. Si `frecuencia_pago` es `"otro"` pero no se da `frecuencia_pago_detalle`, se rechaza.
17. Si `frecuencia_pago` es `"otro"` y el detalle viene vacío o solo espacios, se rechaza.
18. Si `frecuencia_pago` es `"otro"` y el detalle viene con espacios de sobra, se acepta y se recorta (`"  paga cuando puede  "` → `"paga cuando puede"`).
19. Si `frecuencia_pago` es `"semanal"`, no se exige ni `dia_pago_especifico` ni `frecuencia_pago_detalle` (quedan en `None`).
20. Un valor de `frecuencia_pago` que no existe en el catálogo (p. ej. `"mensual"`) se rechaza.

## Crear y consultar clientes (`crear_cliente`, `obtener_cliente`, `buscar_clientes`)

21. Al crear un cliente en la colonia `Centro`, se le asigna `Centro-001` como número de cliente.
22. Un cliente recién creado nace con saldo en cero, estatus inactivo y sin fecha de pago programada.
23. La `frecuencia_pago` elegida (por ejemplo `"quincenal"`) se guarda correctamente en el cliente creado.
24. Buscar un cliente por un id que no existe (`9999`) devuelve `None`.
25. Buscar sin ningún texto de búsqueda devuelve todos los clientes registrados.
26. Buscar por un fragmento del nombre (p. ej. `"ana"`) devuelve solo los clientes cuyo nombre coincide (`"Ana López"`, no `"Beto Ruiz"`).
27. Buscar por un fragmento del número de cliente (p. ej. `"centro-001"`) devuelve ese cliente.

## Bandera amarilla — próximo a vencer

28. Si el saldo del cliente es cero, no se activa la bandera amarilla, aunque tenga fecha de pago programada cercana.
29. Si el cliente no tiene fecha de pago programada, no se activa la bandera amarilla.
30. Si falta 1 día para la fecha de pago programada, la bandera amarilla se activa.
31. Si faltan exactamente 2 días (el límite), la bandera amarilla también se activa.
32. Si faltan 3 días, la bandera amarilla NO se activa.
33. Si la fecha de pago programada ya pasó (vencida desde ayer), no es bandera amarilla — ese caso le toca a la roja, no se solapan.

## Bandera roja — vencido

34. Si el saldo del cliente es cero, no se activa la bandera roja, aunque la fecha ya haya pasado.
35. Si el cliente no tiene fecha de pago programada, no se activa la bandera roja.
36. Si hoy es exactamente la fecha de pago programada (ni un día después), no se activa la bandera roja — la condición exige que hoy sea estrictamente posterior.
37. Si la fecha de pago programada fue ayer, la bandera roja se activa.
38. Si la fecha de pago programada todavía no llega (está en el futuro), no se activa la bandera roja.

## Bandera naranja — apartado por vencer

39. Un cliente sin ningún apartado abierto no tiene bandera naranja.
40. Un apartado recién abierto hoy (lejos de cumplir el mes) no activa la bandera naranja.
41. Un apartado abierto que está a exactamente 5 días de cumplir un mes desde que se apartó, sí activa la bandera naranja.
42. Un apartado que ya está liquidado no activa la bandera naranja, aunque la fecha esté dentro del rango de alerta.

## Bandera negra — morosidad familiar

43. Si el cliente mismo no tiene bandera roja, la bandera negra no se activa, aunque uno de sus familiares sí tenga bandera roja.
44. Si el cliente tiene bandera roja pero no tiene ningún familiar vinculado, la bandera negra no se activa.
45. Si el cliente tiene bandera roja y su familiar vinculado NO tiene bandera roja, la bandera negra no se activa.
46. Si el cliente tiene bandera roja y su familiar vinculado también tiene bandera roja, la bandera negra SÍ se activa.
47. Este mismo resultado (bandera negra activa) se cumple sin importar en qué orden se haya declarado el vínculo entre los dos clientes (quién se vinculó como "cliente A" o "cliente B" internamente no afecta el resultado).

## Vínculos familiares (vincular / listar / desvincular)

48. Al vincular dos clientes, el vínculo se guarda siempre con el id menor como "cliente A" y el id mayor como "cliente B", sin importar en qué orden se pasaron los dos clientes al crear el vínculo.
49. Un cliente no se puede vincular consigo mismo — se rechaza.
50. No se puede vincular un cliente con otro que no existe (id `9999`) — se rechaza.
51. Si dos clientes ya están vinculados, intentar vincularlos de nuevo (en cualquier orden) se rechaza.
52. Si un cliente ya tiene 4 vínculos familiares, no se le puede agregar un quinto (validado cuando ese cliente es el primer argumento de la vinculación).
53. Lo mismo aplica cuando ese cliente con 4 vínculos es el segundo argumento de la vinculación — el tope se respeta igual.
54. Al listar los familiares de un cliente, cada uno de los dos clientes del par ve correctamente al otro como su familiar relacionado (la lista se arma bien desde ambas perspectivas del vínculo).
55. Al desvincular un vínculo, éste desaparece de la lista de familiares de ambos clientes involucrados.
56. Intentar desvincular un id de vínculo que no existe (`9999`) se rechaza.
57. Un cliente que no forma parte de un vínculo no puede desvincularlo — si un tercer cliente ajeno lo intenta, se rechaza.

## Cancelar cliente (`cancelar_cliente`)

58. Intentar cancelar un cliente que no existe (id `9999`) se rechaza.
59. Intentar cancelar un cliente que no está en morosidad (sin bandera roja activa, en este caso porque su saldo es cero) se rechaza.
60. Al cancelar un cliente moroso, se guarda un registro en `cartera_vencida` con su número de cliente original, su nombre, el saldo que tenía al momento de cancelarse, y la fecha de cancelación (la de hoy). Ese registro queda efectivamente guardado en la tabla.
61. Al cancelar, el `id_cliente` y el `no_cliente` del cliente NO cambian — se conservan tal cual. En cambio, sí se limpian: el nombre queda vacío, el teléfono queda en 0, la frecuencia de pago pasa a `"otro"`, el día de pago específico queda vacío, el detalle de frecuencia de pago queda como `"slot disponible"`, el nombre y colonia de referencia quedan vacíos, el teléfono de referencia queda vacío, y la fecha de pago programada queda vacía.
62. Después de cancelar, el saldo del cliente queda en cero y su estatus pasa a inactivo.
63. Cancelar a un cliente no afecta sus vínculos familiares — su familiar sigue teniendo el vínculo registrado con normalidad.

## Endpoints de la API

64. Crear un cliente por la API responde con estado 201, devuelve el número de cliente generado (`Centro-001`), y trae las 4 banderas (`bandera_amarilla`, `bandera_roja`, `bandera_naranja`, `bandera_negra`) presentes en la respuesta, todas en `false` para un cliente recién creado.
65. Enviar un payload inválido al crear un cliente (por ejemplo, un teléfono con pocos dígitos) responde con estado 422.
66. Listar clientes por la API responde con estado 200 y devuelve la cantidad correcta de clientes creados.
67. Consultar el detalle de un cliente que no existe responde con estado 404.
68. Consultar el detalle de un cliente que sí existe responde con estado 200 y devuelve su número de cliente correcto.
69. Intentar cancelar un cliente que no existe responde con estado 404.
70. Intentar cancelar un cliente que no está en morosidad responde con estado 400.
71. Flujo completo de familiares por la API: se crean dos clientes, se vincula uno con el otro (responde 201 y devuelve el id del cliente relacionado correcto), se lista el vínculo (responde 200 con un elemento), se desvincula (responde 204), y al volver a listar, la lista queda vacía.
72. Intentar vincular dos clientes que ya están vinculados responde con estado 400.
73. Intentar desvincular un id de vínculo que no existe responde con estado 404.
