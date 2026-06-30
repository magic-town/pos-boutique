# REPORT — Mapa de Estado del Proyecto (pos-boutique)

> **Qué es este documento:** una fotografía acumulativa de decisiones tomadas,
> evidencia confirmada y huecos de visibilidad. No es un checklist de tareas
> (eso es `CHECKLIST.md`, aún no construido) ni la spec de negocio (eso es
> `REGLAS_NEGOCIO.md` / `00_FULLSTACK_DEVELOPMENT.md`). Es el documento que
> permite retomar el trabajo en cualquier sesión nueva sin tener que recargar
> todo el repo. **Se actualiza cada vez que se revisa código nuevo o se toma
> una decisión.** Última actualización: tras revisión de `init_db.py`,
> `pedidos.py`, `pedido.py`, `pedido_service.py`, `models.py` (nuevo),
> `tabla_precios.ods`, y `00_FULLSTACK_DEVELOPMENT.md` (sección Pedidos completa).

---

## 1. Jerarquía de fuentes (no reabrir sin razón explícita)

1. **`docs/00_FULLSTACK_DEVELOPMENT.md`** — spec de UI/UX, autoridad máxima si hay contradicción. **Pendiente:** agregar sección sobre `tabla_precios.ods` (esquema real de pestañas, regla de desempate por `MAX(fecha_catalogo)`, disparador manual de sincronización). Lo actualiza el usuario, no Claude.
2. **`docs/REGLAS_NEGOCIO.md`** — modelo de datos + reglas de negocio, derivado de (1). **Pendiente:** agregar definición formal de tabla `precios_catalogo` (columnas, regla de no-unicidad de `id_producto`, FK conceptual a `pedidos_articulos.id_producto`). Lo actualiza el usuario, no Claude.
3. **`docs/ARQUITECTURA.md`** — decisiones técnicas, derivado de evidencia de código real. Sección 5 (Autenticación) ya corregida — ver §4.
4. **`docs/README.md`** — orientación y arranque.
5. **`backend/app/models/models.py`** — implementado y migrado. 11 tablas en `pos.db`, alineadas a spec maestra. **Pendiente:** agregar tabla `precios_catalogo` (decisión cerrada en esta sesión — ver §2).

---

## 2. Decisiones ya cerradas (no volver a discutir salvo nueva evidencia)

| Decisión | Resultado |
|---|---|
| ¿Se conserva data de `pos.db`? | **No.** Reset limpio ejecutado ✅. 11 tablas creadas desde `models.py` nuevo vía Alembic (`a1b2c3d4e5f6_esquema_inicial.py`). |
| ¿Multi-empresa / multi-sucursal? | **No existe ni se planea.** Negocio único, una operadora. |
| ¿Async o sync en SQLAlchemy? | **Síncrono**, confirmado en `database.py` (`create_engine` estándar, sin `aiosqlite`). |
| ¿`telefono`/`ref_telefono` tipo de dato? | `Integer` (10 dígitos), no `String`. En `models.py` implementado. Rompe `schemas/cliente.py` actual — pendiente de ajuste (§6 paso 5). |
| ¿Nombres de campo en `Usuario`? | `usuario` (no `username`) y `password_hash` (no `hashed_password`). Rompe `auth.py` actual — pendiente de ajuste (§6 paso 7). |
| ¿`pedidos` plano o cabecera-detalle? | **Cabecera-detalle** (`pedidos` + `pedidos_articulos`), 1 a 4 artículos principales, cada uno con 0 o 1 alternativa. Archivos viejos se reemplazan completos. |
| ¿Shein comparte tabla de clientes? | **No.** `shein_clientes` independiente. `pedidos_shein.py` actual se reemplaza. |
| Estructura de documentación | `00_FULLSTACK_DEVELOPMENT.md` = spec de UI. `REGLAS_NEGOCIO.md` = modelo de datos. `ARQUITECTURA.md` = decisiones técnicas. `REPORT.md` = estado, no spec. |
| ¿`init_db.py` en `lifespan`? | **Riesgo cerrado.** `init_db.py` llama `Base.metadata.create_all()`. Con el reset limpio ya ejecutado y Alembic como única fuente de esquema, esta llamada debe eliminarse de `main.py`. Pendiente de hacer al tocar `main.py`. |
| ¿`precios_catalogo` en SQLite? | **Sí.** Tabla nueva, pendiente de agregar a `models.py` + migración Alembic. Diseño cerrado — ver §2a. |
| ¿Cómo se sincroniza `tabla_precios.ods` con SQLite? | **Disparador manual:** script `backend/app/scripts/importar_precios.py`. El usuario lo corre cuando el proveedor libera catálogo nuevo. Solo `INSERT` de filas nuevas — nunca borra, nunca sobreescribe. SQLite acumula historial completo. |
| ¿Qué columnas guarda `precios_catalogo`? | Todas las columnas del `.ods` (incluidas las "inútiles para el POS" como `catalogo`, `pag`, `redondea`). SQLite las soporta sin problema y preservan fidelidad del archivo original. |
| ¿Cómo resuelve el POS el precio de un artículo? | `SELECT precio_venta WHERE proveedor = :p AND id_producto = :id ORDER BY fecha_catalogo DESC LIMIT 1` — gana la fecha más reciente. |
| ¿`id_producto` es único por proveedor? | **No.** El mismo `id_producto` puede repetirse en catálogos futuros (producto que sigue vigente). Sin restricción `UNIQUE`. Desempate siempre por `MAX(fecha_catalogo)`. |

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

Sin restricción `UNIQUE`. Mapeo de columnas identificadoras por pestaña del `.ods`:

| Pestaña | Columna id en .ods | Columna precio en .ods | Columna base en .ods |
|---|---|---|---|
| `price_shoes` | `ID` | `precio_venta` | `Sug_credito` |
| `pakar` | `CÓDIGO` | `precio_venta` | `2 PAGO` |
| `cklass` | `modelo` | `precio_venta` | `precio_base` |

Nota: `fecha` en `price_shoes`/`pakar` viene como texto (`"02-mayo-2026"`); en `cklass` como fecha ISO. El script de import normaliza ambos formatos a `Date` ISO antes de insertar.

---

## 3. Mapa de archivos — qué se ha visto, qué no, qué no existe

### 3.1 Confirmados con evidencia directa

| Archivo | Rol | Hallazgo clave |
|---|---|---|
| `app/models/models.py` (nuevo) | Modelo de datos vigente | Implementado y migrado ✅. 11 tablas en `pos.db`. |
| `alembic/versions/a1b2c3d4e5f6_esquema_inicial.py` | Migración inicial nueva | Única migración vigente. Esquema limpio alineado a spec. |
| `app/models/models.py` (original, `.bak`) | Modelo viejo | Solo referencia histórica. No se toca. |
| `app/db/init_db.py` | Inicializador de BD | Llama `Base.metadata.create_all()`. **Riesgo cerrado** (ver §2): debe eliminarse de `main.py` al tocar ese archivo. |
| `app/schemas/cliente.py` | Schema Cliente | `telefono: str` — rompe con `Integer` del modelo nuevo. Pendiente §6 paso 5. |
| `app/schemas/movimiento.py` | Schema Movimiento | Usa `notas`, no `descripcion`; sin validación de "obligatoria solo en gasto". Pendiente §6 paso 6. |
| `app/services/cliente_service.py` | Lógica Cliente | Usa `estatus == "liquidado"` (no existe en enum nuevo). Pendiente §6 paso 5. |
| `app/services/movimiento_service.py` | Lógica Movimiento | **Bug crítico:** `cliente.saldo = saldo_resultante` (sobrescribe, no suma). Sin mínimo $100. Usa `"liquidado"`. Pendiente §6 paso 6. |
| `app/main.py` | Bootstrap FastAPI | Llama `init_db()` en `lifespan` — eliminar al tocar. Registra 5 routers. CORS solo a `localhost:5173`. |
| `app/db/database.py` | Conexión BD | SQLAlchemy síncrono confirmado. `get_db()` estándar. |
| `app/core/config.py` | Configuración | Solo tiene `DATABASE_URL`. No existe `AUTH_ENABLED`. `SECRET_KEY` no está aquí. |
| `app/api/v1/endpoints/auth.py` | Endpoint login | JWT real vía `auth_service.crear_token`. Llama `usuario.username` — rompe con rename. Pendiente §6 paso 7. |
| `app/api/v1/endpoints/clientes.py` | Endpoints Cliente | Todos protegidos con `Depends(get_current_user)`. |
| `app/api/v1/endpoints/movimientos.py` | Endpoints Movimiento | Mismo patrón de protección. CRUD básico completo. |
| `app/api/v1/endpoints/pedidos.py` | Endpoints Pedido (viejo) | Modelo plano. Se reemplaza completo — §6 paso 4. |
| `app/api/v1/endpoints/pedidos_shein.py` | Endpoints Shein (viejo) | FK a `clientes` (incorrecto). Se reemplaza completo — §6 paso 4. |
| `app/schemas/pedido.py` | Schema Pedido (viejo) | Estructura plana con `opcion_*`. Referencia de qué NO repetir. |
| `app/schemas/pedido_shein.py` | Schema Shein (viejo) | Visto. Se reemplaza completo. |
| `app/services/pedido_service.py` | Lógica Pedido (viejo) | Modelo plano: `Pedido(producto=..., marca=..., talla=...)`. Sin nada reutilizable — se reemplaza completo. |
| `requirements.txt` | Dependencias | `python-jose` + `passlib`/`bcrypt` — JWT real. Sin `pytest`. Pendiente agregar `odfpy` para script de import. |
| `docs/00_FULLSTACK_DEVELOPMENT.md` | Spec UI/UX | Leída completa en sección Pedidos. Autoridad confirmada. **Pendiente que el usuario agregue sección `tabla_precios`** (ver §1). |
| `tabla_precios.ods` | Catálogo de precios por proveedor | 3 pestañas (`price_shoes`, `pakar`, `cklass`). Esquema documentado en §2a. Fuente de verdad operativa — se mantiene en `.ods`, se sincroniza a SQLite vía script manual. |

### 3.2 Mencionados pero NO vistos (huecos de visibilidad — pedir antes de tocar)

| Archivo | Por qué importa |
|---|---|
| `app/services/auth_service.py` | Contiene `autenticar_usuario`, `crear_token`, `get_current_user`. Probablemente aquí vive `SECRET_KEY` / expiración del JWT. Bloqueante para §6 paso 7. |
| `app/schemas/token.py` | Shape del `Token` de login. Visto en árbol, contenido no leído. |
| `app/services/pedido_shein_service.py` | Lógica Shein vieja — confirmar antes de reemplazar si tiene algo reutilizable. |
| `app/schemas/usuario.py` | Visto en árbol, contenido no leído. Relevante para §6 paso 7. |
| Endpoints/servicios de Inventario | No hay evidencia de que existan — `AUDITORIA.md` lo marcaba como 🔴. Pendiente §6 paso 8. |
| `backend/tests/*` | Contenido real no visto. Referenciado como "vacío". |
| `.env` / variables de entorno reales | No vistas. `config.py` solo define el default de `DATABASE_URL`. |

---

## 4. Correcciones detectadas a documentos ya entregados

**`docs/ARQUITECTURA.md`, sección 5 (Autenticación) — CORREGIDA ✅:**
`config.py` no tiene `AUTH_ENABLED`. `clientes.py` y `movimientos.py` protegen todos sus endpoints con `Depends(get_current_user)` — autenticación activa, no desactivada. Corregido con evidencia directa.

> Nota metodológica: no repetir afirmaciones sin evidencia directa, ni siquiera las propias.

---

## 5. Riesgos activos confirmados (bugs con evidencia, no inferencias)

1. **Sobrescritura de saldo en apartado** (`movimiento_service.py`) — `cliente.saldo = saldo_resultante` en vez de `+=`. Confirmado con cita de código.
2. **Sin mínimo de $100 en apartado** — no existe la validación en ningún punto del flujo. Confirmado.
3. **Estados de cliente obsoletos** (`"liquidado"`) en `cliente_service.py` y `movimiento_service.py` — el enum nuevo no lo incluye, falla en tiempo de ejecución al migrar.
4. **`init_db()` en `lifespan`** — `Base.metadata.create_all()` corre en cada arranque del servidor. No destruye tablas existentes, pero desincroniza silenciosamente el esquema de Alembic si alguna vez se modifica `models.py` sin generar migración. Se elimina al tocar `main.py`.

---

## 6. Ruta de trabajo (orden, no checklist de tareas individuales)

1. ✅ Cerrar huecos bloqueantes de `init_db.py` — riesgo documentado, se resuelve en paso 4 al tocar `main.py`.
2. ✅ Implementar `models.py` aprobado en el repo real.
3. ✅ Reset limpio de BD + migración inicial nueva (`a1b2c3d4e5f6_esquema_inicial.py`). 11 tablas en `pos.db`.
4. **EN CURSO** — Reescritura completa del módulo Pedidos:
   - Prerrequisito no desbloqueado: `tabla_precios` no está documentada en `00_FULLSTACK_DEVELOPMENT.md` ni en `REGLAS_NEGOCIO.md` todavía (pendiente del usuario).
   - Prerrequisito técnico: agregar `precios_catalogo` a `models.py` + migración Alembic + script `importar_precios.py`.
   - Una vez desbloqueado: `schemas/pedido.py` (nuevo), `services/pedido_service.py` (nuevo), `endpoints/pedidos.py` (nuevo). Cubre 4 flujos: Registrar Pedido, Registrar Devolución, Cancelar Artículo, Lista de Surtido.
   - Shein: `schemas/pedido_shein.py` (nuevo), `services/pedido_shein_service.py` (nuevo), `endpoints/pedidos_shein.py` (nuevo).
5. Ajuste de `schemas/cliente.py` y `services/cliente_service.py` (quitar `"liquidado"`, ajustar tipo `telefono`).
6. Ajuste de `schemas/movimiento.py` y `services/movimiento_service.py` (corregir suma de saldo, mínimo $100, `descripcion` en vez de `notas`).
7. Ajuste de `auth.py` + `auth_service.py` (rename `username`→`usuario`, `hashed_password`→`password_hash`). Requiere ver `auth_service.py` y `schemas/usuario.py` primero (§3.2).
8. Construcción desde cero de Inventario (schema + servicio + endpoint — no existe nada hoy).
9. Construcción desde cero de Recargas y Configuración.
10. Solo entonces: `CHECKLIST.md` real, con criterio de completado = pipeline + test.

---

## 7. Cómo usar este documento en una sesión nueva

Si retomas el trabajo y solo compartes `REPORT.md`, ya sé: qué está decidido y no se reabre (§2), qué evidencia tengo y de dónde salió (§3.1), qué no he visto todavía y debo pedir antes de asumir nada (§3.2), y qué riesgos de código ya están confirmados (§5).

No necesitas resubir los archivos de §3.1 — solo los que aparezcan en §3.2 cuando lleguemos a tocarlos, o cualquier archivo que haya cambiado desde la última actualización de este documento.

El próximo paso bloqueante antes de escribir código de pedidos: el usuario actualiza `00_FULLSTACK_DEVELOPMENT.md` y `REGLAS_NEGOCIO.md` con la sección de `tabla_precios`, luego Claude agrega `precios_catalogo` a `models.py` + migración + script de import.
