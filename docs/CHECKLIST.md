# CHECKLIST.md
## pos-boutique — Estado operativo y hoja de ruta

> Este documento es la fuente de verdad del estado actual del proyecto.
> No es un diagnóstico — es una lista de trabajo.
> Se actualiza con cada sesión. Cuando un ítem se completa, se marca ✅ y se anota la fecha.
> El objetivo de este documento es llegar a un punto donde el sistema funcione de extremo
> a extremo y pueda decirse: **"el MVP está listo para operar en producción."**

**Última actualización:** 20 de junio de 2026

---

## Tabla de contenidos

- [Fase 0 — Homologación](#fase-0--homologación-base-antes-de-construir)
- [Fase 1 — Backend funcional](#fase-1--backend-funcional)
- [Fase 2 — Frontend base](#fase-2--frontend-base)
- [Fase 3 — Integración y pruebas](#fase-3--integración-y-pruebas)
- [Fase 4 — Producción](#fase-4--producción)
- [Roadmap de versiones](#roadmap-de-versiones)
- [Infraestructura — sonia@envy](#infraestructura--soniaenvy)

---

## Fase 0 — Homologación (base antes de construir)

> Objetivo: que el código existente y la documentación sean consistentes entre sí
> antes de escribir lógica nueva. Sin esta fase, cualquier avance construye sobre arena.

### Documentación

- [x] `REGLAS_NEGOCIO.md` reescrito con tipos de datos SQLite, enums y reglas de nulabilidad *(20 jun)*
- [x] `README.md` actualizado — modelo de datos, checklist y typos corregidos *(20 jun)*
- [x] Semántica de `saldo` definida: positivo = deuda activa del cliente *(20 jun)*
- [x] Ciclo de vida del cliente documentado: `activo → liquidado → rehabilitar` *(20 jun)*
- [x] `forma_pago` documentada: `efectivo | transferencia | tarjeta` *(20 jun)*
- [x] `referencia` del cliente resuelta: 3 campos (`ref_nombre`, `ref_colonia`, `ref_telefono`) *(20 jun)*
- [x] `opcion` en Pedidos resuelta: 3 campos (`opcion_producto`, `opcion_marca`, `opcion_talla`) *(20 jun)*
- [x] `bono_aplicado` en Shein eliminado — sin regla de negocio *(20 jun)*
- [x] Sección systemd en `DEBUGGING.md` — cómo crear el servicio para producción

### Modelo ORM (`models.py`)

- [x] Migrar de `declarative_base()` a `class Base(DeclarativeBase)` (SQLAlchemy 2.0+)
- [x] `clientes` — reemplazar campo `referencia` por `ref_nombre`, `ref_colonia`, `ref_telefono`
- [x] `clientes` — agregar campo `estatus TEXT NOT NULL DEFAULT 'activo'`
- [x] `pedidos` — reemplazar campo `opcion` por `opcion_producto`, `opcion_marca`, `opcion_talla`
- [x] `pedidos` — agregar campo `id_producto_externo TEXT` (nullable)
- [x] `pedidos_shein` — eliminar campo `bono_aplicado`
- [x] `FormaPago` enum — agregar valor `tarjeta`
- [x] Inventario — agregar campos: `categoria`, `estilo`, `color`, `change_status`
- [x] Inventario — renombrar precio → `precio_venta`, `cantidad` → `stock`
- [x] Inventario — agregar `EstatusInventario` enum (disponible, vendido, disponible c/descuento, en_ruta)

### Infraestructura del backend

- [x] Inicializar Alembic (`alembic init`)
- [x] Generar y aplicar primera migración con los cambios del modelo ORM
- [ ] Migrar `@app.on_event("startup")` al patrón `lifespan` con context manager (FastAPI moderno)
- [ ] Crear `backend/.env` y `backend/.env.example`
- [ ] Sacar URL de la base de datos del hardcode → variable de entorno
- [ ] Crear `backend/app/core/config.py` con `Settings` (Pydantic BaseSettings)
- [ ] Configurar CORS middleware en `main.py` (origen: `http://localhost:5173`)
- [ ] Inicializar Alembic (`alembic init`)
- [ ] Generar y aplicar primera migración con los cambios del modelo ORM

**✋ Punto de verificación Fase 0**
El backend debe arrancar sin warnings, con el modelo ORM actualizado y Alembic inicializado.
`GET /` y `GET /ping` responden. `pos.db` refleja el esquema correcto.

---

## Fase 1 — Backend funcional

> Objetivo: la API REST completa para el MVP (v0.1).
> Al terminar esta fase, toda la lógica de negocio existe y es testeable desde `/docs`.

### Schemas Pydantic (`schemas/`)

- [ ] `ClienteCreate` — campos de entrada para registro de cliente
- [ ] `ClienteRead` — respuesta con todos los campos incluido `no_cliente` y `estatus`
- [ ] `MovimientoCreate` — entrada para las 4 operaciones del panel principal
- [ ] `MovimientoRead` — respuesta con `saldo_resultante` calculado
- [ ] `PedidoCreate` / `PedidoRead`
- [ ] `PedidoSheinCreate` / `PedidoSheinRead`

### Endpoints (`api/v1/endpoints/`)

- [ ] `POST /clientes` — registrar cliente (genera `no_cliente` automáticamente)
- [ ] `GET /clientes` — listar clientes (con filtro por nombre/colonia)
- [ ] `GET /clientes/{id}` — detalle de cliente con saldo y estatus
- [ ] `PATCH /clientes/{id}/rehabilitar` — cambiar estatus `liquidado → activo`
- [ ] `POST /movimientos` — registrar operación (contado, apartado, abono, gasto)
- [ ] `GET /movimientos` — historial filtrado por cliente
- [ ] `POST /pedidos` — registrar pedido de catálogo
- [ ] `GET /pedidos/{id_cliente}` — pedidos de un cliente
- [ ] `POST /pedidos-shein` — registrar pedido Shein
- [ ] `GET /pedidos-shein/{id_cliente}` — pedidos Shein de un cliente

### Servicios — lógica de negocio (`services/`)

- [ ] `generar_no_cliente(colonia)` — formato `{Colonia}-{consecutivo}`, autoincremental por colonia
- [ ] `registrar_movimiento()` — orquesta la operación: valida, calcula saldo, escribe en `movimientos` y actualiza `clientes.saldo` en una sola transacción
- [ ] `calcular_saldo_resultante()` — según tipo de operación (`apartado`: precio − pago; `abono`: saldo − monto)
- [ ] `evaluar_estatus_cliente()` — si `saldo = 0` tras un abono → `estatus = liquidado`
- [ ] `rehabilitar_cliente()` — `estatus = liquidado → activo`

### Tests (`tests/`)

- [ ] Test: registro de cliente genera `no_cliente` correcto
- [ ] Test: abono reduce `saldo` y actualiza `saldo_resultante`
- [ ] Test: abono que lleva `saldo` a 0 cambia `estatus` a `liquidado`
- [ ] Test: `POST /movimientos` rechaza `monto` negativo
- [ ] Test: `POST /movimientos` con `operacion = gasto` no requiere `id_cliente`

**✋ Punto de verificación Fase 1**
Desde `http://localhost:8000/docs` es posible ejecutar todas las operaciones del MVP
sin tocar el frontend. El flujo completo de un ciclo de cliente funciona:
registro → apartado → abono → liquidado → rehabilitado.

---

## Fase 2 — Frontend base

> Objetivo: interfaz operativa para las funciones del MVP (v0.1).
> Al terminar esta fase, la ejecutiva puede operar el sistema desde el navegador.

### Inicialización

- [ ] Ejecutar `npm create vite@latest` en `frontend/`
- [ ] Configurar proyecto: React + TypeScript
- [ ] Instalar dependencias base (React Router, cliente HTTP)
- [ ] Verificar que `npm run dev` levanta en `http://localhost:5173`
- [ ] Configurar proxy hacia `http://localhost:8000` en `vite.config.ts`

### Estructura y navegación

- [ ] Layout base: header + navegación principal
- [ ] Rutas: Panel Principal / Agregar Cliente / Consulta / Pedidos / Shein

### Panel Principal

- [ ] Selector de operación (Contado / Apartado / Abono / Gasto)
- [ ] Formulario dinámico según operación seleccionada
- [ ] Selector de cliente (búsqueda por nombre)
- [ ] Selector de origen de producto (catálogo informal / Piso de Venta — PdV deshabilitado en v0.1)
- [ ] Modal de Apartado (primer pago, saldo pendiente, historial)
- [ ] Confirmación y feedback de operación registrada

### Agregar Cliente

- [ ] Formulario con campos definidos en REGLAS_NEGOCIO
- [ ] `no_cliente` generado por el backend — mostrarlo tras el registro
- [ ] Validaciones en frontend (campos obligatorios)

### Consulta

- [ ] Búsqueda de cliente por nombre o `no_cliente`
- [ ] Vista de detalle: datos del cliente, saldo actual, estatus
- [ ] Historial de movimientos (tabla ordenada por fecha)
- [ ] Botón de rehabilitación si `estatus = liquidado`

### Pedidos y Shein

- [ ] Formulario de pedido de catálogo (con campos de opción alternativa)
- [ ] Formulario Shein (cliente + producto + monto)

**✋ Punto de verificación Fase 2**
La ejecutiva puede completar un ciclo completo desde el navegador sin tocar
la terminal ni la base de datos directamente.

---

## Fase 3 — Integración y pruebas

> Objetivo: el sistema funciona de extremo a extremo en la máquina de desarrollo
> antes de tocarse `sonia@envy`.

- [ ] Prueba de flujo completo: registro de cliente → apartado → abono → liquidado → rehabilitado
- [ ] Prueba de flujo Shein: registro → concretación → ingreso en caja
- [ ] Prueba de Gasto: sin cliente, refleja en historial de caja
- [ ] Verificar que `pos.db` puede copiarse, restaurarse y el sistema sigue operando
- [ ] Script `scripts/start.sh` — levanta backend y frontend con un solo comando
- [ ] Script `scripts/backup.sh` — copia `pos.db` con timestamp

**✋ Punto de verificación Fase 3**
El sistema corre completo en `gabriel@actuary`. Se puede hacer un backup y restaurarlo.
Es el momento de pensar en `sonia@envy`.

---

## Fase 4 — Producción

> Objetivo: el sistema corre de forma estable y autónoma en `sonia@envy`.

### Preparación de `sonia@envy`

- [ ] Verificar Python 3.11+, Node.js 20+, Git instalados
- [ ] Confirmar repo clonado y sincronizado con `main`
- [ ] Ejecutar `pip install -r requirements.txt` en el entorno de producción
- [ ] Ejecutar `npm install` y `npm run build` en frontend
- [ ] Aplicar migraciones: `alembic upgrade head`
- [ ] Verificar que `pos.db` existe y tiene el esquema correcto

### Servicio systemd

> Este es el momento en que `sonia@envy` se convierte en servidor.
> Antes de esta fase, no tiene sentido montar infraestructura.

- [ ] Crear unit file `pos-boutique-backend.service` para Uvicorn
- [ ] Crear unit file `pos-boutique-frontend.service` para el build de Vite (o servir estático con Nginx/Caddy)
- [ ] Habilitar servicios: `systemctl enable pos-boutique-*`
- [ ] Documentar el proceso en `DEBUGGING.md`
- [ ] Verificar arranque automático tras reinicio de la máquina

### Operación

- [ ] Confirmar acceso vía `ssh/tailscale` desde `gabriel@actuary`
- [ ] Primera sesión de uso real con la ejecutiva
- [ ] Ajustes post-primera-sesión

**✋ Punto de verificación Fase 4 = MVP en producción**
La ejecutiva puede usar el sistema en la tienda sin intervención del desarrollador.
`sonia@envy` arranca sola. Los datos persisten. El backup funciona.

---

## Correspondencia con roadmap.png

El roadmap visual del proyecto numera los pasos de desarrollo. Esta tabla
los mapea a las fases de este checklist para que ambos documentos sean navegables juntos.

| Paso | Descripción | Estado | Fase |
|------|-------------|--------|------|
| 1 | Definición del producto (reglas de negocio, módulos, modelo de datos) | ✅ Completado | — |
| 2 | Stack tecnológico (React + Vite / FastAPI / SQLite) | ✅ Completado | — |
| 3 | Repositorio GitHub (pos-boutique) | ✅ Completado | — |
| 4 | Estructura de carpetas del proyecto | ✅ Completado | — |
| 5 | README.md | ✅ Completado | — |
| 6 | venv backend + .gitignore | ✅ Completado | — |
| 7 | requirements.txt (dependencias backend) | ✅ Completado | v0.1 MVP |
| 8 | Esquema inicial de base de datos (SQLite) | ✅ Completado | v0.1 MVP |
| 9 | API REST base (FastAPI) | ✅ Completado (mínima — 2 endpoints de salud) | v0.1 MVP |
| **10** | **Modelos ORM + migraciones (SQLAlchemy + Alembic)** | 🔄 **En curso — Fase 0** | v0.1 MVP |
| 11 | Panel Principal — operaciones | ⏳ Pendiente | v0.1 MVP — Fases 1 y 2 |
| 12 | Módulo Clientes | ⏳ Pendiente | v0.1 MVP — Fases 1 y 2 |
| 13 | Módulo Consulta | ⏳ Pendiente | v0.1 MVP — Fases 1 y 2 |
| 14 | Módulo Piso de Venta | ⏳ Pendiente | v0.2 |
| 15 | Módulo Pedidos | ⏳ Pendiente | v0.2 |
| 16 | Módulo Shein | ⏳ Pendiente | v0.2 |
| 17 | Despliegue en PC ejecutiva | ⏳ Pendiente | Fase 4 |

> El paso 10 fue el hueco identificado en el roadmap original (la numeración saltaba de 9 a 11).
> Confirmado como: **Modelos ORM actualizados (SQLAlchemy 2.0) + Alembic inicializado con primera migración.**
> Es el puente entre el esquema de base de datos (paso 8) y la API REST funcional (paso 11 en adelante).

---

## Roadmap de versiones

| Versión | Alcance | Fase de este checklist | Estado |
|---------|---------|----------------------|--------|
| **v0.1** | MVP: clientes, panel de operaciones (contado/apartado/abono/gasto), consulta, pedidos, Shein | Fases 0–4 | 🔄 En curso |
| **v0.2** | Piso de Venta: integración inventario (spreadsheet → `inventario` DB) | Por definir | ⏳ Pendiente |
| **v0.3** | Devoluciones, préstamos de exhibición, operaciones especiales | Por definir | ⏳ Pendiente |
| **v0.4** | Calendario de pagos por cliente — frecuencia esperada de abonos, alertas de vencimiento | Por definir | ⏳ Pendiente |
| **v1.0** | Sistema estable, probado en operación real, con historial suficiente para validar el modelo | Por definir | ⏳ Pendiente |

> **v0.4 — Calendario de pagos:** la base de datos ya tiene todo lo necesario (`clientes.saldo` +
> historial en `movimientos`). La funcionalidad consiste en definir una frecuencia de pago
> esperada por cliente y generar alertas cuando un cliente activo no ha abonado en el período
> acordado. Se incorpora después de que el ciclo base (v0.1) esté probado en operación real.

---

## Infraestructura — sonia@envy

| Ítem | Estado | Notas |
|------|--------|-------|
| Acceso SSH / Tailscale | ✅ Permanente | Acceso desde `gabriel@actuary` confirmado |
| Repo clonado | ✅ | Sincronizado hasta últimos push — sin conflictos |
| Python 3.11+ | ❓ | Por verificar |
| Node.js 20+ | ❓ | Por verificar |
| Servicio systemd | ⏳ | No es el momento — ver Fase 4 |
| Rol de servidor activo | ⏳ | Se activa al completar Fase 3 en `gabriel@actuary` |

> `sonia@envy` no necesita ser un servidor hasta que el sistema esté validado localmente.
> El detonador para montar infraestructura es completar el ✋ de Fase 3.
