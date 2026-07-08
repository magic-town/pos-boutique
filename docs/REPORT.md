# REPORT — Mapa de Estado del Proyecto (pos-boutique)

> **Qué es este documento:** una fotografía del estado actual — decisiones
> tomadas, código implementado, huecos de visibilidad y ruta de trabajo. No es
> spec de negocio (eso es `REGLAS_NEGOCIO.md` / `docs/FULL_STACK/*.md`).
> Es el documento que permite retomar el trabajo en cualquier sesión nueva sin
> recargar todo el repo. Si solo compartes este archivo, Claude debe poder
> saber qué hacer a continuación; solo pide otro archivo cuando algo no se
> pueda inferir de aquí (ver §6).

---

## 1. Jerarquía de fuentes

1. **`docs/FULL_STACK/module_<nombre>.md`** — spec de UI/UX por módulo,
   autoridad máxima si hay contradicción. Para trabajar un módulo específico,
   basta con su `module_<nombre>.md`. Ver `docs/FULL_STACK/README.md` para el
   mapa y estado de cada uno.
2. **`docs/REGLAS_NEGOCIO.md`** — modelo de datos + reglas de negocio.
3. **`docs/ARQUITECTURA.md`** — decisiones técnicas.
4. **`docs/README.md`** — orientación y arranque.
5. **`backend/app/models/models.py`** — implementado y migrado. 13 tablas en
   `pos.db`, alineadas a la spec maestra. 2 tablas adicionales (`apartados`,
   `apartados_articulos`) con diseño cerrado, pendientes de reflejarse aquí.

**Regla de edición:** el usuario edita los `module_*.md` y
`REGLAS_NEGOCIO.md` directamente; Claude no los reescribe salvo instrucción
explícita del usuario en la sesión.

---

## 2. Estado del modelo de datos (`models.py` / `pos.db`)

13 tablas migradas y alineadas a spec, más 2 tablas con diseño cerrado
pendientes de migración (`apartados`, `apartados_articulos` — ver §3.3).
Cadena de migraciones aplicadas:

| Revisión              | Alcance                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| `a1b2c3d4e5f6`        | Esquema inicial: 11 tablas.                                                                           |
| `b2c3d4e5f6a7`        | Agrega `precios_catalogo` y `shein_pedidos_articulos`; reestructura `shein_pedidos` / `shein_cortes`. |
| `c3d4e5f6a7b8` (head) | Agrega `dia_pago_especifico` y `frecuencia_pago_detalle` a `clientes`.                                |
| *(pendiente)*         | Agregar `apartados`, `apartados_articulos`; agregar FK `id_apartado` a `movimientos`.                 |

### Tablas

| Tabla                     | Módulo          | Notas                                                                        |
| ------------------------- | --------------- | ---------------------------------------------------------------------------- |
| `clientes`                | Clientes        | Incluye `frecuencia_pago`, `dia_pago_especifico`, `frecuencia_pago_detalle`. |
| `pedidos`                 | Pedidos         | Cabecera.                                                                    |
| `pedidos_articulos`       | Pedidos         | Detalle, 1 a 4 artículos, con `rol` (principal/alternativa).                 |
| `precios_catalogo`        | Pedidos         | Catálogo importado de `tabla_precios.ods`. Poblada: 15,564 filas.            |
| `inventario`              | Inventario      | —                                                                            |
| `movimientos`             | Panel Principal | Falta agregar FK `id_apartado` (nullable, solo para `operacion='apartado'`). |
| `apartados`               | Panel Principal | **Diseño cerrado, sin migrar.** Cabecera del lote de apartado. Ver §3.3.     |
| `apartados_articulos`     | Panel Principal | **Diseño cerrado, sin migrar.** Detalle, 1 a N artículos por lote. Ver §3.3. |
| `shein_clientes`          | Shein           | Independiente de `clientes`.                                                 |
| `shein_pedidos`           | Shein           | Cabecera: `id_shein_cliente`, `id_shein_corte`, `estatus_pago`, `fecha`.     |
| `shein_pedidos_articulos` | Shein           | Detalle, 1 a 4 artículos, sin alternativa.                                   |
| `shein_cortes`            | Shein           | `suma_pedidos`, `total_ticket`, `cupon = suma_pedidos - total_ticket`.       |
| `recargas`                | Recargas        | —                                                                            |
| `usuarios`                | Autenticación   | —                                                                            |
| `configuracion`           | Configuración   | —                                                                            |

Diseño completo de columnas y tipos: `REGLAS_NEGOCIO.md`.

---

## 3. Decisiones cerradas (no reabrir salvo nueva evidencia)

| Decisión                                                 | Resultado                                                                                                                               |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| ¿Se conserva data de `pos.db`?                           | No. Reset limpio; esquema nace de `models.py` vía Alembic.                                                                              |
| ¿Async o sync en SQLAlchemy?                             | Síncrono.                                                                                                                               |
| ¿Nombres de campo en `Usuario`?                          | `usuario` (no `username`) y `password_hash` (no `hashed_password`). **`schemas/usuario.py` sigue sin alinearse** — pendiente §5 paso 15. |
| ¿`pedidos` plano o cabecera-detalle?                     | Cabecera-detalle.                                                                                                                       |
| ¿Shein comparte tabla de clientes?                       | No. `shein_clientes` independiente.                                                                                                     |
| ¿`shein_pedidos` plano o cabecera-detalle?               | Cabecera-detalle, sin alternativa.                                                                                                      |
| ¿Cómo se calcula el `cupon` de Shein?                    | `cupon = suma_pedidos - total_ticket`.                                                                                                  |
| ¿Variación de precio Shein?                              | Cualquier variación exige notificación y confirmación del cliente.                                                                      |
| ¿`estatus_pago` en Shein?                                | En `shein_pedidos`, por pedido.                                                                                                         |
| ¿Si todos los artículos Shein se cancelan?               | Pedido no recibe `id_shein_corte` ni `estatus_pago`.                                                                                    |
| ¿`init_db.py` en `lifespan`?                             | No. Alembic es la única fuente de esquema.                                                                                              |
| ¿`precios_catalogo` en SQLite?                           | Sí. Tabla migrada y poblada (15,564 filas).                                                                                             |
| ¿Sincronización de `tabla_precios.ods`?                  | Script manual `importar_precios.py`. Solo `INSERT`.                                                                                     |
| ¿Columnas de `precios_catalogo`?                         | Todas las del `.ods`, incluidas auxiliares no usadas por el POS.                                                                        |
| ¿Resolución de precio de artículo?                       | `SELECT precio_venta WHERE proveedor = :p AND id_producto = :id ORDER BY fecha_catalogo DESC LIMIT 1`.                                  |
| ¿`id_producto` es único por proveedor?                   | No. Desempate por `MAX(fecha_catalogo)`.                                                                                                |
| ¿Cuándo sube el saldo de un artículo de pedido?          | Al marcarse `en_almacen`.                                                                                                               |
| ¿Columna `redondea` del `.ods`?                          | Descartada.                                                                                                                             |
| ¿Valores no numéricos en `pagina`?                       | `NULL`.                                                                                                                                 |
| ¿Cuántas alternativas puede tener un artículo principal? | 0–1, salvo `Price_Shoes` (hasta 3).                                                                                                     |
| ¿Cómo se verifica un módulo?                             | `backend/test/` (pytest + `TestClient`), un archivo por módulo.                                                                         |
| ¿`inventario_bz.ods` sincroniza cambios?                 | Solo `INSERT`. Sin clave natural para UPSERT.                                                                                           |
| ¿Descuento de Inventario?                                | Solo en el sistema (`POST /inventario/descuento-masivo`).                                                                               |
| ¿Segmento de descuento masivo?                           | Filtro por `categoria`/`tipo_producto`/`marca`/`talla`/`color`, y/o selección manual de `ids_producto`.                                 |
| ¿Apartado modela plano o cabecera-detalle?               | Cabecera-detalle: `apartados` + `apartados_articulos`, mismo patrón que Pedidos.                                                        |
| ¿Un cliente puede tener varios apartados abiertos?       | No. Solo una `fecha_apartado` activa a la vez; puede agrupar varios artículos bajo esa misma fecha.                                     |
| ¿`id_producto` obligatorio en Apartado?                  | No. Opcional por artículo. Con coincidencia en `inventario`, autollena `precio_producto`; sin coincidencia, se captura a mano.           |
| ¿El primer pago mínimo aplica por artículo o por lote?   | Por lote completo (`monto_primer_pago`, mínimo $100), no por artículo.                                                                  |
| ¿Cómo se calcula `saldo_pendiente` del apartado?         | `Σ(precio_producto del lote) − monto_primer_pago`. Se suma al `saldo` del cliente.                                                       |
| ¿Semilla de la bandera naranja?                          | `apartados.fecha_apartado`. Independiente de `fecha_pago_programada` y de las banderas amarilla/roja.                                   |
| ¿La bandera naranja se persiste?                         | No. Se calcula al vuelo: activa si `estatus='abierto'` y faltan ≤5 días para cumplirse 1 mes desde `fecha_apartado`.                     |
| ¿Qué pasa al liquidar un apartado?                       | `estatus → liquidado`; artículos `vigente` con `id_producto` en inventario pasan a `vendido`; la bandera se apaga.                       |
| ¿Qué pasa al cancelar un artículo de un apartado?        | `estatus_articulo → cancelado`; si existe en inventario, regresa a `disponible`. No ajusta `saldo_pendiente` ni `clientes.saldo`.        |
| ¿Contado rechaza si el producto no está en inventario?   | No. Sin coincidencia, se captura descripción y precio a mano; sin efecto en inventario.                                                 |
| ¿`precio_producto` capturado a mano se persiste?         | Sí, siempre, en `apartados_articulos.precio_producto`.                                                                                  |

### 3.1 Diseño de `precios_catalogo`

```
precios_catalogo
├── id_precio         Integer, PK AUTOINCREMENT
├── proveedor         Enum (Price_Shoes | Pakar | Cklass)
├── id_producto       String(12)
├── precio_venta      Integer
├── fecha_catalogo    Date
├── catalogo          String       (auxiliar)
├── temporada         String       (auxiliar)
├── pagina            Integer      (auxiliar)
└── precio_base       Integer      (auxiliar)
```

Mapeo de columnas por pestaña del `.ods`:

| Pestaña       | Columna id | Columna precio | Columna base  |
| ------------- | ---------- | -------------- | ------------- |
| `price_shoes` | `ID`       | `precio_venta` | `Sug_credito` |
| `pakar`       | `CÓDIGO`   | `precio_venta` | `2 PAGO`      |
| `cklass`      | `modelo`   | `precio_venta` | `precio_base` |

### 3.2 Diseño de tablas Shein

```
shein_pedidos                              (cabecera)
├── id_shein_pedido    Integer, PK
├── id_shein_cliente   FK → shein_clientes
├── id_shein_corte     FK → shein_cortes, nullable
├── estatus_pago       Enum (pago_pendiente | pagado), nullable
└── fecha              Date

shein_pedidos_articulos                    (detalle)
├── id_shein_articulo  Integer, PK
├── id_shein_pedido    FK → shein_pedidos
├── id_articulo        String(20), nullable
├── producto           String(60) NOT NULL
├── tipo_producto      Enum (Nacional | Importado)
├── monto              Float NOT NULL
├── monto_vigente      Float, nullable
└── estatus_articulo   Enum (vigente | confirmado | cancelado)

shein_cortes
├── id_shein_corte     Integer, PK
├── fecha_corte        Date
├── total_pedidos      Integer
├── suma_pedidos       Float
├── total_ticket       Float        (captura manual, pago en OXXO)
└── cupon              Float        (= suma_pedidos - total_ticket)
```

### 3.3 Diseño de Apartado (cabecera-detalle)

```
apartados                                  (cabecera)
├── id_apartado         Integer, PK
├── id_cliente          FK → clientes
├── fecha_apartado      DateTime          (semilla de la bandera naranja)
├── monto_primer_pago   Float             (mínimo $100, por lote — no por artículo)
├── saldo_pendiente     Float             (Σ precio_producto − monto_primer_pago)
└── estatus             Enum (abierto | liquidado)

apartados_articulos                        (detalle, 1 a N artículos por lote)
├── id_apartado_articulo  Integer, PK
├── id_apartado           FK → apartados
├── id_producto           FK → inventario, nullable
├── precio_producto       Float           (autollenado o manual, siempre persistido)
└── estatus_articulo      Enum (vigente | vendido | cancelado)

movimientos.id_apartado   FK → apartados, nullable
                          (enlaza el evento de caja del primer pago con el lote)
```

Spec completa de comportamiento: `docs/FULL_STACK/module_movimientos.md`.
Modelo de datos y reglas: `REGLAS_NEGOCIO.md` §5.

---

## 4. Mapa de archivos

### 4.1 Módulos cerrados (implementados y con test en verde)

| Archivo                                 | Rol                  | Estado                                                                                                                                                |
| --------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/models/models.py`                  | Modelo de datos      | 13 tablas, alineado a spec. Head: `c3d4e5f6a7b8`. No incluye aún `apartados`/`apartados_articulos`.                                                  |
| `alembic/versions/*.py`                 | 3 migraciones        | Esquema completo aplicado. Falta la migración de Apartado.                                                                                           |
| `app/schemas/pedido.py`                 | Schema Pedido        | Cabecera-detalle, valida reglas por `tipo_producto`/`proveedor`.                                                                                      |
| `app/services/pedido_service.py`        | Lógica Pedido        | Lookup de precio, transacciones de devolución/cancelación con reversión condicional de saldo. **No compartido en esta sesión — ver §5 Nivel 0.**     |
| `app/api/v1/endpoints/pedidos.py`       | Endpoints Pedido     | 4 flujos probados end-to-end.                                                                                                                         |
| `app/schemas/pedido_shein.py`           | Schema Shein         | `max_length` alineado a `models.py`.                                                                                                                  |
| `app/services/pedido_shein_service.py`  | Lógica Shein         | `monto_pedido` (post-corte, `confirmado`) y `monto_pedido_vigente` (pre-corte) separados. Autoconfirma `vigente` sin cambio de precio al crear corte. |
| `app/api/v1/endpoints/pedidos_shein.py` | Endpoints Shein      | 5 flujos + agregar artículo a pedido existente.                                                                                                       |
| `app/schemas/inventario.py`             | Schema Inventario    | —                                                                                                                                                     |
| `app/services/inventario_service.py`    | Lógica Inventario    | Transiciones validadas, descuento masivo.                                                                                                             |
| `app/api/v1/endpoints/inventario.py`    | Endpoints Inventario | Registrado en `main.py`.                                                                                                                              |
| `app/schemas/cliente.py`                | Schema Cliente       | `telefono`/`ref_telefono` int, `frecuencia_pago` obligatorio, validación condicional, `max_length` alineado. **No compartido en esta sesión — ver §5 Nivel 0.** |
| `app/services/cliente_service.py`       | Lógica Cliente       | Sin referencia a `"liquidado"`. `crear_cliente()` asigna los 3 campos de frecuencia. **No compartido en esta sesión — pendiente confirmar `sincronizar_estatus()` y diseñar la bandera naranja ahí. Ver §5 Nivel 0.** |
| `app/api/v1/endpoints/clientes.py`      | Endpoints Cliente    | Rutas: `POST /`, `GET /`, `GET /{id}`, `GET /{id}/historial`, `PATCH /{id}/rehabilitar`.                                                              |
| `app/scripts/importar_precios.py`       | Import de precios    | 15,564 filas insertadas. Solo `INSERT`.                                                                                                               |
| `app/db/database.py`                    | Conexión BD          | SQLAlchemy síncrono.                                                                                                                                  |
| `app/core/config.py`                    | Configuración        | Solo `DATABASE_URL`. Sin `AUTH_ENABLED`.                                                                                                              |
| `app/main.py`                           | Bootstrap FastAPI    | Sin `init_db()`. 5 routers. CORS `localhost:5173`.                                                                                                    |
| `app/schemas/__init__.py`               | Re-exports           | Nombres de Shein corregidos.                                                                                                                          |
| `requirements.txt`                      | Dependencias prod    | Incluye `python-jose`, `passlib`/`bcrypt`, `pandas`, `odfpy`.                                                                                         |
| `requirements-dev.txt`                  | Dependencias test    | `pytest`/`httpx`.                                                                                                                                     |

### 4.2 Tests

| Test                      | Módulo     | Estado           |
| ------------------------- | ---------- | ---------------- |
| `test/test_pedidos.py`    | Pedidos    | ✅ en verde       |
| `test/test_inventario.py` | Inventario | ✅ 19/19 en verde |
| `test/test_shein.py`      | Shein      | ✅ 28/28 en verde |
| `test/test_clientes.py`   | Clientes   | ✅ en verde       |

### 4.3 Movimientos — estado de código y alcance

**Confirmado en el código actual** (`movimiento_service.py`, `schemas/movimiento.py`
recibidos en esta sesión):

| Punto                                          | Ubicación                                       | Descripción                                                                                                    |
| ----------------------------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `notas` → `descripcion`                        | `movimiento_service.py`, `schemas/movimiento.py` | Columna inexistente en `models.py` (la real es `descripcion`). Crash en el 100% de las llamadas.                |
| Sobrescritura de saldo en apartado              | `movimiento_service.py`, rama `apartado`         | `cliente.saldo = saldo_resultante` en vez de `+=`. Con el diseño cerrado (§3.3), además debe cargar `Σ precio_producto` del lote, no solo el `monto` capturado. |
| Sin mínimo $100 en apartado                     | `movimiento_service.py`, rama `apartado`         | Solo valida `monto < 0`. El mínimo aplica por lote (`monto_primer_pago`), no por artículo.                       |
| Sin rama de `gasto`                             | `movimiento_service.py`                          | No existe validación de `descripcion` obligatoria ni ninguna otra regla de esa operación.                        |
| `cancelar_movimiento()` no distingue operación  | `movimiento_service.py`                          | Busca saldo anterior sin filtrar por tipo. Requiere rediseño completo (cancelación de apartado ahora es por artículo — ver §3.3). |

**Sin confirmar — requiere re-verificación con `cliente_service.py`:**

| Punto                      | Estado                                                                                                                                                |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `"liquidado"` inexistente  | No se encontró esta asignación en el `movimiento_service.py` recibido en esta sesión. `cliente_service.py` (§4.1) tampoco lo referencia. Puede estar resuelto, o vivir dentro de `sincronizar_estatus()` — no compartido aún. |

**Fuera del alcance de un bug-fix puntual — funcionalidad sin construir:**

| Punto                                | Ubicación                                          | Descripción                                                                                                    |
| -------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Integración con `inventario`          | `movimiento_service.py`                            | Ninguna rama consulta ni actualiza `inventario`. La requieren tanto `contado` (origen Inventario) como `apartado`. |
| Apartado como cabecera-detalle        | `models.py`, `schemas/movimiento.py`, `movimiento_service.py` | No existen `apartados` / `apartados_articulos`. Diseño cerrado en §3.3; falta migración + schema + servicio.   |
| Rama `contado` completa               | `movimiento_service.py`                            | Sin validación de origen (catálogo/inventario) ni efecto en stock.                                             |
| Reversión de inventario en cancelación | `movimiento_service.py`                            | `cancelar_movimiento()` no toca `inventario`.                                                                  |

### 4.4 Módulos con bugs activos — Auth

| Bug                              | Archivo                  | Descripción                                                                                        |
| -------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------- |
| `UsuarioRead.username`           | `schemas/usuario.py` L28 | Campo `username` no existe en modelo (es `usuario`). `from_attributes = True` rompe serialización. |
| `UsuarioRead.activo: str`        | `schemas/usuario.py` L30 | Debería ser `int` (modelo tiene `Integer`).                                                        |
| `auth.py` usa `usuario.username` | `endpoints/auth.py`      | Rompe con el rename a `usuario`.                                                                   |
| `TokenData.username`             | `schemas/token.py` L13   | Nombre interno, no mapea vía `from_attributes`. Severidad baja.                                    |

> `auth_service.py` ya usa `usuario.usuario` internamente (L59, L69).
> `get_current_user()` (L81) lee `token_data.username` (de `TokenData`).
> `crear_token()` (L73) pone `usuario` en clave `sub` del JWT.

### 4.5 Sin código todavía

| Módulo                | Spec disponible                      |
| --------------------- | ------------------------------------- |
| Recargas Telefónicas  | `module_recargas.md` — completa.     |
| Setting/Configuración | `module_setting.md` — esqueleto MVP. |
| Consulta Global       | `module_consulta.md` — completa.     |

---

## 5. Orden de prioridad (jerarquía → código)

### Nivel 0 — Bloqueante: archivos pendientes de compartir

Sin estos, el Nivel 1 no puede cerrarse con certeza:

| Archivo                    | Para qué                                                                                          |
| --------------------------- | -------------------------------------------------------------------------------------------------- |
| `module_pedidos.md`        | Confirmar/replicar el patrón cabecera-detalle que ya usa Apartado.                                |
| `pedido_service.py`        | Lógica real de carga a saldo por artículo — no duplicar un criterio distinto al ya probado.        |
| `module_clientes.md`       | Definición vigente de banderas amarilla/roja y `fecha_pago_programada`.                            |
| `cliente_service.py`       | Confirmar `sincronizar_estatus()` y decidir dónde vive el cálculo de la bandera naranja.            |
| `schemas/cliente.py`       | Si la bandera naranja se expone en la lectura de cliente.                                          |

### Nivel 1 — Modelo de datos

1. `models.py`: agregar `Apartado`, `ApartadoArticulo`; agregar FK `id_apartado` a `Movimiento`.
2. Migración Alembic correspondiente.

### Nivel 2 — Schemas

3. `ApartadoCreate` (cabecera + lista de artículos) — reemplaza el uso de `MovimientoCreate` para la operación `apartado`.
4. `MovimientoCreate` simplificado — cubre `contado`/`abono`/`gasto`; `notas` → `descripcion`.
5. `schemas/cliente.py` — si aplica exponer la bandera naranja (depende del Nivel 0).

### Nivel 3 — Servicios

6. `cliente_service.py`: cálculo de bandera naranja; revisión de `sincronizar_estatus()` (depende del Nivel 0).
7. Nuevo `apartado_service.py` (o extensión de `movimiento_service.py`):
   - Registrar: multi-artículo + integración con inventario + validación de primer pago mínimo por lote.
   - Liquidar: dispara cuando `saldo_pendiente` llega a 0 vía abono — artículos vigentes con match en inventario pasan a `vendido`, apaga la bandera.
   - Cancelar artículo: revierte inventario a `disponible` si existe, sin ajustar `saldo_pendiente` ni `clientes.saldo`.
8. `movimiento_service.py`:
   - `contado`: integración con inventario condicional a la existencia del producto.
   - `abono`: `saldo -=`, interacción con `apartados.saldo_pendiente` si hay un apartado abierto.
   - `gasto`: validar `descripcion` obligatoria.
   - `cancelar_movimiento()` genérico para estas tres operaciones (la cancelación de apartado vive en el punto 7).

### Nivel 4 — Tests

9. `test_apartados.py` (nuevo).
10. `test_movimientos.py` (contado/abono/gasto).
11. Revisión de `test_clientes.py` (bandera naranja).

### Nivel 5 — Documentación

12. ✅ `module_movimientos.md` — reescrito con el diseño cabecera-detalle de Apartado.
13. ✅ `REGLAS_NEGOCIO.md` (§1, §2, §5, §11) — reescrito.
14. ✅ Este archivo (`REPORT.md`) — actualizado en esta revisión.

### Pasos restantes de la ruta general (sin cambio de alcance)

15. **Corregir Auth** (§4.4): rename `username` → `usuario` en `UsuarioRead`; `activo: str` → `activo: int`; alinear `endpoints/auth.py`; evaluar `TokenData.username` (severidad baja).
16. **Construir Recargas** desde cero.
17. **Construir Setting/Configuración** (esqueleto MVP — sin permisos diferenciados todavía).
18. **Construir Consulta Global** (3 vistas de solo lectura).
19. **Checklist real** — criterio de completado = pipeline + test.

---

## 6. Cómo usar este documento en una sesión nueva

Si retomas el trabajo y solo compartes `REPORT.md`, ya se sabe: qué está
decidido (§3), el estado del modelo de datos (§2), qué evidencia hay de cada
archivo (§4), qué está confirmado/pendiente de verificar en Movimientos
(§4.3), y el orden de prioridad completo (§5).

No hace falta resubir los archivos de §4.1 — solo los que se vayan a tocar
o cualquier archivo que haya cambiado desde la última actualización.

**Siguiente paso inmediato:** §5 Nivel 0 — compartir `module_pedidos.md`,
`pedido_service.py`, `module_clientes.md`, `cliente_service.py` y
`schemas/cliente.py` para poder cerrar el Nivel 1 (modelo de datos) de
Apartado sin reinventar un patrón distinto al que ya usa Pedidos.
