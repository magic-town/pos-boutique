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
   `pos.db`, alineadas a la spec maestra.

**Regla de edición:** el usuario edita los `module_*.md` y
`REGLAS_NEGOCIO.md` directamente; Claude no los reescribe salvo instrucción
explícita del usuario en la sesión.

---

## 2. Estado del modelo de datos (`models.py` / `pos.db`)

13 tablas, todas migradas y alineadas a spec. Cadena de migraciones:

| Revisión              | Alcance                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| `a1b2c3d4e5f6`        | Esquema inicial: 11 tablas.                                                                           |
| `b2c3d4e5f6a7`        | Agrega `precios_catalogo` y `shein_pedidos_articulos`; reestructura `shein_pedidos` / `shein_cortes`. |
| `c3d4e5f6a7b8` (head) | Agrega `dia_pago_especifico` y `frecuencia_pago_detalle` a `clientes`.                                |

### Tablas

| Tabla                     | Módulo          | Notas                                                                        |
| ------------------------- | --------------- | ---------------------------------------------------------------------------- |
| `clientes`                | Clientes        | Incluye `frecuencia_pago`, `dia_pago_especifico`, `frecuencia_pago_detalle`. |
| `pedidos`                 | Pedidos         | Cabecera.                                                                    |
| `pedidos_articulos`       | Pedidos         | Detalle, 1 a 4 artículos, con `rol` (principal/alternativa).                 |
| `precios_catalogo`        | Pedidos         | Catálogo importado de `tabla_precios.ods`. Poblada: 15,564 filas.            |
| `inventario`              | Inventario      | —                                                                            |
| `movimientos`             | Panel Principal | —                                                                            |
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
| ¿Nombres de campo en `Usuario`?                          | `usuario` (no `username`) y `password_hash` (no `hashed_password`). **`schemas/usuario.py` sigue sin alinearse** — pendiente §5 paso 3. |
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

---

## 4. Mapa de archivos

### 4.1 Módulos cerrados (implementados y con test en verde)

| Archivo                                 | Rol                  | Estado                                                                                                                                                |
| --------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/models/models.py`                  | Modelo de datos      | 13 tablas, alineado a spec. Head: `c3d4e5f6a7b8`.                                                                                                     |
| `alembic/versions/*.py`                 | 3 migraciones        | Esquema completo aplicado.                                                                                                                            |
| `app/schemas/pedido.py`                 | Schema Pedido        | Cabecera-detalle, valida reglas por `tipo_producto`/`proveedor`.                                                                                      |
| `app/services/pedido_service.py`        | Lógica Pedido        | Lookup de precio, transacciones de devolución/cancelación con reversión condicional de saldo.                                                         |
| `app/api/v1/endpoints/pedidos.py`       | Endpoints Pedido     | 4 flujos probados end-to-end.                                                                                                                         |
| `app/schemas/pedido_shein.py`           | Schema Shein         | `max_length` alineado a `models.py`.                                                                                                                  |
| `app/services/pedido_shein_service.py`  | Lógica Shein         | `monto_pedido` (post-corte, `confirmado`) y `monto_pedido_vigente` (pre-corte) separados. Autoconfirma `vigente` sin cambio de precio al crear corte. |
| `app/api/v1/endpoints/pedidos_shein.py` | Endpoints Shein      | 5 flujos + agregar artículo a pedido existente.                                                                                                       |
| `app/schemas/inventario.py`             | Schema Inventario    | —                                                                                                                                                     |
| `app/services/inventario_service.py`    | Lógica Inventario    | Transiciones validadas, descuento masivo.                                                                                                             |
| `app/api/v1/endpoints/inventario.py`    | Endpoints Inventario | Registrado en `main.py`.                                                                                                                              |
| `app/schemas/cliente.py`                | Schema Cliente       | `telefono`/`ref_telefono` int, `frecuencia_pago` obligatorio, validación condicional, `max_length` alineado.                                          |
| `app/services/cliente_service.py`       | Lógica Cliente       | Sin referencia a `"liquidado"`. `crear_cliente()` asigna los 3 campos de frecuencia.                                                                  |
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

### 4.3 Módulos con bugs activos — Movimientos

**Todo `registrar_movimiento()` está roto.** El constructor
`Movimiento(..., notas=data.notas)` usa `notas` — columna inexistente en
`models.py` (la columna real es `descripcion`). SQLAlchemy lanza `TypeError`
en **cualquier** operación (`contado`, `apartado`, `abono`, `gasto`). Este bug
enmascara los demás — van a reaparecer en cuanto se corrija:

| Bug                                            | Archivo                                                                            | Descripción                                                                                                   |
| ---------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `notas` → `descripcion`                        | `movimiento_service.py` L61, `schemas/movimiento.py` L13/L43                       | Columna inexistente. Crash en el 100% de las llamadas.                                                        |
| Sobrescritura de saldo                         | `movimiento_service.py` L37                                                        | `cliente.saldo = saldo_resultante` en vez de `+=`.                                                            |
| Sin mínimo $100 en apartado                    | `movimiento_service.py` L28–34                                                     | Solo valida `monto < 0`, no `>= 100`.                                                                         |
| Sin validación de `descripcion` en gasto       | `movimiento_service.py`                                                            | La rama de `gasto` no existe — no se valida nada.                                                             |
| `"liquidado"` inexistente                      | `movimiento_service.py` L52 (`registrar_movimiento`), L124 (`cancelar_movimiento`) | Asigna un valor que no existe en `EstatusCliente` (`activo`/`inactivo`). Crash garantizado con `LookupError`. |
| `cancelar_movimiento()` — reversión incorrecta | `movimiento_service.py` L109–118                                                   | Busca saldo anterior sin filtrar por tipo de operación.                                                       |

### 4.4 Módulos con bugs activos — Auth

| Bug                              | Archivo                  | Descripción                                                                                        |
| -------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------- |
| `UsuarioRead.username`           | `schemas/usuario.py` L28 | Campo `username` no existe en modelo (es `usuario`). `from_attributes = True` rompe serialización. |
| `UsuarioRead.activo: str`        | `schemas/usuario.py` L30 | Debería ser `int` (modelo tiene `Integer`).                                                        |
| `auth.py` usa `usuario.username` | `endpoints/auth.py`      | Rompe con el rename a `usuario`.                                                                   |
| `TokenData.username`             | `schemas/token.py` L13   | Nombre interno, no mapea vía `from_attributes`. Severidad baja.                                    |

> `auth_service.py` ya usa `usuario.usuario` internamente (L59, L69).
> `get_current_user()` (L81) lee `token_data.username` (de `TokenData`).
> `crear_token()` (L73) pone `usuario` en clave `sub` del JWT.

### 4.5 Sin código todavía

| Módulo                | Spec disponible                      |
| --------------------- | ------------------------------------ |
| Recargas Telefónicas  | `module_recargas.md` — completa.     |
| Setting/Configuración | `module_setting.md` — esqueleto MVP. |
| Consulta Global       | `module_consulta.md` — completa.     |

---

## 5. Ruta de trabajo (orden decidido con el usuario)

1. **Corregir Movimientos** (§4.3):
   - Renombrar `notas` → `descripcion` en schema y servicio.
   - Corregir `cliente.saldo += saldo_resultante`.
   - Agregar mínimo $100 en apartado.
   - Agregar rama de validación de `gasto` (`descripcion` obligatoria).
   - Quitar `"liquidado"` de `registrar_movimiento()` y `cancelar_movimiento()`.
   - Rediseñar `cancelar_movimiento()` (filtrar por tipo de operación al
     recuperar saldo anterior).
   - Escribir `test_movimientos.py`.

2. **Corregir Auth** (§4.4):
   - Rename `username` → `usuario` en `UsuarioRead`.
   - Corregir `activo: str` → `activo: int`.
   - Alinear `endpoints/auth.py`.
   - Evaluar si `TokenData.username` se renombra o se deja (severidad baja).

3. **Construir Recargas** desde cero.

4. **Construir Setting/Configuración** (esqueleto MVP — sin permisos
   diferenciados todavía).

5. **Construir Consulta Global** (3 vistas de solo lectura).

6. **Checklist real** — criterio de completado = pipeline + test.

---

## 6. Cómo usar este documento en una sesión nueva

Si retomas el trabajo y solo compartes `REPORT.md`, ya se sabe: qué está
decidido (§3), el estado del modelo de datos (§2), qué evidencia hay de cada
archivo (§4), qué bugs están confirmados (§4.3/§4.4), y qué falta (§5).

No hace falta resubir los archivos de §4.1 — solo los que se vayan a tocar
o cualquier archivo que haya cambiado desde la última actualización.

**Siguiente paso inmediato:** §5 paso 1 — cerrar la verificación de Clientes
(`pytest test/test_clientes.py -v`).
