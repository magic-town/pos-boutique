# REPORT — Mapa de Estado del Proyecto (pos-boutique)

> **Qué es este documento:** una fotografía del estado actual — decisiones
> tomadas, código implementado, huecos de visibilidad y ruta de trabajo. No es
> spec de negocio (eso es `REGLAS_NEGOCIO.md` / `docs/spec/*.md`).
> Es el documento que permite retomar el trabajo en cualquier sesión nueva sin
> recargar todo el repo. Si solo compartes este archivo, Claude debe poder
> saber qué hacer a continuación; solo pide otro archivo cuando algo no se
> pueda inferir de aquí (ver §6).
>
> **No es bitácora de cambios.** Si un bug se corrige y el estado resultante
> ya queda reflejado en las decisiones/código/tests de este documento, no se
> documenta el historial del fix (qué decía antes, cómo se encontró, qué
> commit lo tocó) — solo el estado actual correcto. La pregunta antes de
> agregar algo aquí es "¿esto lo necesita una sesión nueva para retomar el
> trabajo?", no "¿esto pasó?".

---

## 1. Jerarquía de fuentes

1. **`docs/spec/module_<nombre>.md`** — spec de UI/UX por módulo,
   autoridad máxima si hay contradicción. Para trabajar un módulo específico,
   basta con su `module_<nombre>.md`. Ver `docs/spec/README.md` para el
   mapa y estado de cada uno.
2. **`docs/REGLAS_NEGOCIO.md`** — modelo de datos + reglas de negocio.
3. **`docs/ARQUITECTURA.md`** — decisiones técnicas.
4. **`README.md`** (raíz del repo, no dentro de `docs/`) — orientación y arranque.
5. **`backend/app/models/models.py`** — 15 tablas migradas a `pos.db`,
   alineadas a la spec maestra (verificado directo contra `pos.db`:
   `alembic_version = d4e5f6a7b8c9`, `.tables` confirma las 15, incluidas
   `apartados`/`apartados_articulos`).

**Regla de edición:** el usuario edita los `module_*.md` y
`REGLAS_NEGOCIO.md` directamente; Claude no los reescribe salvo instrucción
explícita del usuario en la sesión.

---

## 2. Estado del modelo de datos (`models.py` / `pos.db`)

15 tablas migradas y alineadas a spec. Cadena de migraciones aplicadas:

> **Verificado directo contra `pos.db`**: `SELECT version_num FROM
> alembic_version` → `d4e5f6a7b8c9`. `.tables` confirma las 15 tablas de
> abajo, incluidas `apartados` y `apartados_articulos`. `PRAGMA table_info`
> confirma la FK `id_apartado` en `movimientos`.

| Revisión              | Alcance                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| `a1b2c3d4e5f6`        | Esquema inicial: 11 tablas. Siembra `configuracion` (métodos de pago, CLABEs, `zona_horaria`) vía `op.bulk_insert` en el propio `upgrade()`.          |
| `b2c3d4e5f6a7`        | Agrega `precios_catalogo` y `shein_pedidos_articulos`; reestructura `shein_pedidos` / `shein_cortes`. |
| `c3d4e5f6a7b8`        | Agrega `dia_pago_especifico` y `frecuencia_pago_detalle` a `clientes`.                                |
| `d4e5f6a7b8c9` (head) | Agrega `apartados`, `apartados_articulos`; agrega FK `id_apartado` a `movimientos`.                   |

### Tablas

| Tabla                     | Módulo          | Notas                                                                        |
| ------------------------- | --------------- | ---------------------------------------------------------------------------- |
| `clientes`                | Clientes        | Incluye `frecuencia_pago`, `dia_pago_especifico`, `frecuencia_pago_detalle`. |
| `pedidos`                 | Pedidos         | Cabecera.                                                                    |
| `pedidos_articulos`       | Pedidos         | Detalle, 1 a 4 artículos, con `rol` (principal/alternativa).                 |
| `precios_catalogo`        | Pedidos         | Catálogo importado de `tabla_precios.ods`. Poblada: 15,564 filas.            |
| `inventario`              | Inventario      | —                                                                            |
| `movimientos`             | Panel Principal | Incluye FK `id_apartado` (nullable, solo para `operacion='apartado'`).      |
| `apartados`               | Panel Principal | Cabecera del lote de apartado. Ver §3.3.                                     |
| `apartados_articulos`     | Panel Principal | Detalle, 1 a N artículos por lote. Ver §3.3.                                 |
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
| ¿Nombres de campo en `Usuario`?                          | `usuario` (no `username`) y `password_hash` (no `hashed_password`). Alineado en modelo, schemas y servicio.                              |
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
| ¿Dónde vive el cálculo de la bandera naranja?            | Fuera de `sincronizar_estatus()` (ese archivo solo deriva `activo`/`inactivo` de `saldo`). Se calcula en lectura, join `clientes` + `apartados`, en el servicio/endpoint de Consulta Cliente / Panel Principal. No se expone en `schemas/cliente.py` hasta que `apartados` esté migrado. |
| ¿Qué pasa al liquidar un apartado?                       | `estatus → liquidado`; artículos `vigente` con `id_producto` en inventario pasan a `vendido`; la bandera se apaga.                       |
| ¿Qué pasa al cancelar un artículo de un apartado?        | `estatus_articulo → cancelado`; si existe en inventario, regresa a `disponible`. No ajusta `saldo_pendiente` ni `clientes.saldo`.        |
| ¿Contado rechaza si el producto no está en inventario?   | No. Sin coincidencia, se captura descripción y precio a mano; sin efecto en inventario.                                                 |
| ¿`precio_producto` capturado a mano se persiste?         | Sí, siempre, en `apartados_articulos.precio_producto`.                                                                                  |
| ¿Cómo se cancela un apartado si el cliente no termina de pagar? | No existe "cancelar el lote". Se cancela artículo por artículo (1, 2, o todos, vía `cancelar_articulo_apartado()`); `apartados` nunca se da de baja como unidad — sigue `abierto` hasta liquidarse por abono. |
| ¿`estatus` del cliente cambia automático al liquidar por abono? | Sí, automático (`sincronizar_estatus()`), nunca manual. `module_movimientos.md` tenía una nota contraria a esto — corrección pendiente de aplicar ahí. |
| ¿`ApartadoCreate` recibe `no_cliente` o `id_cliente`?     | `id_cliente` ya resuelto — consistente con `MovimientoCreate` (mismo campo "No. Cliente" del Panel Principal).                          |
| ¿Se puede rehabilitar `estatus` manualmente?             | No. `estatus` no es campo capturable en ningún formulario/endpoint — se deriva solo de `saldo` vía `sincronizar_estatus()`. `PATCH /{id}/rehabilitar` fue removido y no se repone. |
| ¿Semántica de `saldo_resultante` en movimientos con cliente? | Siempre el saldo TOTAL del cliente tras la operación, nunca un delta — misma regla para `abono` y `apartado`. Es informativo (historial); `cancelar_movimiento()` revierte por delta (`+=`/`-=` según la operación), no depende de este campo. |
| ¿Qué pasa al cancelar un movimiento `apartado` (deshacer el registro recién hecho)? | Se cancela el lote completo: cada artículo `vigente` → `cancelado`, cada producto regresa a inventario, `apartados.estatus → cancelado`. Solo aplica si es la última operación del cliente (nadie ha abonado desde entonces). Distinto del flujo de "no le alcanzó para pagar" (cancelación parcial en cualquier momento vía `cancelar_articulo_apartado()`, sin tocar saldo). |
| ¿A qué estatus regresa un producto al cancelarse (contado o lote de apartado)? | `disponible_c/descuento` si `precio_descuento` no es nulo, si no `disponible` — no siempre `disponible` a secas. |
| ¿Setting tiene capa de servicio propia?                  | No. Módulo simple, sin efectos transversales con otros módulos — se construye como esqueleto para futuras implementaciones. Lógica directa en el endpoint; excepción deliberada al patrón schema/service/endpoint de los demás módulos, no un hueco pendiente. |
| ¿Dónde se siembra la tabla `configuracion`?               | En la propia migración `a1b2c3d4e5f6` (`op.bulk_insert` dentro de `upgrade()`), no en un script aparte — consistente con que el reset de `pos.db` se hace regenerando migraciones (§3: "¿Se conserva data de `pos.db`? No."), sin recurrir a `init_db()` en `lifespan`. |

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

Spec completa de comportamiento: `docs/spec/module_movimientos.md`.
Modelo de datos y reglas: `REGLAS_NEGOCIO.md` §5.

---

## 4. Mapa de archivos

### 4.1 Módulos cerrados (implementados y con test en verde)

| Archivo                                 | Rol                  | Estado                                                                                                                                                |
| --------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/models/models.py`                  | Modelo de datos      | 15 tablas migradas (verificado contra `pos.db`, head `d4e5f6a7b8c9`). Clases correctas y verificadas contra archivo real.|
| `alembic/versions/*.py`                 | 4 migraciones        | Esquema de 15 tablas aplicado, incluida `apartados`/`apartados_articulos`/FK `id_apartado`.                                                           |
| `app/schemas/pedido.py`                 | Schema Pedido        | Cabecera-detalle, valida reglas por `tipo_producto`/`proveedor`.                                                                                      |
| `app/services/pedido_service.py`        | Lógica Pedido        | Lookup de precio, transacciones de devolución/cancelación con reversión condicional de saldo. ||
| `app/api/v1/endpoints/pedidos.py`       | Endpoints Pedido     | 4 flujos probados end-to-end.                                                                                                                         |
| `app/schemas/pedido_shein.py`           | Schema Shein         | `max_length` alineado a `models.py`.                                                                                                                  |
| `app/services/pedido_shein_service.py`  | Lógica Shein         | `monto_pedido` (post-corte, `confirmado`) y `monto_pedido_vigente` (pre-corte) separados. Autoconfirma `vigente` sin cambio de precio al crear corte. |
| `app/api/v1/endpoints/pedidos_shein.py` | Endpoints Shein      | 5 flujos + agregar artículo a pedido existente.                                                                                                       |
| `app/schemas/inventario.py`             | Schema Inventario    | —                                                                                                                                                     |
| `app/services/inventario_service.py`    | Lógica Inventario    | Transiciones validadas, descuento masivo.                                                                                                             |
| `app/api/v1/endpoints/inventario.py`    | Endpoints Inventario | Registrado en `main.py`.                                                                                                                              |
| `app/schemas/cliente.py`                | Schema Cliente       | `telefono`/`ref_telefono` int, `frecuencia_pago` obligatorio, validación condicional, `max_length` alineado. `ClienteRead.bandera_naranja: bool` agregado — no es columna mapeada, debe asignarse al objeto `Cliente` antes de `model_validate()` (lo hace el endpoint). No está en `ClienteResumen`. |
| `app/services/cliente_service.py`       | Lógica Cliente       | Sin referencia a `"liquidado"`. `crear_cliente()` asigna los 3 campos de frecuencia. `calcular_bandera_naranja()` implementada — busca el apartado abierto del cliente y compara contra `fecha_apartado + 1 mes − 5 días`. |
| `app/api/v1/endpoints/clientes.py`      | Endpoints Cliente    | Rutas: `POST /` (asigna `bandera_naranja`), `GET /` (usa `ClienteResumen`, sin bandera), `GET /{id}` (asigna `bandera_naranja`). No existe `/{id}/historial` ni `/{id}/rehabilitar` (ver §3). |
| `app/scripts/importar_precios.py`       | Import de precios    | 15,564 filas insertadas. Solo `INSERT`.                                                                                                               |
| `app/schemas/movimiento.py` | Schema Movimiento | `descripcion` (no `notas`), alineado a `models.py`. Verificado contra archivo real. |
| `app/schemas/apartado.py`               | Schema Apartado       | Cabecera + lista de artículos (`ApartadoCreate`), `id_cliente` resuelto, mínimo $100 validado. Verificado contra archivo real, sin cambios pendientes.  |
| `app/services/movimiento_service.py`    | Lógica Movimientos/Apartado | `contado`/`abono`/`gasto` completos. `crear_apartado()`, `obtener_apartado_abierto()`, `cancelar_articulo_apartado()`. `cancelar_movimiento()` revierte inventario en `contado`, revierte saldo por delta (`+=`/`-=`, no depende de `saldo_resultante`) en `abono`/`apartado`, y cancela el lote completo en `apartado` (ver §3). Verificado contra archivo real y contra `test_movimientos.py` (28/28 en verde). |
| `app/models/models.py` (`Usuario`)      | Modelo Auth           | Campos `usuario` (no `username`) y `password_hash` (no `hashed_password`); `activo: Integer`.                                                        |
| `app/schemas/usuario.py`                | Schema Auth           | `UsuarioCreate`: `usuario` 4-16 caracteres sin espacios, `password` 4-10 caracteres con al menos una mayúscula, `rol` en (`estandar`, `admin`) — alineado a `module_setting.md`. `UsuarioRead` expone `usuario` y `activo: int`, `from_attributes = True`.  |
| `app/schemas/token.py`                  | Schema Auth            | `Token` (`access_token`, `token_type="bearer"`), `TokenData` (`usuario`, `rol`), ambos opcionales salvo `access_token`.                              |
| `app/services/auth_service.py`          | Lógica Auth            | `hash_password()`/`verificar_password()` (bcrypt), `crear_token()` (JWT, expira según `settings.TOKEN_EXPIRY_HOURS`), `autenticar_usuario()`, `crear_usuario()`, `get_current_user()` como dependency de FastAPI. `SECRET_KEY`/`ALGORITHM`/`TOKEN_EXPIRY_HOURS` vienen de `app/core/config.py`. |
| `app/api/v1/endpoints/auth.py`          | Endpoint Auth          | `POST /auth/login` (`OAuth2PasswordRequestForm`), retorna `Token`. Mismo status/mensaje para usuario inexistente y password incorrecto.              |
| `app/api/v1/endpoints/movimientos.py`   | Endpoint Movimientos | `POST /movimientos`, `GET /movimientos?id_cliente=`, `DELETE /movimientos/{id}/cancelar` — los 3 con `Depends(get_current_user)`. Verificado contra archivo real. **No expone `crear_apartado()`** — no hay endpoint para registrar un apartado todavía, solo capa de servicio (`app/api/v1/endpoints/apartados.py` sigue sin existir). |
| `app/db/database.py`                    | Conexión BD          | SQLAlchemy síncrono.                                                                                                                                  |
| `app/core/config.py`                    | Configuración        | Solo `DATABASE_URL`. Sin `AUTH_ENABLED`.                                                                                                              |
| `app/main.py`                           | Bootstrap FastAPI    | Sin `init_db()`. 6 routers (incluye Setting). CORS `localhost:5173`.                                                                                  |
| `app/schemas/__init__.py`               | Re-exports           | Nombres de Shein corregidos.                                                                                                                          |
| `requirements.txt`                      | Dependencias prod    | Incluye `python-jose`, `passlib`/`bcrypt`, `pandas`, `odfpy`.                                                                                         |
| `requirements-dev.txt`                  | Dependencias test    | `pytest`/`httpx`.                                                                                                                                     |
| `app/schemas/setting.py`                | Schema Setting        | `ConfiguracionRead`/`ConfiguracionUpdate`, `UsuarioCambiarPassword` (misma regla de password que `usuario.py`, duplicada a propósito para MVP), `UsuarioCambiarRol` (`estandar`/`admin`).                                                          |
| `app/api/v1/endpoints/setting.py`       | Endpoints Setting     | `POST /setting/usuarios`, `PATCH /usuarios/{id}/password`, `PATCH /usuarios/{id}/rol`, `GET /zona-horaria` (solo lectura), `GET /configuracion`, `PATCH /configuracion/{clave}` (valida `'0'`/`'1'` en métodos de pago; `pago_efectivo_activo` rechaza `'0'` con 409). Todos con `Depends(get_current_user)`. Sin `setting_service.py` — lógica directa en el endpoint (ver §3, excepción deliberada, módulo simple sin efectos transversales). |

### 4.2 Tests

| Test                      | Módulo     | Estado           |
| ------------------------- | ---------- | ---------------- |
| `test/test_pedidos.py`    | Pedidos    | ✅ en verde       |
| `test/test_inventario.py` | Inventario | ✅ 19/19 en verde |
| `test/test_shein.py`      | Shein      | ✅ 28/28 en verde |
| `test/test_clientes.py`   | Clientes   | ✅ 43/43 en verde |
| `test/test_movimientos.py`| Movimientos| ✅ 28/28 en verde |
| `test/test_apartados.py`  | Apartado   | ✅ 12/12 en verde |
| `test/test_autenticacion.py` | Auth    | ✅ 59/59 en verde |
| `test/test_recargas.py`  | Recargas    | ✅ 17/17 en verde |
| `test/test_setting.py`   | Setting     | ✅ 26/26 en verde |

### 4.3 Sin código todavía

| Módulo                | Spec disponible                      |
| --------------------- | ------------------------------------- |
| Consulta Global       | `module_consulta.md` — no existe.     |

---

## 5. Orden de prioridad (jerarquía → código)

### Nivel 1 — Modelo de datos

✅ Cerrado. `models.py` y `pos.db` alineados a §3.3, head `d4e5f6a7b8c9`.

### Nivel 2 — Schemas

4. ✅ `ApartadoCreate` (cabecera + lista de artículos) — reemplaza el uso de
   `MovimientoCreate` para la operación `apartado`. Implementado en
   `app/schemas/apartado.py`.
5. ✅ Cerrado — `notas` → `descripcion` en `MovimientoCreate`/`MovimientoRead`, alineado a `models.py`. Verificado contra archivo real.
5b. ✅ Cerrado — `operacion` en `MovimientoCreate` rechaza `Operacion.apartado` vía `field_validator`; esa operación entra exclusivamente por `ApartadoCreate`.
6. ✅ Cerrado — `bandera_naranja: bool` expuesta en `ClienteRead`, calculada en el endpoint antes de serializar.

### Nivel 3 — Servicios

7. ✅ Cerrado — `calcular_bandera_naranja()` en `cliente_service.py`. No requirió tocar `sincronizar_estatus()` (confirma lo ya documentado en §3: el cálculo vive fuera de esa función).
8. ✅ Cerrado — implementado directo en `movimiento_service.py` (`crear_apartado()`, `obtener_apartado_abierto()`, `cancelar_articulo_apartado()`). No se separó en `apartado_service.py`.
9. ✅ Cerrado — `contado`/`abono`/`gasto` completos en `movimiento_service.py`. `cancelar_movimiento()` revierte inventario en `contado`, revierte saldo por delta en `abono`/`apartado`, y cancela el lote completo en `apartado` (ver §3 para el detalle de comportamiento).

### Nivel 4 — Tests

✅ Cerrado.

10. ✅ Cerrado — `test_apartados.py` — creado (ver §4.2).
11. ✅ Cerrado — `test_movimientos.py` (`contado`/`abono`/`gasto`/`apartado`, 28 casos, corrida completa en verde).
12. ✅ Cerrado — revisión de `test_clientes.py` (bandera naranja): agregada la sección 3 (`TestSumarUnMes`, `TestCalcularBanderaNaranja`, `TestBanderaNaranjaEndpoint`) — umbral de 5 días, clamp de fin de mes, y que un apartado no-`abierto` apague la bandera aunque la fecha esté vencida. Corrida completa en verde (ver §4.2).

### Pasos restantes de la ruta general (sin cambio de alcance)

13. ✅ Cerrado — Auth (§4.1). `test_autenticacion.py` creado y corrido completo en verde (ver §4.2).
14. ✅ Cerrado — `test_recargas.py` — creado (ver §4.2).
15. ✅ Cerrado — Setting/Configuración (esqueleto MVP, sin permisos diferenciados todavía). `test_setting.py` creado, 26/26 en verde (ver §4.2).
16. **Construir Consulta Global** (3 vistas de solo lectura).
17. **Checklist real** — criterio de completado = pipeline + test.

---

## 6. Cómo usar este documento en una sesión nueva

Si retomas el trabajo y solo compartes `REPORT.md`, ya se sabe: qué está
decidido (§3), el estado del modelo de datos (§2), qué evidencia hay de cada
archivo (§4), y el orden de prioridad completo (§5).

No hace falta resubir los archivos de §4.1 — solo los que se vayan a tocar
o cualquier archivo que haya cambiado desde la última actualización.

**Siguiente paso inmediato:** el punto 15 (Setting/Configuración) quedó cerrado por completo — `test_setting.py` en verde, 26/26 (ver §4.2). Todos los módulos existentes tienen test en verde. El siguiente punto de la ruta general es el **punto 16 — construir Consulta Global** (spec completa en `module_consulta.md`, ver §4.3).
