# Auditoría de Estado Real del Proyecto — pos-boutique

| | |
|---|---|
| **Fecha** | 2026-06-28 |
| **Fuente de verdad** | `docs/00_FULLSTACK_DEVELOPMENT.md` (tiene precedencia sobre `README.md`, `ARQUITECTURA.md` y `REGLAS_NEGOCIO.md`) |
| **Alcance** | Backend (`app/`, `alembic/`, `tests/`), Frontend (`src/`), consistencia documental |
| **Método** | Verificación directa de código fuente, sin inferencia por nombre de archivo |

---

## 1. Resumen ejecutivo

El proyecto tiene una **base funcional construida sobre un diseño obsoleto**. La documentación se actualizó para reflejar el alcance real del MVP (spec maestra), pero el código —backend y frontend— corresponde a una versión anterior, más simple, del sistema. No es que falte trabajo: es que una parte del trabajo ya hecho está construido sobre un modelo de datos que la spec maestra reemplazó.

| Métrica | Valor |
|---|---|
| Cobertura funcional real vs. spec maestra | **~10 %** |
| Cobertura de pruebas automatizadas | **0 %** |
| Tablas requeridas ya creadas y alineadas | 2 de 11 (`usuarios`, `movimientos` parcial) |
| Tablas requeridas ausentes | 6 (`pedidos_articulos`, `shein_clientes`, `shein_pedidos`, `shein_cortes`, `recargas`, `configuracion`) |
| Endpoints alineados a la spec maestra | 0 de ~23 (todos requieren ajuste o reconstrucción) |
| Avance de frontend | 0 % (directorio sin inicializar) |
| Documentos derivados consistentes con la spec maestra | 0 de 3 (`README.md`, `ARQUITECTURA.md`, `REGLAS_NEGOCIO.md`) |

**Causa raíz:** el backend se desarrolló contra `REGLAS_NEGOCIO.md` en su versión anterior —un modelo de pedidos plano, sin separación Shein, sin inventario activo en MVP—. Cuando la spec maestra introdujo el modelo cabecera-detalle, la separación de clientes Shein, el sistema de banderas de cobranza y el módulo de configuración de pagos, el código no se ajustó. El resultado es un backend funcional pero **desalineado**, no un backend incompleto en el sentido simple.

**Lo que sí está bien:** la arquitectura técnica de base (FastAPI + SQLAlchemy + Alembic + SQLite, autenticación JWT con bcrypt) es compatible con la spec maestra. No se requiere reescribir el stack, solo el esquema de datos y la lógica de negocio sobre él.

---

## 2. Consistencia documental: README / ARQUITECTURA / REGLAS_NEGOCIO vs. spec maestra

Ningún documento derivado es hoy confiable como referencia de trabajo. Se detallan las discrepancias por documento.

### 2.1 README.md

| Afirmación del documento | Veredicto | Detalle |
|---|---|---|
| El modelo de datos consta de 11 tablas con campos y relaciones descritas | 🟡 Parcial | Nombres de tabla en su mayoría correctos, pero tipos y nulabilidad equivocados (ej. `ref_telefono` como `TEXT` en vez de `INTEGER`; `frecuencia_pago` marcado como nullable cuando es obligatorio) |
| El frontend tiene layouts, componentes, hooks, store y services ya definidos | 🔴 Falso | El directorio `frontend/src/` está vacío. No existe ese código |
| Pydantic schemas, configuración centralizada, CORS y Alembic están "completados" (✅) | 🔴 Obsoleto | Lo que existe está construido contra el esquema viejo, no contra la spec maestra. Marcarlo como completado es engañoso |

### 2.2 ARQUITECTURA.md

| Afirmación del documento | Veredicto | Detalle |
|---|---|---|
| El sistema tiene 11 tablas con relaciones multi-empresa (`Empresa 1→N Sucursal`, `Empresa 1→N Usuario`) y roles corporativos (`GERENTE`, `CAJERO`) | 🔴 Contradicción radical | La spec maestra es para un **negocio local de una sola operadora**. No hay concepto de empresas, sucursales ni roles corporativos en ningún punto de `00_FULLSTACK_DEVELOPMENT.md` |
| SQLite se accede de forma asíncrona vía `aiosqlite` | 🔴 Falso | El código en `backend/app/db/database.py` usa SQLAlchemy síncrono |

### 2.3 REGLAS_NEGOCIO.md

| Afirmación del documento | Veredicto | Detalle |
|---|---|---|
| `pedidos` es una tabla plana (un producto por fila, con columnas opcionales) | 🔴 Obsoleto | La spec maestra exige cabecera-detalle: `pedidos` + `pedidos_articulos`, con 1 a 4 artículos por pedido y roles `principal`/`alternativa` |
| El módulo Shein vincula sus pedidos al cliente general de la boutique | 🔴 Obsoleto | La spec maestra exige `shein_clientes` independiente, para no mezclar crédito de boutique con contado de Shein |
| Estatus de cliente: `activo`, `liquidado`, `rehabilitar` | 🔴 Obsoleto | La spec maestra simplifica a `activo`/`inactivo`, y aclara explícitamente que `saldo = 0` no implica baja automática |
| El módulo de Inventario se difiere a v0.2, fuera del MVP | 🔴 Contradicción | La spec maestra incluye Inventario como módulo obligatorio del MVP, con enum de estatus y regla de `precio_descuento` |
| Tabla de avance: Pydantic schemas, servicios, CORS y Alembic "pendientes" (🔲) | ⚠️ Contradice a README.md | README.md afirma que esos mismos elementos ya están completos. Los documentos se contradicen entre sí, no solo contra la spec maestra |

**Conclusión de la sección 2:** los tres documentos no solo están desfasados respecto a la spec maestra — están desfasados **entre sí**. Cualquiera de los tres que se use como referencia hoy lleva a una implementación distinta. Deben reescribirse, no parchearse.

---

## 3. Cobertura por entidad (modelo de datos)

Pipeline de verificación por tabla: **Modelo → Migración → Schema → Endpoint → Test**. Una tabla solo es ✅ si completa los cinco eslabones con evidencia.

| Entidad | En spec | Modelo | Migración | Schema | Endpoint | Test | Estado |
|---|---|---|---|---|---|---|---|
| `clientes` | ✅ | ✅ `models.py:28` | ✅ `38241ae2061c…py` | ✅ `cliente.py:4` | ✅ `clientes.py:11` | ❌ | 🟡 Parcial — faltan `frecuencia_pago` y `fecha_pago_programada` en modelo, BD y schemas |
| `pedidos` (cabecera) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 No implementado — estructura real en BD es plana/obsoleta |
| `pedidos_articulos` (líneas) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 No implementado |
| `inventario` | ✅ | ✅ `models.py:48` | ✅ `38241ae2061c…py` | ❌ | ❌ | ❌ | 🔴 No implementado — modelo desalineado, sin lógica ni endpoints |
| `movimientos` | ✅ | ✅ `models.py:97` | ✅ `38241ae2061c…py` | ✅ `movimiento.py:8` | ✅ `movimientos.py:11` | ❌ | 🟡 Parcial — usa columna `notas` en vez de `descripcion`, sin tests |
| `shein_clientes` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 No implementado |
| `shein_pedidos` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 No implementado — `PedidoShein` en `models.py:85` es obsoleto, apunta a clientes generales |
| `shein_cortes` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 No implementado |
| `recargas` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 No implementado |
| `usuarios` | ✅ | ✅ `models.py:114` | ✅ `97592862ac88…py` | ✅ `usuario.py:14` | 🟡 Parcial (solo login) | ❌ | 🟡 Parcial — faltan endpoints CRUD |
| `configuracion` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 No implementado |

**Lectura rápida:** 2 de 11 tablas tienen pipeline parcial; 0 están completas; 6 no existen en absoluto.

---

## 4. Cobertura por endpoint / caso de uso

| Módulo | Endpoint / caso de uso | Implementado | Cumple regla de negocio | Estado |
|---|---|---|---|---|
| Clientes | Registrar Cliente | ✅ `clientes.py:11` | 🟡 genera `no_cliente` pero no guarda `frecuencia_pago`/`fecha_pago_programada` | 🟡 |
| Clientes | Editar Cliente | ❌ | ❌ | 🔴 |
| Clientes | Consulta Cliente | ✅ `clientes.py:22` | ✅ | 🟡 (sin test) |
| Clientes | Consulta Historial | ❌ | ❌ | 🔴 no existe vista consolidada cronológica |
| Pedidos | Registrar Pedido (1–4 artículos) | ❌ | ❌ `pedidos.py:11` es plano, sin principal/alternativa ni estatus `vigente` | 🔴 |
| Pedidos | Registrar Devolución | ❌ | ❌ | 🔴 |
| Pedidos | Cancelar Artículo | ❌ | ❌ | 🔴 |
| Pedidos | Lista de Surtido | ❌ | ❌ | 🔴 |
| Inventario | Agregar Producto | ❌ | ❌ | 🔴 |
| Inventario | Cambiar Estatus | ❌ | ❌ | 🔴 |
| Inventario | Consulta Inventario | ❌ | ❌ | 🔴 |
| Panel Principal | Contado — Catálogo | ✅ `movimientos.py:11` | ✅ vía `movimiento_service.py:7` | 🟡 (sin test) |
| Panel Principal | Contado — Inventario | ❌ | ❌ no descuenta stock ni actualiza estatus | 🔴 |
| Panel Principal | Apartado | 🟡 | ❌ sobrescribe saldo en vez de sumarlo (`movimiento_service.py:28`); no valida mínimo $100; no toca `inventario` | 🔴 |
| Panel Principal | Abono | 🟡 | ❌ usa estado obsoleto `"liquidado"`; no recalcula `fecha_pago_programada` | 🟡 |
| Panel Principal | Gasto | 🟡 | 🟡 descripción no obligatoria; columna `notas` en vez de `descripcion` | 🟡 |
| Shein | Registrar Cliente Shein | ❌ | ❌ | 🔴 |
| Shein | Registrar Pedido Shein | ❌ | ❌ `pedidos_shein.py:11` usa cliente general | 🔴 |
| Shein | Lista de Pedidos / Registrar Corte | ❌ | ❌ | 🔴 |
| Recargas | Registro / Consulta de totales | ❌ | ❌ | 🔴 |
| Consultas globales | Ventas por período / segmento / cartera | ❌ | ❌ | 🔴 |
| Autenticación | Login | ✅ `auth.py:11` | ✅ | 🟡 (sin test) |
| Autenticación | Me / Configurar métodos de pago | ❌ | ❌ | 🔴 |

**Total: 23 endpoints esperados → 4 con código parcial, 0 completos, 19 ausentes.**

---

## 5. Reglas de negocio críticas — verificación puntual

Solo se listan las reglas con mayor impacto en integridad de datos (saldo, ciclo de cobranza, inventario):

| Regla | Implementada | Evidencia | Estado |
|---|---|---|---|
| Generación de `no_cliente` | 🟡 | `cliente_service.py:7` | Riesgo de colisión: usa `COUNT` por colonia, se rompe si se elimina un cliente |
| Ciclo de `fecha_pago_programada` (rodante por abono) | ❌ | Falta la columna en el modelo `Cliente` | 🔴 |
| Sistema de banderas 🔴/🟡 de cobranza | ❌ | No existe | 🔴 |
| Carga de saldo al marcar `en_almacen` (no al crear el pedido) | ❌ | El saldo se carga erróneamente al crear el pedido/apartado | 🔴 — **riesgo financiero**: se cobra por artículos que aún no llegan |
| Pago mínimo $100 en apartado | ❌ | Sin validación en `movimiento_service.py:28` | 🔴 |
| Validación abono ≤ saldo | ✅ | `movimiento_service.py:40` | 🟡 (sin test) |
| Solo se puede cancelar el último movimiento | ✅ | `movimiento_service.py:90` | 🟡 (sin test) |
| Lookup de precios (Price_Shoes / Pakar / Cklass) | ❌ | No existe | 🔴 |
| Clientes Shein independientes de clientes generales | ❌ | Se asocian a la tabla de clientes general | 🔴 — **riesgo de integridad**: mezcla crédito con contado |
| Script `importar_clientes.py` | ❌ | No existe en `scripts/` | 🔴 |

---

## 6. Frontend

**Estado: 0 % — directorio `frontend/src/` sin inicializar.** Ninguna de las ~20 pantallas de la spec maestra (Clientes, Pedidos, Inventario, Panel Principal, Shein, Recargas, Consultas Globales, Login, Configuración) tiene código. No hay distinción entre "falta pulir" y "falta construir": no existe.

---

## 7. Backlog priorizado de brechas

Clasificación: **P0** bloquea todo lo demás · **P1** bloquea un módulo · **P2** se puede diferir sin romper el MVP.

### P0 — Fundacional (bloquea todo el resto del backend)
1. Migración Alembic que reestructure `pedidos` → `pedidos` + `pedidos_articulos` (cabecera-detalle).
2. Agregar `frecuencia_pago` y `fecha_pago_programada` a `clientes`.
3. Corregir la regla de carga de saldo: mover de "al crear pedido" a "al marcar `en_almacen`" — es un riesgo financiero activo, no solo una brecha funcional.
4. Crear `shein_clientes` y desacoplar `shein_pedidos` de la tabla de clientes general.

### P1 — Por módulo
5. Implementar ciclo de `fecha_pago_programada` y sistema de banderas de cobranza.
6. Validar pago mínimo de $100 en apartados; eliminar el estado obsoleto `"liquidado"`.
7. Construir servicio de Pedidos completo: registro multi-artículo, devolución, cancelación, lista de surtido.
8. Construir módulo Inventario: schemas, endpoints, transición de estatus, regla de `precio_descuento`.
9. Crear tablas `shein_cortes`, `recargas`, `configuracion` con sus endpoints.
10. CRUD completo de `usuarios` (hoy solo existe login).

### P2 — Se puede diferir sin bloquear el MVP funcional
11. Consultas globales (ventas por período, por segmento, cartera por colonia).
12. Script `scripts/importar_clientes.py` para carga inicial de cartera.
13. Suite de pruebas automatizadas en `backend/tests/` (actualmente vacío) — **idealmente esto debería subir de prioridad en cuanto el esquema de datos se estabilice**, para evitar reconstruir tests cada vez que cambie el modelo.
14. Inicialización completa del frontend (Vite + React + TypeScript) y construcción de las ~20 pantallas.

---

## 8. Documentos a reconciliar (orden recomendado)

| Orden | Documento | Acción requerida |
|---|---|---|
| 1 | `REGLAS_NEGOCIO.md` | Reescritura total: esquema cabecera-detalle, estatus `activo/inactivo`, separación Shein, Inventario dentro del MVP, regla de saldo diferido, pago mínimo $100 |
| 2 | `ARQUITECTURA.md` | Eliminar por completo el alcance multi-empresa/multi-sucursal (`empresas`, `sucursales`, `impuestos`); corregir descripción de acceso a SQLite (síncrono, no `aiosqlite`) |
| 3 | `README.md` | Actualizar checklist de progreso técnico para que refleje el estado real (no "completado" donde solo existe código obsoleto); eliminar árbol de frontend inexistente |
| 4 | `CHECKLIST.md` | Reconstruir desde cero usando la sección 7 de este documento como insumo directo |
| 5 | `AVANCE_VALIDACION.md` | No tiene sentido reconstruirlo todavía — depende de que `CHECKLIST.md` tenga avance real que validar |

---

## 9. Próximo paso recomendado

Con esta auditoría como insumo, el siguiente entregable lógico es **`CHECKLIST.md`**, derivado directamente de la sección 7 (backlog priorizado), convertido en tareas verificables con criterio de "completado" = pipeline completo + test pasando. No se recomienda tocar `AVANCE_VALIDACION.md` hasta que el checklist tenga avance real que registrar.
