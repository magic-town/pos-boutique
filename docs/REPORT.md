# REPORT — Mapa de Estado del Proyecto (pos-boutique)

> **Qué es este documento:** una fotografía del estado actual — decisiones
> tomadas, evidencia confirmada, huecos de visibilidad y ruta de trabajo. No es
> spec de negocio (eso es `REGLAS_NEGOCIO.md` / `00_FULLSTACK_DEVELOPMENT.md`).
> Es el documento que permite retomar el trabajo en cualquier sesión nueva sin
> recargar todo el repo. Si solo compartes este archivo, Claude debe poder
> saber qué hacer a continuación; solo pide otro archivo cuando algo no se
> pueda inferir de aquí (ver §7).

---

## 1. Jerarquía de fuentes

1. **`docs/00_FULLSTACK_DEVELOPMENT.md`** — spec de UI/UX, autoridad máxima si
   hay contradicción. Sin pendientes de contenido conocidos. Única
   inconsistencia interna: INC-13, ver §6. **Segmentado en `docs/FULLSTACK/`**
   (un `module_<nombre>.md` por módulo + `resumen_tablas.md` transversal) —
   para trabajar un módulo específico, leer solo su archivo ahí, no el
   monolito completo. Ver `docs/FULLSTACK/README.md` para el mapa y estado
   de cada uno. El monolito sigue siendo la fuente si hay duda de fidelidad
   de la extracción.
2. **`docs/REGLAS_NEGOCIO.md`** — modelo de datos + reglas de negocio, derivado
   de (1). Pendiente: agregar definición formal de la tabla `precios_catalogo`
   (columnas, regla de no-unicidad de `id_producto`, FK conceptual a
   `pedidos_articulos.id_producto`) — no bloquea código, es deuda de
   consistencia entre documentos.
3. **`docs/ARQUITECTURA.md`** — decisiones técnicas, derivado de evidencia de
   código real.
4. **`docs/README.md`** — orientación y arranque.
5. **`backend/app/models/models.py`** — implementado y migrado. 13 tablas en
   `pos.db`, alineadas a la spec maestra completa (incluye `precios_catalogo`
   y el módulo Shein en cabecera-detalle).

**Regla de edición:** el usuario edita `00_FULLSTACK_DEVELOPMENT.md` y
`REGLAS_NEGOCIO.md` directamente; Claude no los reescribe salvo instrucción
explícita del usuario en la sesión.

---

## 2. Estado del modelo de datos (`models.py` / `pos.db`)

13 tablas, todas migradas y alineadas a spec. Migraciones vigentes:
`a1b2c3d4e5f6` (esquema inicial) → `b2c3d4e5f6a7` (agrega `precios_catalogo` y
`shein_pedidos_articulos`; reestructura `shein_pedidos` y `shein_cortes`).
`alembic current` en `b2c3d4e5f6a7` (head).

| Tabla | Módulo | Notas |
|---|---|---|
| `clientes` | Clientes | — |
| `pedidos` | Pedidos | Cabecera. |
| `pedidos_articulos` | Pedidos | Detalle, 1 a 4 artículos, con `rol` (principal/alternativa). |
| `precios_catalogo` | Pedidos | Catálogo importado de `tabla_precios.ods`. **Poblada**: 15,564 filas (`Price_Shoes` 5,816 / `Pakar` 7,268 / `Cklass` 2,480), corrida vía `importar_precios.py` contra el archivo completo (~18,300 filas leídas). |
| `inventario` | Inventario | — |
| `movimientos` | Panel Principal | — |
| `shein_clientes` | Shein | Independiente de `clientes`. |
| `shein_pedidos` | Shein | Cabecera: `id_shein_cliente`, `id_shein_corte`, `estatus_pago`, `fecha`. |
| `shein_pedidos_articulos` | Shein | Detalle, 1 a 4 artículos, **sin** concepto de alternativa (no tiene `rol` ni `id_articulo_principal`). |
| `shein_cortes` | Shein | `suma_pedidos`, `total_ticket`, `cupon = suma_pedidos - total_ticket`. |
| `recargas` | Recargas | — |
| `usuarios` | Autenticación | — |
| `configuracion` | Configuración | — |

Diseño completo de columnas y tipos: `REGLAS_NEGOCIO.md` (por tabla, con la
misma nomenclatura que `models.py`).

**Pendiente de implementación en código sobre este modelo ya migrado**
(schemas/services/endpoints — ver §5 para orden):

- ~~Pedidos~~ — completado. Ver §5 paso 1 (cerrado) y §4.1.
- ~~Shein~~ — completado. Ver §5 paso 2 (cerrado) y §4.1.
- ~~Inventario~~ — completado (primera implementación de código; el modelo
  SQLAlchemy ya existía sin usarse). Ver §5 nuevo paso y §4.1.
- Ajustes puntuales a Clientes, Movimientos y Auth ya existentes — ver §5,
  pasos 5–7.
- Inventario, Recargas y Setting/Configuración — sin código todavía, spec
  completa disponible.

---

## 3. Decisiones cerradas (no reabrir salvo nueva evidencia)

| Decisión | Resultado |
|---|---|
| ¿Se conserva data de `pos.db`? | No. Reset limpio ejecutado; el esquema nace de `models.py` vía Alembic. |
| ¿Multi-empresa / multi-sucursal? | No existe ni se planea. Negocio único, una operadora. |
| ¿Async o sync en SQLAlchemy? | Síncrono (`database.py`, `create_engine` estándar, sin `aiosqlite`). |
| ¿`telefono`/`ref_telefono` tipo de dato? | `Integer` (10 dígitos), no `String`. Implementado en `models.py`; pendiente de ajuste en `schemas/cliente.py` (§5 paso 5, INC-01). |
| ¿Nombres de campo en `Usuario`? | `usuario` (no `username`) y `password_hash` (no `hashed_password`). Pendiente de ajuste en `schemas/usuario.py` y `auth.py` (§5 paso 7, INC-08). |
| ¿`pedidos` plano o cabecera-detalle? | Cabecera-detalle (`pedidos` + `pedidos_articulos`), 1 a 4 artículos principales, cada uno con 0 o 1 alternativa. |
| ¿Shein comparte tabla de clientes? | No. `shein_clientes` independiente. |
| ¿`shein_pedidos` plano o cabecera-detalle? | Cabecera-detalle: `shein_pedidos` (cabecera) + `shein_pedidos_articulos` (detalle, 1 a 4 artículos, sin alternativa). Implementado y migrado. |
| ¿Cómo se calcula el `cupon` de Shein? | `cupon = suma_pedidos - total_ticket`, calculado y persistido por el backend al guardar el corte. No se estima por porcentaje interno — lo determina el proveedor externamente. `total_ticket` (pagado en OXXO) es captura manual obligatoria. |
| ¿Variación de precio Shein entre pedido y corte? | Cualquier variación — sube o baja — exige notificar al cliente y obtener confirmación explícita del artículo al precio actualizado. `estatus_articulo` (`vigente`/`confirmado`/`cancelado`) controla la resolución. |
| ¿Dónde vive `estatus_pago` en Shein? | En `shein_pedidos`, por pedido — nunca en `shein_clientes` ni en `shein_cortes`. Un mismo cliente puede tener pedidos con estatus de pago distinto en cortes distintos. |
| ¿Qué pasa si todos los artículos de un `shein_pedido` se cancelan en el corte? | El pedido completo se considera cancelado: no recibe `id_shein_corte` ni `estatus_pago`. Si sobrevive al menos un artículo `confirmado`, el pedido continúa y solo esos artículos entran al cálculo de `monto_pedido`. |
| ¿`init_db.py` en `lifespan`? | Resuelto: `main.py` ya no invoca `init_db()`. Alembic es la única fuente de esquema (INC-12). |
| ¿`precios_catalogo` en SQLite? | Sí. Tabla migrada. Sin datos todavía — pendiente correr `importar_precios.py`. |
| ¿Cómo se sincroniza `tabla_precios.ods` con SQLite? | Disparador manual: script `backend/app/scripts/importar_precios.py` (aún no escrito). El usuario lo corre cuando el proveedor libera catálogo nuevo. Solo `INSERT` de filas nuevas. |
| ¿Qué columnas guarda `precios_catalogo`? | Todas las columnas del `.ods`, incluidas las no usadas por el POS (`catalogo`, `pagina`, `precio_base`) — se preservan por fidelidad al archivo original. |
| ¿Cómo resuelve el POS el precio de un artículo? | `SELECT precio_venta WHERE proveedor = :p AND id_producto = :id ORDER BY fecha_catalogo DESC LIMIT 1` — gana la fecha más reciente. |
| ¿`id_producto` es único por proveedor? | No. El mismo `id_producto` puede repetirse en catálogos futuros. Sin restricción `UNIQUE`. Desempate siempre por `MAX(fecha_catalogo)`. |
| ¿Cuándo sube el saldo de un artículo de pedido? | Al marcarse `en_almacen`, no al registrar el pedido. Confirmado con pruebas end-to-end reales (§5 paso 1). |
| Estructura de documentación | `00_FULLSTACK_DEVELOPMENT.md` = spec de UI. `REGLAS_NEGOCIO.md` = modelo de datos. `ARQUITECTURA.md` = decisiones técnicas. `REPORT.md` = estado, no spec. |
| ¿Qué hacer con la columna `redondea` del `.ods`? | Descartarla al leer el archivo. No forma parte del modelo (`models.py` no la tiene) ni de `REGLAS_NEGOCIO.md`/`00_FULLSTACK_DEVELOPMENT.md`. No requiere migración. |
| ¿Qué hacer con valores no numéricos en `pagina` del `.ods` (p. ej. `'166BEBES'`)? | Guardar `NULL`. Columna auxiliar, no usada por el POS — sin implicación en el archivo original ni en el sistema. No requiere migración ni cambio de tipo en `models.py`. |
| ¿Cuántas alternativas puede tener un artículo principal? | 0 a 1, salvo que el **principal** sea `proveedor = Price_Shoes`, en cuyo caso hasta 3 (4 artículos en ese renglón). La condición se evalúa sobre el proveedor del principal, no de cada alternativa. Cambio de capa de aplicación (`schemas/pedido.py`, `pedido_service.py`) — `models.py` no requirió cambios: `id_articulo_principal` ya era un FK sin `UNIQUE`, así que la base de datos ya soportaba múltiples alternativas por principal. |
| ¿Cómo se verifica que un módulo sigue funcionando sin repetir `curl` a mano? | Directorio `backend/test/` (pytest + `TestClient`), un archivo por módulo mapeado 1:1 a `FULLSTACK/module_<nombre>.md`. No reemplaza las guías `aux_*.md` (esas son para que una persona entienda el flujo); el directorio `test/` es para verificar que sigue funcionando, sin explicar nada. Ver `backend/test/README.md`. |
| ¿Cómo se segmenta `00_FULLSTACK_DEVELOPMENT.md`? | Un `FULLSTACK/module_<nombre>.md` por módulo, mismo nivel de detalle que `module_pedidos.md` (ya existente). Regla de una sola vía: `REPORT.md` puede referenciar a los `module_*.md`, nunca al revés — un documento de módulo debe bastarse solo. |
| ¿`inventario_bz.ods` sincroniza cambios en re-subidas futuras (UPSERT), o solo agrega productos nuevos? | Solo `INSERT`. Sin clave natural en el archivo para detectar duplicados — responsabilidad operativa correrlo solo con mercancía genuinamente nueva. |
| ¿El descuento de Inventario se captura en `inventario_bz.ods` o en el sistema? | Exclusivamente en el sistema (`POST /inventario/descuento-masivo`). El `.ods` nunca trae `precio_descuento` — es una funcionalidad nueva que no existía antes del POS, sin equivalente en los registros físicos de la usuaria. |
| ¿Cómo se define el "segmento" de un descuento masivo? | Filtro por `categoria`/`tipo_producto`/`marca`/`talla`/`color`, y/o selección manual de `ids_producto` — no excluyentes, se combinan con AND. Sin campo de fecha de expiración: se retira manualmente con la operación simétrica (`/descuento-masivo/retirar`). |
| ¿Qué hacer con las 6 secciones restantes de `00_FULLSTACK_DEVELOPMENT.md`? | Extraídas verbatim a `docs/FULLSTACK/module_clientes.md`, `module_movimientos.md`, `module_shein.md`, `module_recargas.md`, `module_consulta.md`, `module_setting.md` + `resumen_tablas.md` (transversal). Ver `docs/FULLSTACK/README.md` para el mapa completo. Segmentación 100% completa; código/test siguen pendientes por módulo (ver esa tabla). |

### 3.1 Diseño de `precios_catalogo`

```
precios_catalogo
├── id_precio         Integer, PK AUTOINCREMENT
├── proveedor         Enum (Price_Shoes | Pakar | Cklass)  ← sin "otro": otro no tiene catálogo
├── id_producto       String(12)   ← normalizado desde ID / CÓDIGO / modelo según pestaña
├── precio_venta      Integer
├── fecha_catalogo    Date         ← normalizada a ISO desde cualquier formato del .ods
│
│   Columnas auxiliares del .ods (preservadas para fidelidad, no usadas por el POS):
├── catalogo          String       ← nombre del catálogo/tomo
├── temporada         String       ← temp / temporada según pestaña
├── pagina             Integer      ← Pag / PÁG. / pag según pestaña
└── precio_base        Integer      ← Sug_credito / 2 PAGO / precio_base según pestaña
```

Sin restricción `UNIQUE`. Mapeo de columnas identificadoras por pestaña del
`.ods` (confirmado idéntico entre `tabla_precios.ods` y
`00_FULLSTACK_DEVELOPMENT.md`):

| Pestaña | Columna id en .ods | Columna precio en .ods | Columna base en .ods |
|---|---|---|---|
| `price_shoes` | `ID` | `precio_venta` | `Sug_credito` |
| `pakar` | `CÓDIGO` | `precio_venta` | `2 PAGO` |
| `cklass` | `modelo` | `precio_venta` | `precio_base` |

`fecha` en `price_shoes`/`pakar` viene como texto (`"02-mayo-2026"`); en
`cklass` como fecha ISO. El script de import normaliza ambos formatos a `Date`
ISO antes de insertar.

### 3.2 Diseño de tablas Shein

```
shein_pedidos                              (cabecera)
├── id_shein_pedido    Integer, PK AUTOINCREMENT
├── id_shein_cliente   FK → shein_clientes.id_shein_cliente
├── id_shein_corte     FK → shein_cortes.id_shein_corte, nullable
├── estatus_pago       Enum (pago_pendiente | pagado), nullable
└── fecha              Date

shein_pedidos_articulos                    (detalle)
├── id_shein_articulo  Integer, PK AUTOINCREMENT
├── id_shein_pedido    FK → shein_pedidos.id_shein_pedido
├── id_articulo        String(20), nullable   ← referencia libre a la app Shein, sin FK real
├── producto           String(60) NOT NULL
├── tipo_producto       Enum (Nacional | Importado)
├── monto               Float NOT NULL
├── monto_vigente       Float, nullable
└── estatus_articulo    Enum (vigente | confirmado | cancelado), default vigente

shein_cortes
├── id_shein_corte     Integer, PK AUTOINCREMENT
├── fecha_corte        Date
├── total_pedidos      Integer
├── suma_pedidos       Float
├── total_ticket       Float        ← captura manual (pago en OXXO)
└── cupon              Float        ← = suma_pedidos - total_ticket
```

Enums usados en Shein (nombres propios, no comparten clase con los de
Pedidos): `TipoProductoShein` (`Nacional`/`Importado`), `EstatusArticuloShein`
(`vigente`/`confirmado`/`cancelado`), `EstatusPago`
(`pago_pendiente`/`pagado`).

`monto_pedido` (por pedido) y `suma_pedidos` (por corte) no son cálculos que
se repliquen en Python — se derivan siempre por consulta filtrando
`estatus_articulo = 'confirmado'`, igual que documenta `REGLAS_NEGOCIO.md` §6
regla 8.

---

## 4. Mapa de archivos

### 4.1 Confirmados con evidencia directa

| Archivo | Rol | Estado |
|---|---|---|
| `app/models/models.py` | Modelo de datos vigente | 13 tablas, alineado por completo a spec. Migrado vía `b2c3d4e5f6a7` (head). |
| `alembic/versions/a1b2c3d4e5f6_esquema_inicial.py` | Migración | Esquema base: 11 tablas. |
| `alembic/versions/b2c3d4e5f6a7_...py` | Migración correctiva | Agrega `precios_catalogo` y `shein_pedidos_articulos`; reestructura `shein_pedidos`/`shein_cortes`. Probada con `upgrade`/`downgrade` limpios y corrida contra `pos.db` real. |
| `app/db/init_db.py` | Inicializador de BD | Función existe en el archivo pero ya no se invoca desde `main.py`. Alembic es la única fuente de esquema. |
| `app/main.py` | Bootstrap FastAPI | Confirma que `init_db()` no se ejecuta en `lifespan`. Registra 5 routers. CORS solo a `localhost:5173`. |
| `app/schemas/cliente.py` | Schema Cliente | `telefono: str` (L9) / `ref_telefono: Optional[str]` (L12) deberían ser `int` (INC-01). `ClienteCreate` (L6–19) no incluye `frecuencia_pago`, `nullable=False` en el modelo (INC-02). `ClienteRead` (L22–35) no incluye `fecha_pago_programada` (INC-10). Pendiente §5 paso 5. |
| `app/services/cliente_service.py` | Lógica Cliente | `estatus == "liquidado"` en `rehabilitar_cliente()` (L67, L73) — no existe en el enum nuevo (INC-07). `crear_cliente()` (L26–36) no asigna `frecuencia_pago` — el `INSERT` fallará en tiempo de ejecución (INC-02). No asigna `fecha_pago_programada`, pero esa columna sí es `nullable=True` — comportamiento correcto, queda `NULL` hasta el primer abono. Pendiente §5 paso 5. |
| `app/schemas/movimiento.py` | Schema Movimiento | `notas: Optional[str]` (L13, L43) debería ser `descripcion` (INC-03). Sin validación de `descripcion` obligatoria cuando `operacion = 'gasto'` (INC-04). Pendiente §5 paso 6. |
| `app/services/movimiento_service.py` | Lógica Movimiento | Sobrescritura de saldo (L37, INC-05), estatus `"liquidado"` inexistente (L52, INC-07), `notas=data.notas` no mapea a columna real (L61, INC-03/INC-11), sin validación de mínimo $100 (L28–36, INC-06). `cancelar_movimiento()` tiene bug de diseño en la reversión, no solo de typo — ver §5 punto 4. Pendiente §5 paso 6. |
| `app/db/database.py` | Conexión BD | SQLAlchemy síncrono. `get_db()` estándar. |
| `app/core/config.py` | Configuración | Solo tiene `DATABASE_URL`. No existe `AUTH_ENABLED`. `SECRET_KEY` no está aquí. |
| `app/api/v1/endpoints/auth.py` | Endpoint login | JWT real vía `auth_service.crear_token`. Llama `usuario.username` — rompe con el rename a `usuario`. Pendiente §5 paso 7. |
| `app/schemas/usuario.py` | Schema Usuario | `UsuarioRead` (L26–33) define `username: str` (L28) cuando el modelo tiene `usuario`; `activo: str` (L30) cuando el modelo tiene `Integer` (INC-08). Con `from_attributes = True`, Pydantic intentará leer `obj.username`, que no existe — error de serialización. Bloqueante para §5 paso 7. |
| `app/schemas/token.py` | Schema Token | `TokenData.username` (L13) en vez de `usuario`. No es bug funcional — nombre interno del schema, no mapea al modelo vía `from_attributes`, y `auth_service.py` lo usa de forma consistente. Severidad baja (INC-09), no bloqueante. |
| `app/api/v1/endpoints/clientes.py` | Endpoints Cliente | Todos protegidos con `Depends(get_current_user)`. |
| `app/api/v1/endpoints/movimientos.py` | Endpoints Movimiento | Mismo patrón de protección. CRUD básico completo. |
| `app/api/v1/endpoints/pedidos.py` | Endpoints Pedido | Reescrito completo, reemplaza el modelo plano viejo. 4 flujos (Registrar Pedido, Registrar Devolución, Cancelar Artículo, Lista de Surtido) probados end-to-end con `curl` real (login JWT + `no_cliente = PRUEBA-001`) contra `pos.db` en head `b2c3d4e5f6a7`. §5 paso 1 cerrado. |
| `app/api/v1/endpoints/pedidos_shein.py` | Endpoints Shein | Implementado y probado (5 flujos: cliente, pedido, lista, resolución de artículo, corte). §5 paso 2 cerrado. |
| `app/schemas/pedido.py` | Schema Pedido | Reescrito completo (`ArticuloCreate`/`ArticuloConAlternativa`/`PedidoCreate`/etc.), reemplaza la estructura plana con `opcion_*`. Valida reglas por `tipo_producto`/`proveedor` (monto obligatorio si `proveedor = otro`). |
| `app/schemas/pedido_shein.py` | Schema Shein | Implementado. `max_length` agregado en `nombre`(20)/`colonia`(12)/`producto`(60)/`id_articulo`(20) para alinear con `String(N)` de `models.py` — verificado con `curl` contra servidor real (`422` al exceder, `201` en caso válido). |
| `app/services/pedido_service.py` | Lógica Pedido | Reescrito completo, reemplaza `Pedido(producto=..., marca=..., talla=...)`. Incluye lookup de precio (`ORDER BY fecha_catalogo DESC LIMIT 1`), transacciones de devolución/cancelación con reversión condicional de saldo (solo si el artículo ya había pasado por `en_almacen`) — ambos casos probados con `curl` real. |
| `app/services/pedido_shein_service.py` | Lógica Shein | Implementado. `monto_pedido` derivado siempre de artículos `confirmado` (nunca replicado). Pedido con todos los artículos `cancelado` no recibe `id_shein_corte`/`estatus_pago`. |
| `app/scripts/importar_precios.py` | Script de import de precios | Implementado y corrido contra `tabla_precios.ods` completo. 15,564 filas nuevas insertadas (ver §2). Descarta `redondea`, guarda `NULL` en `pagina` no numérica (ver §3). Solo `INSERT`, idempotente por `(proveedor, id_producto, fecha_catalogo)`. |
| `app/schemas/inventario.py` | Schema Inventario | Nuevo. `ProductoCreate`/`CambiarEstatusRequest`/`SegmentoDescuento`/etc. Primera implementación de código de este módulo. |
| `app/services/inventario_service.py` | Lógica Inventario | Nuevo. Transiciones de estatus validadas por tabla (`TRANSICIONES_VALIDAS`), descuento masivo solo afecta `disponible`→`disponible_c/descuento` (y su reversa), nunca `vendido`/`apartado`/`en_ruta`. |
| `app/api/v1/endpoints/inventario.py` | Endpoints Inventario | Nuevo. **Pendiente registrar en `main.py`**: `app.include_router(inventario.router, prefix="/api/v1")` — a diferencia de Pedidos, este router no existía antes. |
| `app/scripts/importar_inventario.py` | Script de carga inicial de Inventario | Nuevo. Solo `INSERT` desde `inventario_bz.ods` — sin clave natural para detectar duplicados (ver §3), a diferencia de `importar_precios.py`. Columnas del `.ods` **provisionales**, pendiente confirmar contra el archivo real (rótulos + 2 registros, aún no subido). |
| `requirements.txt` | Dependencias | `python-jose` + `passlib`/`bcrypt` — JWT real. Sin `pytest`. `pandas` + `odfpy` agregados (requeridos por `importar_precios.py`). |
| `docs/00_FULLSTACK_DEVELOPMENT.md` | Spec UI/UX | Confirma `tabla_precios`/`precios_catalogo`, módulo Inventario, módulo Recargas, módulo Setting, módulo Shein — todos documentados al mismo nivel de detalle. Único hallazgo: inconsistencia interna de longitud de `producto` (INC-13, ver §6). |
| `docs/REGLAS_NEGOCIO.md` | Modelo de datos + reglas de negocio | Alineado por completo a `00_FULLSTACK_DEVELOPMENT.md`, incluye Shein cabecera-detalle. Pendiente: definición formal de `precios_catalogo` (ver §1 punto 2). |
| `tabla_precios.ods` | Catálogo de precios por proveedor | 3 pestañas (`price_shoes`, `pakar`, `cklass`). Esquema documentado en §3.1. Fuente de verdad operativa — se mantiene en `.ods`, se sincroniza a SQLite vía script manual. Ya sincronizada (§2). 34 filas de `cklass` con `id_producto` > 12 caracteres (descripciones, no códigos) quedan fuera del catálogo — sin match, el monto se captura a mano en el formulario (decisión del usuario). |

### 4.2 Mencionados pero NO vistos (pedir antes de tocar)

| Archivo | Por qué importa |
|---|---|
| `app/services/auth_service.py` | Contiene `autenticar_usuario`, `crear_token`, `get_current_user`. Confirmado vía `grep` esta sesión: `get_current_user` en L81, `hash_password`/`verificar_password` con `passlib`/`bcrypt` (`CryptContext`, `schemes=["bcrypt"]`) en L22/28/32, `verificar_password`/`password_hash` en L59/69. Suficiente para usarlo desde `endpoints/pedidos.py` (§5 paso 1) y para el login de pruebas. **Archivo completo aún no visto** — sigue bloqueante para renombrar `username`→`usuario` (§5 paso 7). |
| Endpoints/servicios de Inventario | No hay evidencia de que existan en código. Spec completa disponible. |
| Endpoints/servicios de Recargas | Mismo caso: spec completa, cero evidencia de código. |
| Endpoints/servicios de Setting/Configuración | Mismo caso: spec completa, marcada explícitamente como "esqueleto MVP". |
| `backend/tests/*` | Contenido real no visto. Referenciado como vacío. |
| `.env` / variables de entorno reales | No vistas. `config.py` solo define el default de `DATABASE_URL`. |

### 4.3 Riesgos activos confirmados (bugs con evidencia, no inferencias)

1. **Sobrescritura de saldo en apartado** (`movimiento_service.py` L37) —
   `cliente.saldo = saldo_resultante` en vez de `cliente.saldo +=
   saldo_resultante` (INC-05).
2. **Sin mínimo de $100 en apartado** (`movimiento_service.py` L28–36) — la
   rama de `apartado` solo valida `monto < 0`, no `monto >= 100` (INC-06).
3. **Estados de cliente obsoletos (`"liquidado"`)** — aparece en tres lugares:
   `movimiento_service.py` L52 (`registrar_movimiento()` lo asigna al llegar
   `saldo` a 0), `cancelar_movimiento()` (lo vuelve a poner como `"activo"` al
   revertir, heredando el mismo problema de fondo), y `cliente_service.py`
   L67/L73 (`rehabilitar_cliente()` lee y escribe `"liquidado"`). El enum
   nuevo (`EstatusCliente`) solo tiene `activo`/`inactivo` — los tres puntos
   deben corregirse juntos, no uno a la vez (INC-07).
4. **`cancelar_movimiento()` — bug de diseño, no de línea.** Al revertir un
   movimiento, el método busca el `saldo_resultante` del movimiento anterior
   del cliente completo, sin filtrar por tipo de operación. Si ese movimiento
   anterior fue un `apartado` afectado por el bug del punto 1, el "saldo
   anterior" recuperado es matemáticamente incorrecto — persiste
   independientemente de que se corrija el `+=` del punto 1, si ya hay datos
   de prueba generados antes del fix. Necesita rediseño de la lógica de
   reversión. Depende de que el punto 1 se resuelva primero — no se puede
   arreglar en paralelo.
5. **`crear_cliente()` no asigna `frecuencia_pago`** (`cliente_service.py`
   L26–36) — la columna es `nullable=False` en el modelo. El primer `INSERT`
   real falla en tiempo de ejecución: es un crash garantizado, no una
   degradación silenciosa (INC-02). **Confirmado en runtime esta sesión**: al
   probar `POST /api/v1/clientes` para crear un cliente de prueba para el
   módulo Pedidos, el servidor devolvió `500` con
   `sqlite3.IntegrityError: NOT NULL constraint failed: clientes.frecuencia_pago`
   — traceback completo coincide exactamente con lo ya documentado aquí. No
   se corrigió (fuera de alcance de §5 paso 1); se usó un `INSERT` manual en
   SQLite como workaround solo para destrabar las pruebas de Pedidos.
6. **`app/schemas/__init__.py` importaba nombres inexistentes de Shein**
   (`PedidoSheinCreate`/`PedidoSheinRead` en vez de `SheinPedidoCreate`/
   `SheinPedidoRead`) — residuo del nombre viejo previo a la reestructura
   cabecera-detalle. Tumbaba el arranque completo del servidor
   (`ImportError` en cadena desde `main.py`). Corregido y verificado con
   `uvicorn` levantando limpio (INC-14).

---

## 5. Ruta de trabajo (orden, no checklist de tareas individuales)

1. **Módulo Pedidos** — ✅ CERRADO. `importar_precios.py` (nuevo),
   `schemas/pedido.py` (reescrito), `services/pedido_service.py` (reescrito),
   `endpoints/pedidos.py` (reescrito) implementados y probados end-to-end
   (login JWT + `curl` real) contra `pos.db` en head `b2c3d4e5f6a7`. Cubre los
   4 flujos: Registrar Pedido (lookup automático de precio + captura manual
   para `proveedor = otro` / `informal`), Registrar Devolución, Cancelar
   Artículo (probados ambos casos: `vigente` sin impacto de saldo, `en_almacen`
   con reversión), Lista de Surtido (`vigente` → `en_almacen`, saldo `+=`).
   Import de precios corrido contra el `.ods` completo: 15,564 filas nuevas
   (ver §2).

1.1. **Módulo Inventario** — ✅ CÓDIGO CERRADO, pendiente probar end-to-end.
   Primera implementación (el modelo SQLAlchemy ya existía, sin usarse).
   `schemas/inventario.py`, `services/inventario_service.py`,
   `endpoints/inventario.py` (nuevo, falta registrar en `main.py`),
   `scripts/importar_inventario.py` (nuevo, columnas provisionales — falta
   confirmar contra `inventario_bz.ods` real). Agrega Opción 4/5 (Descuento
   Masivo aplicar/retirar) al spec original, sin requerir migración —
   `precio_descuento` y `EstatusInventario.disponible_c_descuento` ya
   existían en `models.py`. `FULLSTACK/module_inventario.md` extraído
   verbatim de `00_FULLSTACK_DEVELOPMENT.md` + secciones nuevas marcadas
   como tal. `test/test_inventario.py` escrito, no corrido todavía contra
   servidor real (falta registrar el router primero).
2. **Módulo Shein** — ✅ CERRADO. `schemas/pedido_shein.py`,
   `services/pedido_shein_service.py`, `endpoints/pedidos_shein.py`
   implementados y probados end-to-end (login JWT + `curl` real) contra
   `pos.db` en head `b2c3d4e5f6a7`. Cubre los 5 flujos. Bug de import
   encontrado y corregido en el camino (INC-14, ver §4.3).
3. Ajuste de `schemas/cliente.py` y `services/cliente_service.py`:
   - Quitar `"liquidado"` de `rehabilitar_cliente()`.
   - Ajustar tipo `telefono`/`ref_telefono` a `int` (INC-01).
   - Agregar `frecuencia_pago` a `ClienteCreate` y a la construcción del
     objeto en `crear_cliente()` — bloqueante de crash, no cosmético (INC-02).
   - Agregar `fecha_pago_programada` a `ClienteRead` (INC-10).
4. Ajuste de `schemas/movimiento.py` y `services/movimiento_service.py`:
   - Renombrar `notas` → `descripcion` en schema y en la construcción del
     objeto `Movimiento` (INC-03, INC-11).
   - Agregar validación de `descripcion` obligatoria cuando
     `operacion = 'gasto'` (INC-04).
   - Corregir suma de saldo: `cliente.saldo += saldo_resultante`.
   - Agregar validación de mínimo $100 en apartado.
   - Quitar `"liquidado"` de los tres puntos identificados en §4.3 punto 3, no
     solo de `registrar_movimiento()`.
   - Rediseñar `cancelar_movimiento()` para filtrar por tipo de operación al
     recuperar el saldo anterior — depende de que el punto de suma de saldo
     ya esté corregido.
5. Ajuste de `auth.py` + `auth_service.py` + `schemas/usuario.py` (rename
   `username`→`usuario`, `hashed_password`→`password_hash`, `activo: str`→
   `int` en `UsuarioRead`). Requiere ver `auth_service.py` directamente antes
   de tocarlo (§4.2). `schemas/token.py` no requiere cambio funcional
   (INC-09, severidad baja).
6. Construcción desde cero de Inventario — spec completa disponible, solo
   falta schema + servicio + endpoint en código.
7. Construcción desde cero de Recargas y Setting/Configuración (Setting con
   alcance explícito "esqueleto MVP" — no construir lógica de permisos
   diferenciada todavía).
8. Antes o junto con el paso 1: usuario decide y corrige la inconsistencia
   interna de longitud de `producto` (INC-13, ver §6) en
   `00_FULLSTACK_DEVELOPMENT.md`. No bloquea el inicio del paso 1, pero sí debe
   resolverse antes de fijar el `String(N)` definitivo si cambia respecto al
   ya migrado en `models.py`.
9. Solo entonces: `CHECKLIST.md` real, con criterio de completado = pipeline +
   test.

---

## 6. Acción pendiente del usuario sobre la documentación

**🔴 Urgente, fuera de documentación — rotar contraseña real.** Al segmentar
`00_FULLSTACK_DEVELOPMENT.md` (§3, última fila) se encontró que la sección
de seed (`backend/db/seed.py`) tenía contraseñas de usuario en texto plano,
incluida la de `sonia` — usuario real ya en uso en esta sesión (ver
`aux_pedidos.md`). Se redactaron en `docs/FULLSTACK/module_setting.md`, pero
si esa contraseña sigue siendo la vigente en `pos.db`, **rotarla ahora**, y
no volver a poner contraseñas reales en texto plano en ningún documento que
se suba a git.

Un solo pendiente de edición, de tu lado, no de Claude (regla de §1: tú editas
`00_FULLSTACK_DEVELOPMENT.md` y `REGLAS_NEGOCIO.md`, Claude no los reescribe
salvo instrucción explícita en la sesión):

- **Decidir y corregir INC-13**: el campo `producto` de `pedidos_articulos`
  aparece con dos longitudes distintas citadas en `00_FULLSTACK_DEVELOPMENT.md`
  — una en el SQL de ejemplo, otra en el schema JSON del formulario. Verifica
  el valor vigente en el documento y ajusta la otra línea para que coincidan.
  Esto es lo único que bloquea fijar el tipo definitivo de esa columna si
  llegara a diferir del `String(40)` ya migrado en `models.py` (§5 paso 8).

Por separado, sigue pendiente que `REGLAS_NEGOCIO.md` incorpore la definición
formal de `precios_catalogo` (columnas, no-unicidad de `id_producto`, FK
conceptual). No bloquea el trabajo de código porque
`00_FULLSTACK_DEVELOPMENT.md` ya trae el detalle suficiente; es deuda de
consistencia entre documentos, no un bloqueo técnico.

---

## 7. Cómo usar este documento en una sesión nueva

Si retomas el trabajo y solo compartes `REPORT.md`, ya se sabe: qué está
decidido y no se reabre (§3), el estado exacto del modelo de datos y qué
falta poblarlo (§2), qué evidencia hay de cada archivo y qué huecos de
visibilidad quedan (§4), qué riesgos de código están confirmados (§4.3), y
qué falta del lado de la documentación (§6).

No hace falta resubir los archivos de §4.1 — solo los que aparezcan en §4.2
cuando se lleguen a tocar, o cualquier archivo que haya cambiado desde la
última actualización de este documento.

**Siguiente paso de código, ya desbloqueado:** probar Inventario end-to-end
(registrar router en `main.py`, correr `test/test_inventario.py`, confirmar
`inventario_bz.ods` real contra las columnas provisionales del script de
import) — y, en paralelo, ajuste de `schemas/cliente.py` +
`services/cliente_service.py` (§5 paso 3). Módulo Pedidos (§5 paso 1) y
módulo Shein (§5 paso 2) ya cerrados. El paso 3 ya no es solo deuda
documentada: el crash de `frecuencia_pago` (INC-02) se reprodujo en runtime
esta sesión al intentar crear un cliente de prueba (ver §4.3 punto 5).
