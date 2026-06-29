# REPORT — Mapa de Estado del Proyecto (pos-boutique)

> **Qué es este documento:** una fotografía acumulativa de decisiones tomadas,
> evidencia confirmada y huecos de visibilidad. No es un checklist de tareas
> (eso es `CHECKLIST.md`, aún no construido) ni la spec de negocio (eso es
> `REGLAS_NEGOCIO.md` / `00_FULLSTACK_DEVELOPMENT.md`). Es el documento que
> permite retomar el trabajo en cualquier sesión nueva sin tener que re-subir
> todo el repo. **Se actualiza cada vez que se revisa código nuevo o se toma
> una decisión.** Última actualización: tras revisión de `main.py`, `database.py`,
> `config.py`, `auth.py`, `clientes.py`, `movimientos.py`, `pedidos.py`,
> `pedidos_shein.py`, `pedido.py`, `requirements.txt`.

---

## 1. Jerarquía de fuentes (no reabrir sin razón explícita)

1. **`docs/00_FULLSTACK_DEVELOPMENT.md`** — spec de UI/UX, autoridad máxima si hay contradicción.
2. **`docs/REGLAS_NEGOCIO.md`** — modelo de datos + reglas de negocio, derivado de (1).
3. **`docs/ARQUITECTURA.md`** — decisiones técnicas, derivado de evidencia de código real. **Tiene una sección incorrecta — ver §4.**
4. **`docs/README.md`** — orientación y arranque.
5. **`docs/AUDITORIA.md`** — fotografía de brechas a una fecha dada (2026-06-28). Se vuelve obsoleta más rápido que los demás; no tratarla como verdad permanente, sino como snapshot.
6. **`backend/app/models.py` (propuesto)** — entregado en esta sesión, alineado a (2). **Aprobado por el usuario, pendiente de implementación real en el repo.**

---

## 2. Decisiones ya cerradas (no volver a discutir salvo nueva evidencia)

| Decisión | Resultado |
|---|---|
| ¿Se conserva data de `pos.db`? | **No.** Es solo data de prueba. Camino de migración = **reset limpio** (Camino B): borrar `pos.db` y el historial de Alembic, generar migración inicial nueva desde `models.py` aprobado. |
| ¿Multi-empresa / multi-sucursal? | **No existe ni se planea.** Negocio único, una operadora. |
| ¿Async o sync en SQLAlchemy? | **Síncrono**, confirmado en `database.py` (`create_engine` estándar, sin `aiosqlite`). |
| ¿`telefono`/`ref_telefono` tipo de dato? | `Integer` (10 dígitos), no `String`. Confirmado en `models.py` propuesto — pendiente de implementar, rompe `cliente.py` (schema) actual que usa `str`. |
| ¿Nombres de campo en `Usuario`? | `usuario` (no `username`) y `password_hash` (no `hashed_password`) — alineado a la spec maestra. **Rompe `auth.py` actual**, que llama `usuario.username` y `usuario.rol`. |
| ¿`pedidos` plano o cabecera-detalle? | **Cabecera-detalle** (`pedidos` + `pedidos_articulos`), 1 a 4 artículos. El `pedidos.py`/`pedido.py` actuales son el modelo viejo (plano) y se reemplazan, no se parchean. |
| ¿Shein comparte tabla de clientes? | **No.** `shein_clientes` independiente. `pedidos_shein.py` actual (FK a `clientes`) se reemplaza. |
| Estructura de documentación | `00_FULLSTACK_DEVELOPMENT.md` se mantiene como spec de UI. `README.md` / `ARQUITECTURA.md` / `REGLAS_NEGOCIO.md` ya reescritos con propósito formal separado (ver §1). |

---

## 3. Mapa de archivos — qué se ha visto, qué no, qué no existe

### 3.1 Confirmados con evidencia directa (leídos en esta sesión)

| Archivo | Rol | Hallazgo clave |
|---|---|---|
| `app/models/models.py` (original) | Modelo de datos viejo | Base del diagnóstico en `AUDITORIA.md` §3 |
| `alembic/versions/38241ae2061c_*.py` | Migración inicial | Crea esquema viejo completo |
| `alembic/versions/97592862ac88_*.py` | Migración usuarios | Agrega tabla `usuarios` (esquema viejo) |
| `app/schemas/cliente.py` | Schema Cliente | `telefono: str` — rompe con el nuevo `Integer` |
| `app/schemas/movimiento.py` | Schema Movimiento | Usa `notas`, no `descripcion`; sin validación de "obligatoria solo en gasto" |
| `app/services/cliente_service.py` | Lógica Cliente | Usa `estatus == "liquidado"` (no existe en nuevo enum); patrón de servicio es reutilizable |
| `app/services/movimiento_service.py` | Lógica Movimiento | **Bug crítico confirmado:** en `apartado`, `cliente.saldo = saldo_resultante` (sobrescribe, no suma). Sin validación de mínimo $100. Usa `"liquidado"` igual que arriba |
| `app/main.py` | Bootstrap FastAPI | Llama `init_db()` en `lifespan` (¿`create_all`? — ver §4, archivo no visto). Registra 5 routers. CORS solo a `localhost:5173` |
| `app/db/database.py` | Conexión BD | SQLAlchemy síncrono confirmado. `get_db()` estándar |
| `app/core/config.py` | Configuración | **Solo tiene `DATABASE_URL`.** No existe `AUTH_ENABLED`, `SECRET_KEY` no está aquí (probablemente en `auth_service.py`, no visto) |
| `app/api/v1/endpoints/auth.py` | Endpoint login | JWT real (no stub) vía `auth_service.crear_token`. Llama `usuario.username` — **se rompe con el rename a `usuario`** |
| `app/api/v1/endpoints/clientes.py` | Endpoints Cliente | Todos protegidos con `Depends(get_current_user)` — **ver corrección en §4** |
| `app/api/v1/endpoints/movimientos.py` | Endpoints Movimiento | Mismo patrón de protección. CRUD básico completo (crear, historial, cancelar) |
| `app/api/v1/endpoints/pedidos.py` | Endpoints Pedido (viejo) | Se reemplaza completo por el modelo cabecera-detalle |
| `app/api/v1/endpoints/pedidos_shein.py` | Endpoints Shein (viejo) | Se reemplaza completo por `shein_clientes`/`shein_pedidos` |
| `app/schemas/pedido.py` | Schema Pedido (viejo) | Confirma estructura plana con `opcion_producto/marca/talla`. Útil solo como referencia de qué NO repetir |
| `requirements.txt` | Dependencias | `python-jose` + `passlib`/`bcrypt` confirman JWT real, no mockeado. Sin `pytest` listado — consistente con "tests vacíos" de `AUDITORIA.md` |

### 3.2 Mencionados pero NO vistos (huecos de visibilidad — pedir antes de tocar)

| Archivo | Por qué importa |
|---|---|
| `app/db/init_db.py` | `main.py` lo llama en `lifespan`. Si hace `Base.metadata.create_all()`, puede estar creando tablas **por fuera de Alembic**, lo cual complica el reset limpio (§2) — hay que verificarlo antes de migrar |
| `app/services/auth_service.py` | Contiene `autenticar_usuario`, `crear_token`, `get_current_user`. Probablemente aquí vive `SECRET_KEY` / expiración del JWT |
| `app/schemas/token.py` | Shape del `Token` de login |
| `app/services/pedido_service.py` | Lógica del pedido viejo — confirmar antes de borrar si tiene algo reutilizable (ej. validaciones) |
| `app/services/pedido_shein_service.py` | Idem para Shein |
| `app/schemas/pedido_shein.py` | Shape del pedido Shein viejo |
| `app/schemas/inventario.py` | **No existe.** Confirmado por el usuario. Inventario no tiene capa de schemas en absoluto |
| Endpoints/servicios de Inventario | No hay evidencia de que existan en absoluto — `AUDITORIA.md` ya lo marcaba como 🔴 |
| `backend/tests/*` | Contenido real no visto, solo referenciado como "vacío" en `AUDITORIA.md` |
| `.env` / variables de entorno reales | No vistas — `config.py` solo define el default |

---

## 4. Correcciones detectadas a documentos ya entregados

**`docs/ARQUITECTURA.md`, sección 5 (Autenticación) — CORREGIDA (✅ aplicada en esta sesión):**

Yo había escrito que el login "está construido pero desactivado mediante `AUTH_ENABLED`". Eso era una suposición sin verificar. La evidencia real lo contradijo:

- `config.py` **no tiene** ningún flag `AUTH_ENABLED`.
- `clientes.py` y `movimientos.py` protegen **todos** sus endpoints con `Depends(get_current_user)` — la autenticación está **activa**, no desactivada.

`ARQUITECTURA.md` §5 ya quedó corregida: autenticación activa vía JWT real (`python-jose`), sin flag de desactivación, con `auth_service.py` aún pendiente de revisión directa (§3.2).

> Nota metodológica para mí mismo en futuras sesiones: esto es exactamente el tipo de error que esta auditoría existe para prevenir — no repetir afirmaciones sin evidencia directa, ni siquiera las mías.

---

## 5. Riesgos activos confirmados (no son brechas, son bugs con evidencia)

1. **Sobrescritura de saldo en apartado** (`movimiento_service.py`) — confirmado con cita de código, no inferido.
2. **Sin mínimo de $100 en apartado** — confirmado, no existe la validación en ningún punto del flujo.
3. **Estados de cliente obsoletos en uso activo** (`"liquidado"`) en dos archivos de servicio — al migrar el enum, ambos archivos fallan en tiempo de ejecución, no solo en lógica.
4. **Posible doble creación de esquema** (`init_db()` + Alembic) — no confirmado, requiere ver `init_db.py` antes del reset limpio para no pisar el plan de migración.

---

## 6. Ruta de trabajo (orden, no checklist de tareas individuales)

1. Cerrar huecos de visibilidad de §3.2 — en particular `init_db.py` y `auth_service.py`, son bloqueantes para decidir cómo se hace el reset limpio sin sorpresas.
2. ~~Corregir `ARQUITECTURA.md` §5 (ver §4).~~ ✅ Hecho.
3. Implementar `models.py` aprobado en el repo real.
4. Reset limpio de BD + migración inicial nueva (Camino B, ya decidido).
5. Reescritura completa de: `pedidos.py`+`pedido.py`+`pedido_service.py` (cabecera-detalle), `pedidos_shein.py`+`pedido_shein.py`+`pedido_shein_service.py` (Shein independiente).
6. Ajuste de `cliente.py` (schema) y `cliente_service.py` (quitar `"liquidado"`, ajustar tipo `telefono`).
7. Ajuste de `movimiento.py` (schema) y `movimiento_service.py` (corregir suma de saldo, mínimo $100, `descripcion` en vez de `notas`).
8. Ajuste de `auth.py` + `auth_service.py` (rename `username`→`usuario`, `hashed_password`→`password_hash`).
9. Construcción desde cero de Inventario (schema + servicio + endpoint — no existe nada hoy).
10. Construcción desde cero de Recargas y Configuración.
11. Solo entonces: `CHECKLIST.md` real, derivado de esta ruta, con criterio de completado = pipeline + test.

---

## 7. Cómo usar este documento en una sesión nueva

Si retomas el trabajo y solo compartes `REPORT.md`, ya sé: qué está decidido y no se reabre (§2), qué evidencia tengo y de dónde salió (§3.1), qué no he visto todavía y debo pedir antes de asumir nada (§3.2), y qué riesgos de código ya están confirmados (§5). No necesitas resubir los archivos de §3.1 — solo los que aparezcan en §3.2 cuando lleguemos a tocarlos, o cualquier archivo que haya cambiado desde la última actualización de este documento.
