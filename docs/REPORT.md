# REPORT — Mapa de Estado del Proyecto (pos-boutique)

> **Qué es este documento:** una fotografía acumulativa de decisiones tomadas,
> evidencia confirmada y huecos de visibilidad. No es un checklist de tareas
> (eso es `CHECKLIST.md`, aún no construido) ni la spec de negocio (eso es
> `REGLAS_NEGOCIO.md` / `00_FULLSTACK_DEVELOPMENT.md`). Es el documento que
> permite retomar el trabajo en cualquier sesión nueva sin tener que recargar
> todo el repo. **Se actualiza cada vez que se revisa código nuevo o se toma
> una decisión.** Última actualización: tras revisión de `INCONCISTENCIAS.md`
> (auditoría de un agente externo, 2 sesiones) y relectura completa de
> `00_FULLSTACK_DEVELOPMENT.md` — el documento maestro **ya contiene** la
> sección `tabla_precios` que esta misma versión del REPORT marcaba como
> pendiente del usuario. Ver §0.

---

## 0. Cambio de estado desde la última versión de este documento

Esta pendiente el prerrequisito *técnico*: agregar
`precios_catalogo` a `models.py` + migración Alembic + script `importar_precios.py`
(nadie ha tocado código todavía, solo se confirmó que la spec ya no es el cuello
de botella). Ver §6 para la ruta de trabajo reordenada.

**Nota de disciplina:** la sección "Resumen de tablas del sistema" al final de
`00_FULLSTACK_DEVELOPMENT.md` (línea ~2295) ya lista 12 tablas, incluyendo
`precios_catalogo` junto a las 11 que este REPORT confirma como migradas en
`pos.db`. Eso es esperado — la spec puede ir adelante del código migrado, es
exactamente el caso aquí. No es una inconsistencia, es el estado normal de un
prerrequisito de spec ya resuelto y un prerrequisito de implementación pendiente.

---

## 1. Jerarquía de fuentes (no reabrir sin razón explícita)

1. **`docs/00_FULLSTACK_DEVELOPMENT.md`** — spec de UI/UX, autoridad máxima si hay
   contradicción. **Ya no tiene pendientes conocidos** (ver §0). Único hallazgo:
   una inconsistencia *interna* del propio archivo, no una sección faltante — ver
   §4a (INC-13).
2. **`docs/REGLAS_NEGOCIO.md`** — modelo de datos + reglas de negocio, derivado de
   (1). **Pendiente:** agregar definición formal de tabla `precios_catalogo`
   (columnas, regla de no-unicidad de `id_producto`, FK conceptual a
   `pedidos_articulos.id_producto`). Este pendiente sigue abierto — la sección
   nueva de (1) no se ha propagado todavía a este archivo. Lo actualiza el
   usuario, no Claude.
3. **`docs/ARQUITECTURA.md`** — decisiones técnicas, derivado de evidencia de
   código real. Sección 5 (Autenticación) corregida — ver §5.
4. **`docs/README.md`** — orientación y arranque.
5. **`backend/app/models/models.py`** — implementado y migrado. 11 tablas en
   `pos.db`, alineadas a spec maestra. **Pendiente:** agregar tabla
   `precios_catalogo` (diseño cerrado, ver §2a — ya no bloqueado por la spec).

---

## 2. Decisiones ya cerradas (no volver a discutir salvo nueva evidencia)

| Decisión | Resultado |
|---|---|
| ¿Se conserva data de `pos.db`? | **No.** Reset limpio ejecutado ✅. 11 tablas creadas desde `models.py` nuevo vía Alembic (`a1b2c3d4e5f6_esquema_inicial.py`). |
| ¿Multi-empresa / multi-sucursal? | **No existe ni se planea.** Negocio único, una operadora. |
| ¿Async o sync en SQLAlchemy? | **Síncrono**, confirmado en `database.py` (`create_engine` estándar, sin `aiosqlite`). |
| ¿`telefono`/`ref_telefono` tipo de dato? | `Integer` (10 dígitos), no `String`. En `models.py` implementado. Rompe `schemas/cliente.py` actual — pendiente de ajuste (§6 paso 5; línea exacta en §3.1 / INC-01). |
| ¿Nombres de campo en `Usuario`? | `usuario` (no `username`) y `password_hash` (no `hashed_password`). Rompe `schemas/usuario.py` y `auth.py` actuales — pendiente de ajuste (§6 paso 7; línea exacta en §3.1 / INC-08). |
| ¿`pedidos` plano o cabecera-detalle? | **Cabecera-detalle** (`pedidos` + `pedidos_articulos`), 1 a 4 artículos principales, cada uno con 0 o 1 alternativa. Archivos viejos se reemplazan completos. |
| ¿Shein comparte tabla de clientes? | **No.** `shein_clientes` independiente. `pedidos_shein.py` actual se reemplaza. |
| Estructura de documentación | `00_FULLSTACK_DEVELOPMENT.md` = spec de UI. `REGLAS_NEGOCIO.md` = modelo de datos. `ARQUITECTURA.md` = decisiones técnicas. `REPORT.md` = estado, no spec. |
| ¿`init_db.py` en `lifespan`? | **Resuelto en código, no solo cerrado como decisión.** Ver §5 punto 4 — `main.py` ya no llama `init_db()`. Confirmado por INC-12, contradice la versión anterior de este REPORT que aún lo listaba como riesgo activo. |
| ¿`precios_catalogo` en SQLite? | **Sí.** Tabla nueva, pendiente de agregar a `models.py` + migración Alembic. Diseño cerrado — ver §2a. La spec que la documenta ya existe (§0) — el pendiente ahora es puramente de implementación. |
| ¿Cómo se sincroniza `tabla_precios.ods` con SQLite? | **Disparador manual:** script `backend/app/scripts/importar_precios.py`. El usuario lo corre cuando el proveedor libera catálogo nuevo. Solo `INSERT` de filas nuevas — nunca borra, nunca sobreescribe. SQLite acumula historial completo. |
| ¿Qué columnas guarda `precios_catalogo`? | Todas las columnas del `.ods` (incluidas las "inútiles para el POS" como `catalogo`, `pag`, `redondea`). SQLite las soporta sin problema y preservan fidelidad del archivo original. |
| ¿Cómo resuelve el POS el precio de un artículo? | `SELECT precio_venta WHERE proveedor = :p AND id_producto = :id ORDER BY fecha_catalogo DESC LIMIT 1` — gana la fecha más reciente. |
| ¿`id_producto` es único por proveedor? | **No.** El mismo `id_producto` puede repetirse en catálogos futuros (producto que sigue vigente). Sin restricción `UNIQUE`. Desempate siempre por `MAX(fecha_catalogo)`. |
| ¿Cuándo sube el saldo de un artículo de pedido? | Al marcarse `en_almacen`, no al registrar el pedido (`00_FULLSTACK_DEVELOPMENT.md` líneas 634–646). Dato nuevo confirmado en esta revisión, no estaba en versiones previas del REPORT. |

### §2a — Diseño de tabla `precios_catalogo` (cerrado, pendiente de implementar)

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
├── pagina            Integer      ← Pag / PÁG. / pag según pestaña
└── precio_base       Integer      ← Sug_credito / 2 PAGO / precio_base según pestaña
```

Sin restricción `UNIQUE`. Mapeo de columnas identificadoras por pestaña del `.ods`,
confirmado idéntico entre `tabla_precios.ods` (revisión directa del archivo) y
`00_FULLSTACK_DEVELOPMENT.md` líneas 656–660 (documentación nueva del usuario):

| Pestaña | Columna id en .ods | Columna precio en .ods | Columna base en .ods |
|---|---|---|---|
| `price_shoes` | `ID` | `precio_venta` | `Sug_credito` |
| `pakar` | `CÓDIGO` | `precio_venta` | `2 PAGO` |
| `cklass` | `modelo` | `precio_venta` | `precio_base` |

Nota: `fecha` en `price_shoes`/`pakar` viene como texto (`"02-mayo-2026"`); en
`cklass` como fecha ISO. El script de import normaliza ambos formatos a `Date`
ISO antes de insertar.

---

## 3. Mapa de archivos — qué se ha visto, qué no, qué no existe

### 3.1 Confirmados con evidencia directa

| Archivo | Rol | Hallazgo clave |
|---|---|---|
| `app/models/models.py` (nuevo) | Modelo de datos vigente | Implementado y migrado ✅. 11 tablas en `pos.db`. Falta `precios_catalogo` (12ª, ya diseñada en §2a). |
| `alembic/versions/a1b2c3d4e5f6_esquema_inicial.py` | Migración inicial nueva | Única migración vigente. Esquema limpio alineado a spec. |
| `app/models/models.py` (original, `.bak`) | Modelo viejo | Solo referencia histórica. No se toca. |
| `app/db/init_db.py` | Inicializador de BD | Llama `Base.metadata.create_all()`. La función en sí sigue existiendo en el archivo, pero ya **no se invoca desde `main.py`** — ver fila siguiente y §5 punto 4. |
| `app/main.py` | Bootstrap FastAPI | **Corregido respecto a versión anterior del REPORT.** Líneas 8–12 traen un comentario explícito confirmando que `init_db()` ya no se ejecuta en `lifespan` y que Alembic es la única fuente de esquema (INC-12). Registra 5 routers. CORS solo a `localhost:5173`. |
| `app/schemas/cliente.py` | Schema Cliente | Tres problemas confirmados con línea exacta (INC-01, INC-02, INC-10): `telefono: str` en L9 / `ref_telefono: Optional[str]` en L12 (debería ser `int`, ver INC-01); `ClienteCreate` (L6–19) no incluye `frecuencia_pago`, campo `nullable=False` en el modelo (INC-02, ver impacto crítico en §5); `ClienteRead` (L22–35) no incluye `fecha_pago_programada`, presente en el modelo y requerido por la pantalla de Consulta Historial (INC-10, `00_FULLSTACK_DEVELOPMENT.md` L452). Pendiente §6 paso 5. |
| `app/services/cliente_service.py` | Lógica Cliente | `estatus == "liquidado"` en `rehabilitar_cliente()` L67, L73 — no existe en el enum nuevo (`activo`/`inactivo`), INC-07. Además, confirmado en esta revisión: `crear_cliente()` (L26–36) no asigna `frecuencia_pago` — va a fallar el `INSERT` en producción porque la columna es `nullable=False` (esto es la otra cara de INC-02, ahora confirmada también del lado del servicio, no solo del schema). `crear_cliente()` tampoco asigna `fecha_pago_programada`, pero esa columna sí es `nullable=True` — **no es un bug**, es el comportamiento correcto: queda `NULL` hasta el primer abono, según la regla de negocio del ciclo de `fecha_pago_programada`. Pendiente §6 paso 5. |
| `app/schemas/movimiento.py` | Schema Movimiento | `notas: Optional[str]` en L13 y L43, debería ser `descripcion` (modelo usa `descripcion = Column(String(60))`, INC-03). Sin validación de `descripcion` obligatoria cuando `operacion = 'gasto'` (`model_validator` en L22–32 solo valida ausencia de `id_cliente`, no presencia de descripción — INC-04). Pendiente §6 paso 6. |
| `app/services/movimiento_service.py` | Lógica Movimiento | **Más bugs de los documentados originalmente — ver desglose completo en §5.** Confirmado con línea exacta: sobrescritura de saldo (L37, INC-05), estatus `"liquidado"` inexistente (L52, INC-07), `notas=data.notas` no mapea a columna real (L61, INC-03/INC-11), sin validación de mínimo $100 (L28–36, INC-06). Hallazgo nuevo de esta revisión: `cancelar_movimiento()` tiene un bug de diseño, no solo de typo — ver §5 punto 5. Pendiente §6 paso 6. |
| `app/db/database.py` | Conexión BD | SQLAlchemy síncrono confirmado. `get_db()` estándar. |
| `app/core/config.py` | Configuración | Solo tiene `DATABASE_URL`. No existe `AUTH_ENABLED`. `SECRET_KEY` no está aquí. |
| `app/api/v1/endpoints/auth.py` | Endpoint login | JWT real vía `auth_service.crear_token`. Llama `usuario.username` — rompe con rename. Pendiente §6 paso 7. |
| `app/schemas/usuario.py` | Schema Usuario | Visto y confirmado con línea exacta (INC-08): `UsuarioRead` (L26–33) define `username: str` (L28) cuando el modelo tiene `usuario`; `activo: str` (L30) cuando el modelo tiene `Integer`. Con `from_attributes = True`, Pydantic intentará leer `obj.username`, que no existe — error de serialización. Bloqueante para §6 paso 7. |
| `app/schemas/token.py` | Schema Token | Visto y confirmado (INC-09): `TokenData.username` (L13) en vez de `usuario`. **No es un bug funcional** — es un nombre interno del schema, no mapea al modelo vía `from_attributes`, y `auth_service.py` lo usa de forma consistente (`auth_service.py` L103, L107). Es una inconsistencia de nomenclatura, no de comportamiento. Severidad baja, no bloqueante. |
| `app/api/v1/endpoints/clientes.py` | Endpoints Cliente | Todos protegidos con `Depends(get_current_user)`. |
| `app/api/v1/endpoints/movimientos.py` | Endpoints Movimiento | Mismo patrón de protección. CRUD básico completo. |
| `app/api/v1/endpoints/pedidos.py` | Endpoints Pedido (viejo) | Modelo plano. Se reemplaza completo — §6 paso 4. |
| `app/api/v1/endpoints/pedidos_shein.py` | Endpoints Shein (viejo) | FK a `clientes` (incorrecto). Se reemplaza completo — §6 paso 4. |
| `app/schemas/pedido.py` | Schema Pedido (viejo) | Estructura plana con `opcion_*`. Referencia de qué NO repetir. |
| `app/schemas/pedido_shein.py` | Schema Shein (viejo) | Visto. Se reemplaza completo. |
| `app/services/pedido_service.py` | Lógica Pedido (viejo) | Modelo plano: `Pedido(producto=..., marca=..., talla=...)`. Sin nada reutilizable — se reemplaza completo. |
| `requirements.txt` | Dependencias | `python-jose` + `passlib`/`bcrypt` — JWT real. Sin `pytest`. Pendiente agregar `odfpy` para script de import. |
| `docs/00_FULLSTACK_DEVELOPMENT.md` | Spec UI/UX | **Releída completa, no solo sección Pedidos.** Confirma `tabla_precios`/`precios_catalogo` (L648–698), módulo Inventario (L1122–1340), módulo Recargas (L2004–2077), módulo Setting (L2238–2295) — los cuatro ya documentados, ver §0. Único hallazgo: inconsistencia interna de longitud de `producto` (INC-13, ver §4a). |
| `tabla_precios.ods` | Catálogo de precios por proveedor | 3 pestañas (`price_shoes`, `pakar`, `cklass`). Esquema documentado en §2a, ahora también reflejado en la spec maestra (L648–698). Fuente de verdad operativa — se mantiene en `.ods`, se sincroniza a SQLite vía script manual. |

### 3.2 Mencionados pero NO vistos (huecos de visibilidad — pedir antes de tocar)

| Archivo | Por qué importa |
|---|---|
| `app/services/auth_service.py` | Contiene `autenticar_usuario`, `crear_token`, `get_current_user`. El `INCONCISTENCIAS.md` cita líneas concretas (L46–48, L103, L107) que sugieren que el archivo sí fue leído por el agente externo, pero **Claude no lo ha visto directamente todavía** en esta sesión — las citas se toman como evidencia reportada, no verificada de primera mano. Sigue bloqueante para §6 paso 7 hasta confirmación directa. |
| `app/services/pedido_shein_service.py` | Lógica Shein vieja — confirmar antes de reemplazar si tiene algo reutilizable. |
| Endpoints/servicios de Inventario | No hay evidencia de que existan en código — la spec (§0) ya está completa, pero el backend de Inventario sigue sin construirse. Pendiente §6. |
| Endpoints/servicios de Recargas | Mismo caso que Inventario: spec completa (§0), cero evidencia de código. Pendiente §6. |
| Endpoints/servicios de Setting/Configuración | Mismo caso: spec completa (§0) marcada explícitamente como "esqueleto MVP", cero evidencia de código. Pendiente §6. |
| `backend/tests/*` | Contenido real no visto. Referenciado como "vacío". |
| `.env` / variables de entorno reales | No vistas. `config.py` solo define el default de `DATABASE_URL`. |
| `docs/REGLAS_NEGOCIO.md` | No releído en esta sesión. Sigue con el pendiente de §1 (agregar `precios_catalogo`). |

---

## 4. Riesgos activos confirmados (bugs con evidencia, no inferencias)

1. **Sobrescritura de saldo en apartado** (`movimiento_service.py` L37) —
   `cliente.saldo = saldo_resultante` en vez de `cliente.saldo += saldo_resultante`.
   Confirmado con cita de código (INC-05). Spec: `00_FULLSTACK_DEVELOPMENT.md`
   L1682, `UPDATE clientes SET saldo = saldo + :saldo_resultante`.

2. **Sin mínimo de $100 en apartado** (`movimiento_service.py` L28–36) — la rama
   de `apartado` solo valida `monto < 0`, no `monto >= 100`. Confirmado (INC-06).
   Spec: `00_FULLSTACK_DEVELOPMENT.md` L1579.

3. **Estados de cliente obsoletos (`"liquidado"`)** — aparece en **tres** lugares,
   no uno (corrección sobre la versión anterior de este REPORT, que solo
   mencionaba el campo en general):
   - `movimiento_service.py` L52 — `registrar_movimiento()` lo asigna cuando
     `saldo` llega a 0 tras un abono.
   - `movimiento_service.py` (en `cancelar_movimiento()`) — lo vuelve a poner
     como `"activo"` al revertir, heredando el mismo problema de fondo.
   - `cliente_service.py` L67, L73 — `rehabilitar_cliente()` lee y escribe
     `"liquidado"` al cambiar a `"activo"`.
   El enum nuevo (`models.py` L45–47, `EstatusCliente`) solo tiene `activo` e
   `inactivo`. Parchar solo la asignación original (L52) deja el revert de
   `cancelar_movimiento()` con el mismo problema de fondo — los tres puntos
   deben corregirse juntos, no uno a la vez (INC-07).

4. **`cancelar_movimiento()` — bug de diseño, no de línea.** Hallazgo nuevo de
   esta sesión, no estaba en `INCONCISTENCIAS.md` original. Al revertir un
   movimiento, el método busca el `saldo_resultante` del movimiento *anterior*
   del cliente completo, **sin filtrar por tipo de operación**. Si ese
   movimiento anterior fue un `apartado` afectado por el bug del punto 1 (que
   nunca sumó correctamente al saldo previo), el "saldo anterior" recuperado es
   matemáticamente incorrecto — y ese error persiste **independientemente** de
   que se corrija el `+=` del punto 1, porque ya hay datos de prueba
   potencialmente viciados si se corrió antes del fix. Este método necesita
   rediseño de la lógica de reversión, no un parche de una línea. Depende de
   cómo quede resuelto el punto 1 primero — no se puede arreglar en paralelo.

5. **`crear_cliente()` no asigna `frecuencia_pago`** (`cliente_service.py`
   L26–36) — la columna es `nullable=False` en el modelo (`models.py` L122).
   El primer `INSERT` real fallará en tiempo de ejecución. Esto es más grave
   que un campo faltante cosmético: es un crash garantizado, no una
   degradación silenciosa. Confirma INC-02 con evidencia del lado del
   servicio, no solo del schema (`ClienteCreate` tampoco lo incluye).

> **Nota retirada de esta versión:** el riesgo anterior "`init_db()` en
> `lifespan`" ya no aparece en esta lista — está resuelto en código, ver §4
> y §0.

---

## 5. Ruta de trabajo (orden, no checklist de tareas individuales)

1. ✅ Cerrar huecos bloqueantes de `init_db.py` — riesgo confirmado como resuelto
   en código (`main.py` ya no lo invoca, INC-12). Ya no requiere acción.
2. ✅ Implementar `models.py` aprobado en el repo real.
3. ✅ Reset limpio de BD + migración inicial nueva (`a1b2c3d4e5f6_esquema_inicial.py`).
   11 tablas en `pos.db`.
4. **DESBLOQUEADO — listo para iniciar.** Reescritura completa del módulo Pedidos:
   - ~~Prerrequisito de spec~~ — **resuelto.** `tabla_precios` ya está documentada
     en `00_FULLSTACK_DEVELOPMENT.md` (L648–698, ver §0). El pendiente que cerraba
     este paso en la versión anterior del REPORT ya no existe.
   - Prerrequisito técnico restante (sin iniciar): agregar `precios_catalogo` a
     `models.py` + migración Alembic + script `importar_precios.py`.
   - Una vez hecho lo anterior: `schemas/pedido.py` (nuevo),
     `services/pedido_service.py` (nuevo), `endpoints/pedidos.py` (nuevo). Cubre
     4 flujos: Registrar Pedido, Registrar Devolución, Cancelar Artículo, Lista
     de Surtido.
   - Shein: `schemas/pedido_shein.py` (nuevo), `services/pedido_shein_service.py`
     (nuevo), `endpoints/pedidos_shein.py` (nuevo).
5. Ajuste de `schemas/cliente.py` y `services/cliente_service.py`:
   - Quitar `"liquidado"` de `rehabilitar_cliente()`.
   - Ajustar tipo `telefono`/`ref_telefono` a `int` (INC-01).
   - Agregar `frecuencia_pago` a `ClienteCreate` y a la construcción del objeto
     en `crear_cliente()` — bloqueante de crash, no cosmético (INC-02, §5 punto 5).
   - Agregar `fecha_pago_programada` a `ClienteRead` (INC-10).
6. Ajuste de `schemas/movimiento.py` y `services/movimiento_service.py`:
   - Renombrar `notas` → `descripcion` en schema y en la construcción del objeto
     `Movimiento` (INC-03, INC-11).
   - Agregar validación de `descripcion` obligatoria cuando `operacion = 'gasto'`
     (INC-04).
   - Corregir suma de saldo: `cliente.saldo += saldo_resultante` (§5 punto 1).
   - Agregar validación de mínimo $100 en apartado (§5 punto 2).
   - Quitar `"liquidado"` de los tres puntos identificados en §5 punto 3,
     no solo de `registrar_movimiento()`.
   - Rediseñar `cancelar_movimiento()` para filtrar por tipo de operación al
     recuperar el saldo anterior (§5 punto 4) — depende de que el punto de
     suma de saldo ya esté corregido.
7. Ajuste de `auth.py` + `auth_service.py` + `schemas/usuario.py` (rename
   `username`→`usuario`, `hashed_password`→`password_hash`, `activo: str`→`int`
   en `UsuarioRead`). Requiere ver `auth_service.py` directamente antes de tocarlo
   — las citas de línea en `INCONCISTENCIAS.md` (L46–48, L103, L107) son evidencia
   reportada por el agente externo, no verificada de primera mano todavía (§3.2).
   `schemas/token.py` no requiere cambio funcional (INC-09, severidad baja).
8. Construcción desde cero de Inventario — **spec ya completa y disponible**
   (`00_FULLSTACK_DEVELOPMENT.md` L1122–1340), solo falta schema + servicio +
   endpoint en código.
9. Construcción desde cero de Recargas (spec en L2004–2077) y Setting/Configuración
   (spec en L2238–2295, explícitamente alcance "esqueleto MVP" — no construir
   lógica de permisos diferenciada todavía).
10. Antes o junto con el paso 4: usuario decide y corrige la inconsistencia interna
    de longitud de `producto` (40 vs 50, INC-13/§4a) en `00_FULLSTACK_DEVELOPMENT.md`.
    No bloquea el inicio del paso 4, pero sí debe resolverse antes de fijar el
    `String(N)` definitivo en el nuevo `models.py`.
11. Solo entonces: `CHECKLIST.md` real, con criterio de completado = pipeline + test.

---

## 6. Acción pendiente del usuario sobre la documentación

A diferencia de la versión anterior de este REPORT, **ya no hay ninguna sección
faltante que el usuario deba redactar en `00_FULLSTACK_DEVELOPMENT.md`** — la
relectura completa (§0) confirma que Pedidos, Inventario, Recargas y Setting ya
están documentados con el mismo nivel de detalle que Clientes y Panel Principal.

Queda un solo pendiente de edición, acotado y de tu lado, no de Claude (regla de
§1: tú editas `00_FULLSTACK_DEVELOPMENT.md`, Claude no lo reescribe):

- **Decidir y corregir INC-13** (§4a): el campo `producto` de `pedidos_articulos`
  aparece como `TEXT(40)` en el SQL (L583) y como `longitud: 50` en el schema
  JSON del formulario (L981). Elige el valor correcto y ajusta la otra línea para
  que coincidan. Esto es lo único que bloquea fijar el tipo definitivo de esa
  columna en el `models.py` nuevo cuando se llegue al paso 4/10 de §6.

Por separado, sigue pendiente — ya estaba así antes, no es nuevo — que `REGLAS_NEGOCIO.md`
incorpore la definición formal de `precios_catalogo` (columnas, no-unicidad de
`id_producto`, FK conceptual). No bloquea el trabajo de código porque
`00_FULLSTACK_DEVELOPMENT.md` ya trae el detalle suficiente; es deuda de
consistencia entre documentos, no un bloqueo técnico.

---

## 7. Cómo usar este documento en una sesión nueva

Si retomas el trabajo y solo compartes `REPORT.md`, ya sé: qué está decidido y no
se reabre (§2), qué cambió de estado desde la versión anterior (§0 y §4), qué
evidencia tengo y de dónde salió, línea por línea cuando aplica (§3.1), qué no he
visto todavía y debo pedir antes de asumir nada (§3.2), qué riesgos de código ya
están confirmados con su severidad real (§5), y qué falta de tu lado en la
documentación, acotado a un solo punto (§7).

No necesitas resubir los archivos de §3.1 — solo los que aparezcan en §3.2 cuando
lleguemos a tocarlos, o cualquier archivo que haya cambiado desde la última
actualización de este documento.

El siguiente paso de código, ya desbloqueado: agregar `precios_catalogo` a
`models.py` + migración Alembic + script `importar_precios.py` (§6 paso 4),
seguido de la reescritura de `schemas/pedido.py`, `services/pedido_service.py`
y `endpoints/pedidos.py`.
