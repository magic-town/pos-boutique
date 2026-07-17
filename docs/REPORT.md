# REPORT — Mapa de Estado del Proyecto (pos-boutique)

> **Qué es este documento:** una fotografía del estado actual — decisiones
> tomadas, código implementado, huecos de visibilidad y ruta de trabajo. No es
> spec de negocio (eso es `REGLAS_NEGOCIO.md` / `docs/spec/*.md`).
> Es el documento que permite retomar el trabajo en cualquier sesión nueva sin
> recargar todo el repo. Si solo compartes este archivo, el agente debe poder
> saber qué hacer a continuación; solo pide otro archivo cuando algo no se
> pueda inferir de aquí (ver §6).
>
> **Ánimo actual (Momentum):** ¡Excelente! La fundación de datos está consolidada
> y el Bloque B — Módulo Clientes ya está cerrado: sistema de banderas completo
> (amarilla/roja/naranja/negra), cancelación con archivo a `cartera_vencida` y
> vinculación de familiares con tope de 4, todo con `test/test_clientes.py`
> en verde (76/76). El terreno está listo para el Bloque C (Módulo Shein).
>
> **No es bitácora de cambios.** Si un bug se corrige y el estado resultante
> ya queda reflejado en las decisiones/código/tests de este documento, no se
> documenta el historial del fix — solo el estado actual correcto. La pregunta
> antes de agregar algo aquí es "¿esto lo necesita una sesión nueva para
> retomar el trabajo?", no "¿esto pasó?".

---

## 1. Jerarquía de fuentes

1. **`docs/spec/module_<nombre>.md`** — spec de UI/UX por módulo,
   autoridad máxima si hay contradicción. Para trabajar un módulo específico,
   basta con su `module_<nombre>.md`. Ver `docs/spec/README.md` para el
   mapa y estado de cada uno.
2. **`docs/REGLAS_NEGOCIO.md`** — modelo de datos + reglas de negocio.
3. **`docs/ARQUITECTURA.md`** — decisiones técnicas.
4. **`README.md`** (raíz del repo) — orientación y arranque.
5. **`backend/app/models/models.py`** — 18 tablas migradas a `pos.db`
   (head `f6a7b8c9d0e1`). Sincronizado con las specs de modelo de datos
   (ver §2). La lógica de negocio pendiente sobre estas tablas (Clientes,
   Shein) se lista en §4.1 y §5.

**Regla de edición:** el usuario edita los `module_*.md` y
`REGLAS_NEGOCIO.md` directamente; el agente no los reescribe salvo instrucción
explícita del usuario en la sesión.

---

## 2. Estado del modelo de datos (`models.py` / `pos.db`)

18 tablas migradas. Cadena de migraciones aplicadas:

> **Verificado directo contra `pos.db`**: `SELECT version_num FROM
> alembic_version` → `f6a7b8c9d0e1`. `.tables` confirma las 18 tablas.
> `.schema shein_pedidos_articulos` confirma `sku VARCHAR(25) NOT NULL`.

| Revisión              | Alcance                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| `a1b2c3d4e5f6`        | Esquema inicial: 11 tablas. Siembra `configuracion` vía `op.bulk_insert` en `upgrade()`.              |
| `b2c3d4e5f6a7`        | Agrega `precios_catalogo` y `shein_pedidos_articulos`; reestructura `shein_pedidos` / `shein_cortes`. |
| `c3d4e5f6a7b8`        | Agrega `dia_pago_especifico` y `frecuencia_pago_detalle` a `clientes`.                                |
| `d4e5f6a7b8c9`        | Agrega `apartados`, `apartados_articulos`; agrega FK `id_apartado` a `movimientos`.                   |
| `e5f6a7b8c9d0`        | Agrega `cartera_vencida`, `familiares`, `shein_movimientos`; agrega columnas de cartera a `shein_clientes`. |
| `f6a7b8c9d0e1` (head) | Renombra `id_articulo` → `sku` en `shein_pedidos_articulos`; cambia tipo `String(20)` → `String(25)` y agrega `NOT NULL`. |

### Tablas en `pos.db` (estado actual — 18 tablas)

| Tabla                     | Módulo          | Notas                                                                        |
| ------------------------- | --------------- | ---------------------------------------------------------------------------- |
| `clientes`                | Clientes        | Incluye `frecuencia_pago`, `dia_pago_especifico`, `frecuencia_pago_detalle`. |
| `cartera_vencida`         | Clientes        | Tabla de archivo independiente, sin FKs.                                     |
| `familiares`              | Clientes        | FK doble a `clientes` (par no dirigido, dedupe vía `id_cliente_a < id_cliente_b`). Máx. 4 vínculos por cliente, validado en servicio. |
| `pedidos`                 | Pedidos         | Cabecera.                                                                    |
| `pedidos_articulos`       | Pedidos         | Detalle, 1 a 4 artículos, con `rol` (principal/alternativa).                 |
| `precios_catalogo`        | Pedidos         | Catálogo importado de `tabla_precios.ods`. Poblada: 15,564 filas.            |
| `inventario`              | Inventario      | —                                                                            |
| `movimientos`             | Panel Principal | Incluye FK `id_apartado` (nullable, solo para `operacion='apartado'`).       |
| `apartados`               | Panel Principal | Cabecera del lote de apartado.                                               |
| `apartados_articulos`     | Panel Principal | Detalle, 1 a N artículos por lote.                                           |
| `shein_clientes`          | Shein           | Con cartera: `saldo`, `estatus`, `frecuencia_pago`, `dia_pago_especifico`, `frecuencia_pago_detalle`, `fecha_pago_programada`. |
| `shein_movimientos`       | Shein           | Abonos a la cartera Shein. FK a `shein_clientes`.                            |
| `shein_pedidos`           | Shein           | Cabecera.                                                                    |
| `shein_pedidos_articulos` | Shein           | Detalle, 1 a 4 artículos, sin alternativa.                                   |
| `shein_cortes`            | Shein           | —                                                                            |
| `recargas`                | Recargas        | —                                                                            |
| `usuarios`                | Autenticación   | —                                                                            |
| `configuracion`           | Configuración   | —                                                                            |

---

## 3. Decisiones cerradas (no reabrir salvo nueva evidencia)

| Decisión                                                 | Resultado                                                                                                                               |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| ¿Se conserva data de `pos.db`?                           | No. Reset limpio; esquema nace de `models.py` vía Alembic.                                                                              |
| ¿Async o sync en SQLAlchemy?                             | Síncrono.                                                                                                                               |
| ¿Nombres de campo en `Usuario`?                          | `usuario` (no `username`) y `password_hash` (no `hashed_password`).                                                                     |
| ¿`pedidos` plano o cabecera-detalle?                     | Cabecera-detalle.                                                                                                                       |
| ¿Shein comparte tabla de clientes?                       | No. `shein_clientes` independiente de `clientes` — sin FK entre ellas.                                                                  |
| ¿`shein_pedidos` plano o cabecera-detalle?               | Cabecera-detalle, sin alternativa.                                                                                                      |
| ¿Cómo se calcula el `cupon` de Shein?                    | `cupon = suma_pedidos - total_ticket`. Nunca con porcentaje interno.                                                                    |
| ¿Variación de precio Shein?                              | Cualquier variación (sube o baja) exige notificación y confirmación del cliente.                                                        |
| ¿`estatus_pago` en Shein?                                | En `shein_pedidos`, por pedido. Nunca en `shein_clientes`.                                                                              |
| ¿Si todos los artículos Shein se cancelan?               | Pedido no recibe `id_shein_corte` ni `estatus_pago`. Saldo no impactado.                                                                |
| ¿`precios_catalogo` en SQLite?                           | Sí. Tabla migrada y poblada (15,564 filas).                                                                                             |
| ¿Sincronización de `tabla_precios.ods`?                  | Script manual `importar_precios.py`. Solo `INSERT`.                                                                                     |
| ¿Cuándo sube el saldo de un artículo de pedido?          | Al marcarse `en_almacen`.                                                                                                               |
| ¿Cuántas alternativas puede tener un artículo principal? | 0-1, salvo `Price_Shoes` (hasta 3).                                                                                                     |
| ¿Apartado modela plano o cabecera-detalle?               | Cabecera-detalle: `apartados` + `apartados_articulos`.                                                                                  |
| ¿Un cliente puede tener varios apartados abiertos?       | No. Solo uno a la vez.                                                                                                                  |
| ¿El primer pago mínimo aplica por artículo o por lote?   | Por lote completo (`monto_primer_pago`, mínimo $100).                                                                                   |
| ¿Se puede rehabilitar `estatus` manualmente?             | No. `estatus` se deriva solo de `saldo` vía `sincronizar_estatus()`. `PATCH /{id}/rehabilitar` fue removido.                            |
| ¿Setting tiene capa de servicio propia?                  | No. Lógica directa en endpoint — excepción deliberada al patrón schema/service/endpoint.                                                |
| ¿`no_cliente` es permanente por persona?                 | No. Es un slot reutilizable. Al cancelar un cliente o liquidar cuenta, el `no_cliente` puede reasignarse. El `id_cliente` (PK) no cambia.|
| ¿`cartera_vencida` tiene FKs?                            | No. Tabla de archivo independiente, sin relaciones.                                                                                     |
| ¿`familiares` es transitiva?                             | No. Solo pares declarados explícitamente. Sin grupos familiares.                                                                        |
| ¿Cuántos vínculos familiares puede declarar un cliente?  | Hasta 4. Mismo comportamiento de declaración y de cálculo de bandera negra para los 4 — sin roles ni orden especial entre ellos.        |
| ¿Shein tiene script de migración desde ODS?              | No. No existe tabla ODS para Shein. Todos los clientes se registran directamente en el sistema.                                         |
| ¿Shein tiene cartera de crédito?                         | Sí. `shein_clientes` incorpora `saldo`, `estatus`, `frecuencia_pago`, `dia_pago_especifico`, `frecuencia_pago_detalle`, `fecha_pago_programada`. Los abonos viven en `shein_movimientos`. |
| ¿El cargo de saldo Shein ocurre al corte o al pedido?    | Al guardar el corte. El `monto_pedido` (artículos `confirmado`) se carga al `saldo` del `shein_cliente`.                                |
| ¿El sistema sigue siendo local (single-device)?          | No. Se requiere espejo Android para operar sin PC (ver §5, tareas pendientes). `ARQUITECTURA.md` debe actualizarse.                     |

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

### 3.2 Diseño de tablas Shein (estado spec actual)

```
shein_clientes                             (cartera propia)
├── id_shein_cliente        Integer, PK
├── nombre                  String(20) NOT NULL
├── colonia                 String(12) NOT NULL
├── telefono                Integer NOT NULL
├── frecuencia_pago         Enum (semanal|quincenal|dia_especifico_mes|otro)
├── dia_pago_especifico     Integer, nullable
├── frecuencia_pago_detalle String(60), nullable
├── saldo                   Float NOT NULL DEFAULT 0
├── estatus                 Enum (activo|inactivo) DEFAULT 'inactivo'
└── fecha_pago_programada   Date, nullable

shein_movimientos                          (abonos a cartera)
├── id_shein_movimiento     Integer, PK
├── id_shein_cliente        FK → shein_clientes
├── monto                   Float NOT NULL
├── forma_pago              Enum (efectivo|transferencia|tarjeta)
├── saldo_resultante        Float NOT NULL
└── fecha                   DateTime NOT NULL

shein_pedidos                              (cabecera)
├── id_shein_pedido         Integer, PK
├── id_shein_cliente        FK → shein_clientes
├── id_shein_corte          FK → shein_cortes, nullable
├── estatus_pago            Enum (pago_pendiente|pagado), nullable
└── fecha                   Date

shein_pedidos_articulos                    (detalle)
├── id_shein_articulo       Integer, PK
├── id_shein_pedido         FK → shein_pedidos
├── sku                     String(25) NOT NULL
├── producto                String(60) NOT NULL
├── tipo_producto           Enum (Nacional|Importado)
├── monto                   Float NOT NULL
├── monto_vigente           Float, nullable
└── estatus_articulo        Enum (vigente|confirmado|cancelado)

shein_cortes
├── id_shein_corte          Integer, PK
├── fecha_corte             Date
├── total_pedidos           Integer
├── suma_pedidos            Float
├── total_ticket            Float
└── cupon                   Float
```

### 3.3 Diseño de tablas nuevas (spec, pendientes de migración)

```
cartera_vencida                            (archivo independiente, sin FKs)
├── id_cartera_vencida      Integer, PK
├── no_cliente_original     Text NOT NULL
├── nombre                  Text NOT NULL
├── colonia                 Text NOT NULL
├── telefono                Integer NOT NULL
├── ref_nombre              Text NOT NULL
├── ref_colonia             Text NOT NULL
├── ref_telefono            Integer, nullable
├── saldo_cancelado         Real NOT NULL
├── fecha_registro_original Text NOT NULL
└── fecha_cancelacion       Text NOT NULL

familiares                                 (pares de clientes emparentados)
├── id_vinculo              Integer, PK
├── id_cliente_a            FK → clientes (el menor de los dos id_cliente)
├── id_cliente_b            FK → clientes (el mayor de los dos id_cliente)
├── CHECK (id_cliente_a < id_cliente_b)
└── UNIQUE INDEX uq_familiares(id_cliente_a, id_cliente_b)
```

> Cada fila declara un par. Un cliente acumula vínculos apareciendo en varias filas
> (como `id_cliente_a` o `id_cliente_b`), hasta un máximo de 4 por cliente —
> validado en el servicio al vincular, no por constraint de base de datos. No
> existen grupos familiares ni una fila con más de 2 clientes.

### 3.4 Diseño de Apartado (cabecera-detalle)

```
apartados                                  (cabecera)
├── id_apartado             Integer, PK
├── id_cliente              FK → clientes
├── fecha_apartado          DateTime
├── monto_primer_pago       Float (mínimo $100, por lote)
├── saldo_pendiente         Float (Σ precio_producto − monto_primer_pago)
└── estatus                 Enum (abierto|liquidado)

apartados_articulos                        (detalle, 1 a N artículos por lote)
├── id_apartado_articulo    Integer, PK
├── id_apartado             FK → apartados
├── id_producto             FK → inventario, nullable
├── precio_producto         Float (autollenado o manual, siempre persistido)
└── estatus_articulo        Enum (vigente|vendido|cancelado)

movimientos.id_apartado     FK → apartados, nullable
```

---

## 4. Mapa de archivos

### 4.1 Módulos cerrados (implementados y con test en verde)

| Archivo                                 | Rol                   | Estado                                                                    |
| --------------------------------------- | --------------------- | ------------------------------------------------------------------------- |
| `app/models/models.py`                  | Modelo de datos       | ✅ 18 tablas. Sincronizado con spec (migración `f6a7b8c9d0e1`).           |
| `alembic/versions/*.py`                 | 6 migraciones         | ✅ Head `f6a7b8c9d0e1`. Migración del rediseño completada.                |
| `app/schemas/pedido.py`                 | Schema Pedido         | Cabecera-detalle, valida reglas por `tipo_producto`/`proveedor`.           |
| `app/services/pedido_service.py`        | Lógica Pedido         | Lookup de precio, transacciones de devolución/cancelación.                |
| `app/api/v1/endpoints/pedidos.py`       | Endpoints Pedido      | 4 flujos probados end-to-end.                                             |
| `app/schemas/pedido_shein.py`           | Schema Shein          | **En progreso:** incluye `frecuencia_pago`. Faltan endpoints de abono.    |
| `app/services/pedido_shein_service.py`  | Lógica Shein          | **En progreso:** crea cliente con `frecuencia_pago`. Falta lógica de `saldo`.|
| `app/api/v1/endpoints/pedidos_shein.py` | Endpoints Shein       | **Desincronizado:** falta endpoint de abono Shein.                        |
| `app/schemas/inventario.py`             | Schema Inventario     | —                                                                         |
| `app/services/inventario_service.py`    | Lógica Inventario     | Transiciones validadas, descuento masivo.                                 |
| `app/api/v1/endpoints/inventario.py`    | Endpoints Inventario  | —                                                                         |
| `app/schemas/cliente.py`                | Schema Cliente        | Expone las 4 banderas (`amarilla`/`roja`/`naranja`/`negra`), schemas de cancelación (`CarteraVencidaRead`) y de familiares (`FamiliarVincular`/`FamiliarRead`). |
| `app/services/cliente_service.py`       | Lógica Cliente        | Sistema de banderas completo; `cancelar_cliente()` (precondición `bandera_roja`, snapshot a `cartera_vencida`, limpieza de slot conservando `no_cliente`/`id_cliente`); vinculación/desvinculación de familiares con tope de 4 validado para ambos clientes del par. |
| `app/api/v1/endpoints/clientes.py`      | Endpoints Cliente     | `POST /{id}/cancelar`, `GET/POST /{id}/familiares`, `DELETE /{id}/familiares/{id_vinculo}`. |
| `app/scripts/importar_precios.py`       | Import de precios     | 15,564 filas insertadas. Solo `INSERT`.                                   |
| `app/schemas/movimiento.py`             | Schema Movimiento     | —                                                                         |
| `app/schemas/apartado.py`               | Schema Apartado       | —                                                                         |
| `app/services/movimiento_service.py`    | Lógica Movimientos    | `contado`/`abono`/`gasto`/`apartado` completos.                           |
| `app/models/models.py` (`Usuario`)      | Modelo Auth           | —                                                                         |
| `app/schemas/usuario.py`                | Schema Auth           | —                                                                         |
| `app/schemas/token.py`                  | Schema Auth           | —                                                                         |
| `app/services/auth_service.py`          | Lógica Auth           | —                                                                         |
| `app/api/v1/endpoints/auth.py`          | Endpoint Auth         | —                                                                         |
| `app/api/v1/endpoints/movimientos.py`   | Endpoint Movimientos  | **No expone `crear_apartado()`** — `apartados.py` no existe.              |
| `app/db/database.py`                    | Conexión BD           | SQLAlchemy síncrono.                                                      |
| `app/core/config.py`                    | Configuración         | Solo `DATABASE_URL`. Sin `AUTH_ENABLED`.                                  |
| `app/main.py`                           | Bootstrap FastAPI     | Sin `init_db()`. CORS `localhost:5173`.                                   |
| `app/schemas/setting.py`                | Schema Setting        | —                                                                         |
| `app/api/v1/endpoints/setting.py`       | Endpoints Setting     | Sin `setting_service.py` — excepción deliberada.                          |

### 4.2 Tests (todos en verde en la build previa al rediseño)

| Test                        | Módulo      | Estado               |
| --------------------------- | ----------- | -------------------- |
| `test/test_pedidos.py`      | Pedidos     | ✅ en verde           |
| `test/test_inventario.py`   | Inventario  | ✅ 19/19 en verde     |
| `test/test_shein.py`        | Shein       | ✅ 28/28 — **requiere actualización por rediseño Shein** |
| `test/test_clientes.py`     | Clientes    | ✅ 76/76 en verde     |
| `test/test_movimientos.py`  | Movimientos | ✅ 28/28 en verde     |
| `test/test_apartados.py`    | Apartados   | ✅ 12/12 en verde     |
| `test/test_autenticacion.py`| Auth        | ✅ 59/59 en verde     |
| `test/test_recargas.py`     | Recargas    | ✅ 17/17 en verde     |
| `test/test_setting.py`      | Setting     | ✅ 26/26 en verde     |

### 4.3 Sin código todavía

| Módulo / Funcionalidad       | Spec disponible                                    |
| ---------------------------- | -------------------------------------------------- |
| Endpoint Apartado            | `module_movimientos.md` — servicio existe, endpoint no. `app/api/v1/endpoints/apartados.py` no existe. |
| Consulta Finanzas            | `module_consulta_finanzas.md` ✅ (creado en rediseño) |
| Espejo Android               | `docs/spec/SPEC_STACK_ANDROID.md` ✅ (spec ya definida). Ver §5. |

---

## 5. Orden de prioridad (jerarquía → código)

### Cerrados ✅

Niveles 1-4 completos. Auth, Setting, todos los módulos existentes con test en verde.
Bloque A (modelo de datos) y Bloque B (Módulo Clientes) del rediseño, completos.
Ver §4.2 para el detalle.

### Tareas pendientes — por orden de ejecución

**Bloque A — Modelo de datos (✅ COMPLETADO)**

16. [x] Agregar migración Alembic para:
    - Columnas nuevas en `shein_clientes`: `saldo`, `estatus`, `frecuencia_pago`,
      `dia_pago_especifico`, `frecuencia_pago_detalle`, `fecha_pago_programada`.
    - Tabla nueva `cartera_vencida` (sin FKs).
    - Tabla nueva `familiares` (FKs a `clientes`, constraint + índice único).
    - Tabla nueva `shein_movimientos` (FK a `shein_clientes`).
17. [x] Actualizar `models.py` con los nuevos modelos y columnas.
18. [x] Actualizar `resumen_tablas.md` en `docs/spec/` con las tablas nuevas.
19. [x] Actualizar `docs/spec/README.md` con `module_consulta_finanzas.md` en el mapa de módulos.

**Bloque B — Módulo Clientes (✅ COMPLETADO)**

20. [x] Actualizado `app/schemas/cliente.py`: agrega `bandera_amarilla`, `bandera_roja`, `bandera_negra` (además de `bandera_naranja` ya existente), `CarteraVencidaRead`, `FamiliarVincular`, `FamiliarRead`.
21. [x] Actualizado `app/services/cliente_service.py`:
    - `cancelar_cliente()` — precondición `bandera_roja` activa; snapshot a `cartera_vencida`; limpieza del slot (conserva `no_cliente` e `id_cliente`).
    - `calcular_bandera_amarilla()`, `calcular_bandera_roja()`, `calcular_bandera_negra()` (consulta `familiares` + `bandera_roja` de cada familiar).
    - Vinculación/desvinculación de familiares (máx. 4 vínculos por cliente, validado en el servicio para ambos clientes del par).
22. [x] Actualizado `app/api/v1/endpoints/clientes.py`:
    - Endpoint `POST /{id}/cancelar`.
    - Endpoints `GET/POST /{id}/familiares` (listar/vincular) y `DELETE /{id}/familiares/{id_vinculo}` (desvincular).
23. [x] Redactado `test/test_clientes.py` desde cero — 76/76 en verde.

**Bloque C — Módulo Shein**

24. Actualizar `app/schemas/pedido_shein.py`:
    - `SheinClienteCreate` / `SheinClienteRead` con campos de cartera.
    - `SheinMovimientoCreate` / `SheinMovimientoRead` (nuevo).
25. Actualizar `app/services/pedido_shein_service.py`:
    - Carga de `saldo` al guardar corte (`saldo += monto_pedido` por `shein_cliente`).
    - `registrar_abono_shein()` — reduce `saldo`, recalcula `fecha_pago_programada`.
    - `calcular_bandera_shein()` — amarilla y roja.
26. Actualizar `app/api/v1/endpoints/pedidos_shein.py`:
    - Endpoint `POST /shein/abono`.
27. Actualizar `test/test_shein.py` con los nuevos flujos de cartera.

**Bloque D — Endpoint Apartado (pendiente pre-rediseño)**

28. Crear `app/api/v1/endpoints/apartados.py` — exponer `crear_apartado()` del servicio existente.
29. Registrar el router en `main.py`.

**Bloque E — Módulo Consulta Finanzas**

30. Construir spec → código → test:
    - Schema de solo lectura.
    - Service con las 3 consultas (Cortes por periodo, Ventas por segmento, Detalle tienda).
    - Endpoints `GET /consulta-finanzas/cortes`, `GET /consulta-finanzas/segmentos`, `GET /consulta-finanzas/detalle`.
    - `test/test_consulta_finanzas.py`.

**Bloque F — Espejo Android**

31. Actualizar `docs/ARQUITECTURA.md`: el sistema deja de ser local-only; documentar
    el nuevo modelo de sincronización multi-dispositivo.
32. [x] Spec técnica del espejo Android definida en `docs/spec/SPEC_STACK_ANDROID.md`
    (stack, mecanismo de sincronización con el backend FastAPI, alcance funcional).
33. Implementar según `docs/spec/SPEC_STACK_ANDROID.md`.

**Bloque G — Checklist real**

34. Criterio de completado de la sesión de trabajo: pipeline + test en verde para cada bloque.

---

## 6. Cómo usar este documento en una sesión nueva

Si retomas el trabajo y solo compartes `REPORT.md`, ya se sabe: qué está
decidido (§3), el estado del modelo de datos (§2), qué evidencia hay de cada
archivo (§4), y el orden de prioridad completo (§5).

No hace falta resubir los archivos de §4.1 — solo los que se vayan a tocar
o cualquier archivo que haya cambiado desde la última actualización.

**Siguiente paso inmediato:** Bloque C — Módulo Shein. Empezar por actualizar `app/schemas/pedido_shein.py` (`SheinClienteCreate`/`SheinClienteRead` con campos de cartera, `SheinMovimientoCreate`/`SheinMovimientoRead`), luego `app/services/pedido_shein_service.py` (carga de `saldo` al guardar corte, `registrar_abono_shein()`, `calcular_bandera_shein()` amarilla/roja) y finalmente exponer `POST /shein/abono` en `app/api/v1/endpoints/pedidos_shein.py`.
