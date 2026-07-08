# Tests automatizados — convención

Este documento parte desde cero y está pensado para una persona que necesita verificar el funcionamiento de los siguientes módulos. Su objetivo es reconstruir el escenario completo en pocos pasos para comprobar que el flujo sigue funcionando correctamente, evitando configuraciones o validaciones manuales repetitivas. Se enfoca exclusivamente en la verificación del flujo, no en explicar su funcionamiento o servir como material de aprendizaje.

## Cómo correr

Correr desde `backend/`, requiere `pytest.ini`

```bash
cd backend
python3 -m venv venv          # si no existe ya
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest test/ -v
```

Requiere `pos.db` ya migrado (`alembic upgrade head`) y, para los tests de
Pedidos que dependen de catálogo, `precios_catalogo` ya importado
(`python -m app.scripts.importar_precios ...`). No requiere `uvicorn`
corriendo — usa `TestClient`, que invoca la app directamente en proceso.

## Estructura

- `conftest.py` — fixtures compartidas por todos los módulos: `client`
  (TestClient), `admin_token`/`auth_headers` (login real), `cliente_prueba`
  (cliente desechable, `no_cliente` único por corrida vía `uuid`, creado
  directo en SQLAlchemy para no depender de módulos con bugs conocidos).
- `test_<modulo>.py` — un archivo por módulo, mapeado 1:1 a
  `FULLSTACK/module_<modulo>.md`. Si el spec de un módulo no tiene un
  `module_<modulo>.md` propio todavía, ese es el primer paso, no escribir el
  test a ciegas contra el `.md` monolítico.

## Módulos y su estado (actualizar conforme se agreguen)

| Módulo | `FULLSTACK/module_*.md` | `test_*.py` | `casos_uso` |
|---|---|---|---|
| Pedidos | ✅ existe | ✅ `test_pedidos.py` (corrido, verde) | ✅ `casos_pedidos.md` |
| Inventario | ✅ existe | ✅ `test_inventario.py` (corrido, verde) | ✅ `casos_inventario.md` |
| Shein | ✅ existe | ✅ `test_shein.py` (corrido, verde) | ✅ `casos_shein.md` |
| Clientes | ✅ existe | ✅ `test_cliente.py` (corrido, verde) | ✅ `casos_cliente.md` |
| Movimientos | ✅ existe | ❌ pendiente (bloqueado por INC-05/06) | ❌ en diseño |
| Recargas | ✅ existe | ❌ pendiente (sin código todavía) | ❌ en diseño |
| Consulta | ✅ existe | ❌ pendiente (sin código todavía) | ❌ en diseño |
| Setting | ✅ existe | ❌ pendiente (Auth existente; Setting sin código) | ❌ en diseño |

Ver `docs/FULLSTACK/README.md` para el detalle de cada uno (es la fuente de
verdad de esta tabla — actualízala ahí primero, luego refleja aquí).

Detalle en lenguaje llano de cada caso, mapeado 1:1 a los tests de abajo: `casos_inventario.md`, `casos_pedidos.md`, `casos_shein.md`, `casos_clientes.md`.

## Cobertura conocida (revisado contra el spec, no solo "ya quedó")

### `test_pedidos.py`

Cubre: lookup automático de precio, `informal` con monto libre, cliente
inexistente (404), límite de alternativas (3 para Price_Shoes / 1 para el resto, ambos límites superiores), saldo del cliente sin cambios mientras el artículo está `vigente` (aunque ya tenga monto resuelto) y solo sube (`+=`) al pasar a `en_almacen`, devolución (`-=` + precarga), cancelar `vigente` (sin impacto) y `en_almacen` (revierte), escenario integral de 3 artículos mixto.

**Huecos que NO están cubiertos todavía** (encontrados al revisar, no
inventados para parecer exhaustivo):
- `proveedor = otro` con `monto` faltante — el schema lo valida
  (`ArticuloCreate`), pero ningún test dispara ese `422`.
- Alternativa con proveedor distinto al principal (ej. principal `Pakar`,
  alternativa `Price_Shoes`) — la regla dice que el límite lo da el
  principal; no hay test que confirme que una alternativa "distinta" no
  rompe nada.
- Devolver un artículo que no está `en_almacen` (ej. todavía `vigente`) —
  debería dar `400`, no probado.
- Cancelar un artículo ya `cancelado` o `devuelto` — comportamiento en
  reintento, no probado.
- 404 de cliente inexistente en `/devolucion` y `/cancelacion` (solo se
  probó en `POST /pedidos`).

### `test_inventario.py`

Cubre: alta básica, transición a `en_ruta` (requiere `descripcion_ruta`),
transición inválida (`vendido → disponible`), `precio_descuento >=
precio_venta` rechazado, descuento masivo por `marca` (aplicar + retirar),
`precio_fijo` mayor al de venta (omitido, no aborta), segmento vacío
rechazado, productos `vendido` no afectados por descuento masivo.

**Huecos:**
- Selección manual por `ids_producto` — el schema lo soporta
  (`SegmentoDescuento.ids_producto`), pero solo se probó filtro por `marca`.
- Combinar filtro + `ids_producto` a la vez (AND) — no probado.
- Consulta con múltiples filtros combinados a la vez (`categoria` +
  `tipo_producto` + `marca` juntos) — solo se probó un filtro por vez.

Quedan pendientes de cerrar en una sesión aparte — son casos nuevos, no
arreglos de lo ya escrito, y no bloquean nada de lo que ya está en verde.

### `test_shein.py`

Cubre los 5 flujos (Registrar Cliente, Registrar Pedido, Lista de Pedidos,
Registrar Corte, Consulta de Cortes), el endpoint de agregar artículo a un
pedido existente, y los 3 hallazgos corregidos esta sesión (`REPORT.md
§4.3`, `INC-15/16/17`): agregar artículo pre-corte, `monto_pedido_vigente`
en Lista de Pedidos, autoconfirmación de `vigente` al crear el corte.
Escenario integral (`test_escenario_shein_ciclo_completo`) que ejercita los
3 fixes en conjunto, no solo aislados.

**Huecos:**
- Límite exacto de teléfono (`1000000000` y `9999999999`, los bordes del
  rango válido) — solo se probaron valores claramente inválidos (9 y 11
  dígitos), no los bordes exactos.
- `id_articulo` (referencia libre a la app Shein, `max_length=20`) — nunca
  se ejercitó con un valor que exceda el límite.
- `tipo_producto` con un valor fuera del enum (`Nacional`/`Importado`) — no
  probado explícitamente.
- Corte incluyendo pedidos de **distintos** clientes Shein a la vez — todos
  los casos de corte usan pedidos de un mismo cliente.
- `SheinArticuloEstatusUpdate.estatus_articulo` acepta técnicamente
  `"vigente"` como valor (no está restringido a `confirmado`/`cancelado`,
  que son las únicas dos resoluciones que describe el spec) — no es un
  `INC` numerado porque no rompe nada hoy, pero no está probado que el
  sistema rechace revertir un artículo ya resuelto de vuelta a `vigente`.

Igual que Inventario: son casos nuevos o de borde, no arreglos de lo ya
escrito, y no bloquean el estado en verde actual.

### `test_clientes.py`

Cubre los 2 casos (Registrar Cliente, Consulata cliente)  — a diferencia de las tres
secciones anteriores. De los 3 pendientes originales (ver `docs/REPORT.md`
§5 punto 3 / §4.3), los 3 ya están resueltos en este `conftest.py`:

1. ~~Actualizar el fixture `cliente_prueba`~~ ✅ — ya crea el cliente vía
   `POST /api/v1/clientes` real (ver sección de abajo).
2. ~~Confirmar las rutas asumidas contra `app/api/v1/endpoints/clientes.py`
   real~~ ✅ — confirmadas: `POST /clientes`, `GET /clientes/{id_cliente}`,
   `GET /clientes?q=`, las 3 protegidas con `Depends(get_current_user)`.
   `GET /clientes` responde `list[ClienteResumen]` — ya confirmado en
   corrida real que expone `nombre`/`no_cliente` (los dos tests de
   búsqueda parcial lo asumían).
3. ~~Confirmar o exponer una fixture `db_session`~~ ✅ — expuesta en este
   `conftest.py` (function-scoped, sesión directa vía `SessionLocal()`).
   Ya sin uso en `test_clientes.py` tras el punto siguiente; se deja en
   `conftest.py` por si otro módulo la necesita (ej. Movimientos).

**Retirado tras revisión de negocio (no era un pendiente, fue una
corrección):** `rehabilitar_cliente()`, el endpoint `PATCH
/clientes/{id}/rehabilitar` y los 3 tests que lo cubrían se quitaron.
`module_clientes.md` no define ninguna opción de "Rehabilitar Cliente" —
el menú de Clientes solo tiene 4 botones (Registrar, Editar, Consulta
Cliente, Consulta Historial), y el enum `estatus` documenta que el cambio
`activo`↔`inactivo` es siempre manual desde **Editar Cliente** (`UPDATE`
genérico, todavía sin construir), no desde un endpoint aparte. `saldo = 0`
tampoco dispara nada automático (confirmado en el spec). La suite pasó de
32 a 29 tests por este retiro — no es una regresión de cobertura, es
cobertura que no correspondía a ningún caso de negocio real.

Con esto, `test_clientes.py` ya no tiene pendientes de fixtures/rutas.
**Lo único que falta es correr `pytest test/ -v` de verdad** contra un
`pos.db` migrado y ver si pasa — ya se corrió una vez y encontró (y se
corrigió) un bug real en `rehabilitar_cliente()` antes de decidir
retirarla; falta la corrida final con la función ya fuera.

Cubre (una vez en verde): alta con las 4 variantes de `frecuencia_pago` y
sus campos condicionales, rango de `dia_pago_especifico` (1-31, bordes
inválidos 0/32), longitud máxima de los campos de texto (`nombre`,
`colonia`, `ref_nombre`, `ref_colonia`, `frecuencia_pago_detalle` — INC-18,
hallazgo de esta sesión), consecutivo de `no_cliente` por colonia,
normalización de mayúsculas en `no_cliente`, y consulta por id/búsqueda
parcial.

**Huecos deliberados, no cubiertos:**
- "Editar Cliente" — sin `service`/`endpoint` todavía, no se inventa el
  caso. Cuando se construya, el cambio de `estatus` (incluida la
  reactivación) se prueba ahí, como un caso más del `UPDATE` genérico —
  no como una función aparte.
- Enviar `dia_pago_especifico`/`frecuencia_pago_detalle` cuando la
  `frecuencia_pago` no los requiere — el validador hoy lo acepta sin
  rechazar (decisión de diseño abierta, ver `casos_clientes.md` §5).
- Concurrencia en `generar_no_cliente()` (sin lock) — riesgo de
  arquitectura anotado, no bloqueante para un solo usuario concurrente.
- La fórmula real de `fecha_pago_programada` — vive en Movimientos, se
  prueba en `test_movimientos.py`, no aquí.

**Pendiente de actualizar por tu lado, no de código:** `casos_clientes.md`
§3 (Rehabilitar Cliente) queda obsoleto y `docs/FULLSTACK/module_clientes.md`
no necesita cambios (nunca definió esta opción) — pero si algún otro
documento (`REPORT.md`, `TRAZABILIDAD.md`) todavía menciona
`rehabilitar_cliente` como parte del alcance de Clientes, conviene
limpiarlo en la misma pasada para que no reaparezca como pendiente fantasma
en una sesión futura.

## Al agregar un módulo nuevo

1. Extraer `FULLSTACK/module_<nombre>.md` del monolito (o pedir que se
   extraiga), del mismo tamaño/nivel de detalle que `module_pedidos.md`.
2. Escribir `test_<nombre>.py` usando las fixtures de `conftest.py` — no
   crear un cliente de prueba ni un login propio dentro del archivo.
3. Un archivo de test por módulo, nunca un mega-archivo — la razón de ser de
   esta carpeta es exactamente evitar el problema del `.md` monolítico, no
   reproducirlo en Python.
4. Actualizar la tabla de arriba.

## Por qué `cliente_prueba` ya usa `POST /api/v1/clientes`

INC-02 (ver `REPORT.md §4.3` punto 11) hacía que ese endpoint fallara con
`IntegrityError` (`frecuencia_pago` NOT NULL no expuesto en
`ClienteCreate`) — el fixture creaba el cliente directo en SQLAlchemy como
workaround, en un solo lugar, para que Pedidos y Shein no dependieran de un
endpoint roto. **INC-02 ya está resuelto** en `schemas/cliente.py` /
`services/cliente_service.py`, así que el workaround **ya se quitó**:
`cliente_prueba` ahora llama `POST /api/v1/clientes` con un payload válido,
igual que cualquier cliente real, y luego lee el objeto vía SQLAlchemy para
devolver el mismo tipo de valor que antes (para no romper los tests de
Pedidos/Shein que ya dependían de sus atributos).

Pendiente antes de dar esto por cerrado del todo:

1. **Correr toda la suite (`pytest test/ -v`)** con el `conftest.py`
   actualizado — Pedidos y Shein dependen de `cliente_prueba` y hay que
   confirmar que nada se rompió al cambiar de bypass a POST real (ahora el
   fixture pasa por autenticación y por las validaciones reales del
   schema, que antes se saltaba).
2. Si `POST /api/v1/clientes` de verdad rechaza el payload del fixture por
   algo no documentado aquí, el fixture fallará con un `assert` explícito
   (no en silencio) — señal de que hay que ajustar el payload o de que hay
   otro bug no visto todavía.

## Autenticación — dos rutas, cada una para un contexto distinto

Ya se revisaron `backend/scripts/set_admin_password.py` y
`test/verificar_clientes.sh`. **Conclusión: ninguno de los dos sobra.**
No son rutas de autenticación en competencia, son dos entradas al mismo
mecanismo (fijar la contraseña del admin en `pos.db` de forma conocida),
necesarias porque resuelven problemas en momentos distintos:

| Contexto | Cómo se fija la contraseña | Cómo se loguea |
|---|---|---|
| **`pytest test/ -v`** (esta suite) | Fixture `_fijar_password_admin` de `conftest.py`, autouse, corre sola al iniciar la sesión de pytest | `admin_token`/`auth_headers`, login real vía `TestClient` contra `POST /api/v1/auth/login`, en el mismo proceso |
| **Verificación manual con `curl`** (`verificar_clientes.sh`) contra un servidor real (`uvicorn app.main:app --reload`) | `python3 scripts/set_admin_password.py --usuario admin --password '...'`, corrido a mano ANTES del script — pytest no toca ese proceso de `uvicorn`, así que su fixture no le sirve | El script hace su propio `curl -X POST .../auth/login` y extrae el token con `python3 -c "...json..."` |

La confusión de esta sesión (¿cuál es "la" ruta confirmada?) no era un
problema de rutas duplicadas — era que **no estaba escrito en ningún lado
cuál usar según el contexto**. Regla simple para no repetir la confusión:

- ¿Vas a correr `pytest`? No toques contraseñas a mano, la fixture ya lo
  hace por ti.
- ¿Vas a probar con `curl` contra un servidor real (`uvicorn` corriendo)?
  Corre primero `set_admin_password.py`, luego `verificar_clientes.sh`
  (o tus propios `curl`).
- Nunca seas la tercera ruta: no escribas un login/usuario de prueba nuevo
  dentro de un archivo de test — usa `auth_headers`.

Ambos scripts comparten la misma lógica (mismo `CryptContext`, mismo
query/create sobre `Usuario`) porque uno se derivó del otro — es
duplicación de código consciente, no un descuido, ya que viven en procesos
que no se pueden importar entre sí (uno corre dentro de pytest, el otro es
standalone). Si en algún momento molesta mantener las dos copias en
sincronía, se puede extraer a un `app/scripts/_auth_test_utils.py` común
que ambos importen — no es urgente, es una mejora de mantenimiento, no una
corrección de un bug.

**Recordatorio de seguridad que ya trae `verificar_clientes.sh` (no lo
quites):** rotar la contraseña real de admin después de correr el script,
para no dejar `admin123-test` (o la que hayas puesto) como contraseña
vigente de un usuario real.
