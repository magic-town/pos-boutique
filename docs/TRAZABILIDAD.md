# TRAZABILIDAD — Referencia Técnica de pos-boutique

> **Para quién es:** para el responsable del desarrollo y mantenimiento del producto. 
> Una combinación entre Product Owner y Team Lider.
> Asume que entiendes lógica y estructuras de datos, pero explica la jerga
> técnica la primera vez que aparece. Cada afirmación cita el archivo del que
> fue tomada. Si algo está pendiente de implementar, se marca explícitamente
> como **PENDIENTE**.
>
> **Última generación:** 2026-06-29, basada en el estado del código real del repo.
> No modifica ni propone cambios a ningún archivo existente.

---

## Tabla de contenidos

- [1. Cómo está construido, en general](#1-cómo-está-construido-en-general)
- [2. El modelo de datos completo](#2-el-modelo-de-datos-completo)
- [3. Cómo viaja una request](#3-cómo-viaja-una-request)
- [4. Alembic en este proyecto](#4-alembic-en-este-proyecto)
- [5. Glosario de términos técnicos](#5-glosario-de-términos-técnicos)
- [6. Estado real vs. documentado — Incongruencias detectadas](#6-estado-real-vs-documentado--incongruencias-detectadas)

---

## 1. Cómo está construido, en general

El backend de pos-boutique es una aplicación Python que usa tres piezas
principales. Esta sección explica qué hace cada una **en este proyecto
específico**, no en abstracto.

### 1.1 FastAPI — el servidor web

FastAPI es el framework que recibe las peticiones HTTP del frontend (la interfaz
que ve la operadora) y las responde. Vive en `backend/app/main.py`.

Cuando levantas el servidor con `uvicorn app.main:app`, FastAPI:

1. Crea la aplicación con título `"pos-boutique"` y versión `"0.1.0"`
   (`main.py` L15–19).
2. Habilita CORS solo para `http://localhost:5173` — eso significa que solo
   el frontend local de desarrollo (Vite en su puerto default) puede hablar
   con el backend (`main.py` L22–28).
3. Registra 5 routers — uno por cada grupo de endpoints actualmente construidos
   (`main.py` L30–34):
   - `/api/v1/clientes` → CRUD de clientes
   - `/api/v1/movimientos` → operaciones de caja
   - `/api/v1/pedidos` → pedidos (versión vieja, pendiente de reemplazo)
   - `/api/v1/pedidos_shein` → pedidos Shein (versión vieja, pendiente de reemplazo)
   - `/api/v1/auth` → login (JWT)
4. Define un `lifespan` vacío (`main.py` L6–13). Originalmente llamaba a
   `init_db()` aquí, pero ya se eliminó — el comentario en el código lo
   explica: *"Alembic es la única fuente de verdad del esquema"*.

**En resumen:** FastAPI es el puente entre el frontend y la base de datos.
Recibe JSON, valida la estructura, ejecuta la lógica, y devuelve JSON.

### 1.2 SQLAlchemy — el ORM

Un ORM (Object-Relational Mapper) permite definir las tablas de la base de
datos como clases de Python, en vez de escribir SQL directamente. En este
proyecto:

- **Dónde se definen las tablas:** `backend/app/models/models.py`. Cada clase
  (por ejemplo `Cliente`, `Pedido`, `Inventario`) corresponde a una tabla en
  SQLite. Cada atributo `Column(...)` dentro de la clase corresponde a una
  columna de esa tabla.
- **Dónde se configura la conexión:** `backend/app/db/database.py`. Ahí se
  crea el motor de conexión (`create_engine`) apuntando a `pos.db` (un archivo
  SQLite local), se configura el modo **síncrono** (sin async, sin aiosqlite
  — decisión cerrada en REPORT.md §2), y se define `get_db()`, la función
  generadora que abre y cierra la sesión de base de datos en cada request.
- **`Base`:** la clase madre de la que heredan todos los modelos. Vive en
  `database.py` L13 como `DeclarativeBase`. Cuando escribes
  `class Cliente(Base)`, SQLAlchemy sabe que esa clase corresponde a una tabla
  real en la base.

**En resumen:** SQLAlchemy traduce entre objetos Python y filas de SQLite. Cuando
el servicio hace `db.add(cliente)` y `db.commit()`, SQLAlchemy genera y ejecuta
el `INSERT` correspondiente.

### 1.3 Alembic — las migraciones

Alembic es la herramienta que gestiona los cambios al esquema de la base de
datos (crear tablas, agregar columnas, cambiar tipos). Se explica en detalle
en la [Sección 4](#4-alembic-en-este-proyecto).

### 1.4 Cómo se conectan las tres piezas

```
                  ┌─────────────┐
                  │  Frontend   │ (Vite, localhost:5173)
                  └──────┬──────┘
                         │  HTTP request (JSON)
                         ▼
               ┌──────────────────┐
               │    FastAPI       │  main.py → routers en api/v1/endpoints/
               │  (endpoints)     │  Valida con Pydantic (schemas/)
               └────────┬────────┘
                         │  llama funciones Python
                         ▼
               ┌──────────────────┐
               │    Services      │  services/*.py
               │  (lógica de      │  Reglas de negocio, cálculos,
               │   negocio)       │  validaciones complejas
               └────────┬────────┘
                         │  opera con objetos ORM
                         ▼
               ┌──────────────────┐
               │   SQLAlchemy     │  models/models.py + db/database.py
               │  (ORM / sesión)  │  Traduce Python ↔ SQL
               └────────┬────────┘
                         │  genera SQL real
                         ▼
               ┌──────────────────┐
               │    SQLite        │  pos.db (archivo local)
               │  (base de datos) │  Esquema creado por Alembic
               └──────────────────┘
```

**Archivos clave y su rol:**

| Archivo | Rol |
|---|---|
| `backend/app/main.py` | Punto de entrada. Crea la app FastAPI, registra routers y middleware. |
| `backend/app/db/database.py` | Motor SQLAlchemy, sesión, `get_db()` y clase `Base`. |
| `backend/app/core/config.py` | Configuración centralizada: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `TOKEN_EXPIRY_HOURS`. Lee de `.env` si existe. |
| `backend/app/models/models.py` | Todas las clases ORM (tablas). 11 tablas implementadas. |
| `backend/app/schemas/*.py` | Schemas Pydantic: definen la forma del JSON de entrada y salida. |
| `backend/app/services/*.py` | Lógica de negocio: cálculos, validaciones, interacción con la BD. |
| `backend/app/api/v1/endpoints/*.py` | Endpoints HTTP: reciben request, llaman al servicio, devuelven response. |
| `backend/alembic/` | Configuración y scripts de migración de esquema. |
| `backend/app/db/init_db.py` | Utilidad manual: `Base.metadata.create_all()`. **Ya no se invoca automáticamente** — solo queda como referencia. |

---

## 2. El modelo de datos completo

El archivo `backend/app/models/models.py` define **11 tablas** actualmente
migradas a `pos.db`. La tabla `precios_catalogo` está diseñada (REPORT.md §2a)
pero **PENDIENTE** de agregar al código.

A continuación se documenta cada tabla con su propósito de negocio, columnas
clave, relaciones, y la regla de negocio que la justifica.

---

### 2.1 `clientes`

**Clase ORM:** `Cliente` (`models.py` L114–134)

**Propósito de negocio:** representa la cartera de crédito de la boutique. Cada
persona que compra a crédito tiene un registro aquí. Los clientes de Shein no
viven en esta tabla (decisión cerrada — REPORT.md §2).

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_cliente` | `Integer`, PK | Clave interna. Nunca aparece en UI. |
| `no_cliente` | `String`, unique | Identificador operativo visible: `{Colonia}-{consecutivo:03d}`. Lo genera el backend. |
| `nombre` | `String(40)` | Nombre completo del cliente. |
| `colonia` | `String(20)` | Colonia de residencia. También se usa para generar `no_cliente`. |
| `telefono` | `Integer` | 10 dígitos. Decisión cerrada: Integer, no String (REPORT.md §2). |
| `frecuencia_pago` | `Enum(FrecuenciaPago)` | `semanal`, `quincenal`, `dia_especifico_mes`, `otro`. Controla el cálculo de `fecha_pago_programada`. |
| `ref_nombre` | `String(40)` | Nombre del garante/referencia. |
| `ref_colonia` | `String(40)` | Colonia de la referencia. |
| `ref_telefono` | `Integer`, nullable | Teléfono de referencia. Opcional. |
| `saldo` | `Float`, default 0 | Deuda acumulada. `saldo > 0` = deuda activa. Invariante: nunca se sobrescribe, siempre `+=` o `-=`. |
| `estatus` | `Enum(EstatusCliente)` | `activo` o `inactivo`. Cambio siempre manual por la operadora. `saldo = 0` no implica baja automática. |
| `fecha_registro` | `Date` | Autogenerada. Almacenada en ISO 8601 (`YYYY-MM-DD`). |
| `fecha_pago_programada` | `Date`, nullable | `NULL` hasta el primer abono. Recalculada en cada abono: `fecha_abono + frecuencia_pago`. |

**Relaciones:**
- `movimientos` → `relationship("Movimiento")` — un cliente tiene muchos movimientos.
- `pedidos` → `relationship("Pedido")` — un cliente tiene muchos pedidos.

**Regla de negocio citada:** *"saldo = 0 no implica baja automática. El cambio a
inactivo siempre es una decisión operativa explícita de la operadora."*
(`REGLAS_NEGOCIO.md` §2, regla 1; `00_FULLSTACK_DEVELOPMENT.md` L163–165).

---

### 2.2 `pedidos` (cabecera)

**Clase ORM:** `Pedido` (`models.py` L140–149)

**Propósito de negocio:** cabecera de un pedido a proveedor. Un pedido pertenece a
un cliente y agrupa de 1 a 4 artículos (en la tabla `pedidos_articulos`). Antes
esta tabla mezclaba cabecera y artículos en una sola fila — el rediseño la separó
en cabecera + detalle (decisión cerrada — REPORT.md §2).

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_pedido` | `Integer`, PK | Clave interna. |
| `id_cliente` | `Integer`, FK → `clientes.id_cliente` | El cliente que hizo el pedido. |
| `fecha` | `Date`, `server_default=func.current_date()` | Fecha de registro. Autogenerada. |

**Relaciones:**
- `cliente` → `relationship("Cliente")` — cada pedido pertenece a un cliente.
- `articulos` → `relationship("PedidoArticulo")` — un pedido tiene de 1 a 4 artículos.

---

### 2.3 `pedidos_articulos` (detalle)

**Clase ORM:** `PedidoArticulo` (`models.py` L152–172)

**Propósito de negocio:** cada fila es un artículo individual dentro de un pedido.
Puede ser un artículo `principal` o una `alternativa` (opción B que se ofrece
si el principal no está disponible en el proveedor). Cada principal puede tener
0 o 1 alternativa.

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_articulo` | `Integer`, PK | Clave interna. |
| `id_pedido` | `Integer`, FK → `pedidos.id_pedido` | A qué pedido pertenece. |
| `rol` | `Enum(RolArticulo)` | `principal` o `alternativa`. Default: `principal`. |
| `id_articulo_principal` | `Integer`, FK → `pedidos_articulos.id_articulo`, nullable | **Autorreferencia.** Solo se llena cuando `rol = alternativa` — enlaza la alternativa con su artículo principal. |
| `tipo_producto` | `Enum(TipoProducto)` | `formal` (producto de catálogo con proveedor) o `informal` (sin catálogo). |
| `proveedor` | `Enum(Proveedor)`, nullable | `Price_Shoes`, `Pakar`, `Cklass`, `otro`. `NULL` cuando `tipo_producto = informal`. |
| `id_producto` | `String(12)`, nullable | Referencia libre al catálogo del proveedor. No es una FK real — es informativo. |
| `producto` | `String(40)` | Descripción del artículo. Siempre obligatorio. |
| `marca` | `String(20)`, nullable | Opcional. |
| `talla` | `String(8)`, nullable | Opcional. |
| `monto` | `Float`, nullable | Precio. Autollenado vía lookup si el proveedor tiene catálogo, manual si `proveedor = otro`, libre si `informal`. |
| `estatus_articulo` | `Enum(EstatusArticulo)` | `vigente` → `en_almacen` → `devuelto` o `cancelado`. Controla el ciclo de vida y cuándo impacta el saldo. Default: `vigente`. |
| `id_articulo_sustituye` | `Integer`, FK → `pedidos_articulos.id_articulo`, nullable | **Segunda autorreferencia.** Solo se llena en artículos sustitutos de una devolución — apunta al artículo original devuelto. |

**Relaciones:**
- `pedido` → `relationship("Pedido", foreign_keys=[id_pedido])` — cada artículo pertenece a un pedido.
- La relación inversa (`id_articulo_principal` y `id_articulo_sustituye`) no tiene `relationship()` explícita definida en el código — se resuelve manualmente con queries cuando se necesita.

**Regla de negocio citada:** *"El saldo del cliente NO se carga al registrar el
pedido. Se carga únicamente cuando el artículo se marca en_almacen."*
(`REGLAS_NEGOCIO.md` §3, regla 3; `00_FULLSTACK_DEVELOPMENT.md` L638–646).

---

### 2.4 `precios_catalogo` — **PENDIENTE DE IMPLEMENTAR**

**No existe aún en `models.py` ni en la migración.** El diseño está cerrado en
REPORT.md §2a y documentado en `REGLAS_NEGOCIO.md` §3 y
`00_FULLSTACK_DEVELOPMENT.md` L666–698.

**Propósito de negocio:** catálogo de precios de proveedor, importado desde
`tabla_precios.ods`. Permite el "lookup automático" de precio cuando la operadora
ingresa un `id_producto` de un proveedor con catálogo digitalizado.

**Diseño cerrado (tomado de REPORT.md §2a):**

| Columna | Tipo | Propósito |
|---|---|---|
| `id_precio` | Integer, PK | Interno. |
| `proveedor` | Enum (`Price_Shoes`, `Pakar`, `Cklass`) | Sin `otro` — ese proveedor no tiene catálogo. |
| `id_producto` | String(12) | Normalizado desde `ID`/`CÓDIGO`/`modelo` según pestaña. |
| `precio_venta` | Integer | Precio final. |
| `fecha_catalogo` | Date | Desempate: gana `MAX(fecha_catalogo)`. |
| `catalogo` | String, nullable | Preservado del .ods, no usado por el POS. |
| `temporada` | String, nullable | Ídem. |
| `pagina` | Integer, nullable | Ídem. |
| `precio_base` | Integer, nullable | Ídem. |

Sin restricción `UNIQUE`. El mismo `id_producto` puede aparecer en múltiples
catálogos. El script `importar_precios.py` solo hace `INSERT`, nunca borra ni
sobreescribe.

**Lo que falta para implementarlo (tomado de REPORT.md §6 paso 4):**
1. Agregar la clase ORM a `models.py`.
2. Generar migración Alembic.
3. Construir el script `backend/app/scripts/importar_precios.py`.

---

### 2.5 `inventario`

**Clase ORM:** `Inventario` (`models.py` L178–198)

**Propósito de negocio:** existencias propias de la boutique en piso de venta.
No hay almacén separado — piso y almacén son el mismo espacio físico
(`00_FULLSTACK_DEVELOPMENT.md` L1124–1127).

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_producto` | `Integer`, PK | Clave interna. No se reutiliza aunque el producto se venda. |
| `categoria` | `Enum(CategoriaInventario)` | `dama`, `caballero`, `infantil`, `accesorio`, `calzado`. |
| `tipo_producto` | `Enum(TipoProducto)` | `formal` o `informal`. |
| `descripcion` | `String(40)` | Descripción del artículo. |
| `talla` | `String(10)`, nullable | Opcional. |
| `color` | `String(10)`, nullable | Opcional. |
| `marca` | `String(12)`, nullable | Opcional. |
| `precio_venta` | `Integer` | Precio base. Siempre visible en UI. |
| `precio_descuento` | `Integer`, nullable | `NULL` = sin descuento. Con valor = precio vigente con descuento. El porcentaje se calcula al vuelo: `(1 - precio_descuento/precio_venta) * 100`. |
| `stock` | `Integer`, default 0 | Cantidad en existencia. |
| `estatus` | `Enum(EstatusInventario)` | `disponible`, `disponible_c/descuento`, `en_ruta`, `apartado`, `vendido`. |
| `descripcion_ruta` | `String`, nullable | Obligatorio solo si `estatus = en_ruta`. Validado en el servicio, no en el modelo. |
| `created` | `Date`, `server_default` | Fecha de alta. |
| `changed_status` | `Date`, nullable | Se actualiza en cada cambio de estatus. Invariante global del sistema. |

**Relaciones:**
- `movimientos` → `relationship("Movimiento")` — un producto de inventario puede tener muchos movimientos asociados.

**Regla de negocio citada:** *"Todo cambio de estatus debe actualizar changed_status
en la misma transacción."* (`REGLAS_NEGOCIO.md` §4, regla 3).

---

### 2.6 `movimientos`

**Clase ORM:** `Movimiento` (`models.py` L204–218)

**Propósito de negocio:** registro de toda operación de caja. Es la tabla central
del Panel Principal: contado, apartado, abono y gasto. Es la fuente de verdad
para liquidez, historial de abonos y consultas contables.

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_movimiento` | `Integer`, PK | Clave interna. |
| `operacion` | `Enum(Operacion)` | `contado`, `apartado`, `abono`, `gasto`. |
| `id_cliente` | `Integer`, FK → `clientes.id_cliente`, nullable | Obligatorio en `apartado`/`abono`. `NULL` en `gasto`. Opcional en `contado`. |
| `id_producto` | `Integer`, FK → `inventario.id_producto`, nullable | Solo cuando aplica (contado/apartado desde inventario). |
| `monto` | `Float` | Siempre obligatorio, siempre > 0. |
| `forma_pago` | `Enum(FormaPago)` | `efectivo`, `transferencia`, `tarjeta`. |
| `saldo_resultante` | `Float`, nullable | `NULL` en contado/gasto. Calculado en apartado/abono. |
| `descripcion` | `String(60)`, nullable | Obligatoria solo en `gasto`. En el **modelo** el campo se llama `descripcion`, pero en el **schema actual** (`schemas/movimiento.py`) se llama `notas` — ver §6 Incongruencias. |
| `fecha` | `DateTime`, `server_default=func.now()` | Timestamp completo. |

**Relaciones:**
- `cliente` → `relationship("Cliente")` — cada movimiento puede pertenecer a un cliente.
- `producto` → `relationship("Inventario")` — cada movimiento puede vincular un producto.

**Regla de negocio citada:** *"Ninguna operación de caja se registra sin forma_pago."*
(`REGLAS_NEGOCIO.md` §11).

---

### 2.7 `shein_clientes`

**Clase ORM:** `SheinCliente` (`models.py` L225–233)

**Propósito de negocio:** clientes transaccionales de Shein. Independiente de
`clientes` — sin saldo, sin garante, sin frecuencia de pago. Decisión cerrada
(REPORT.md §2): forzarlos en `clientes` contaminaría la cartera de crédito.

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_shein_cliente` | `Integer`, PK | Clave interna. Visible en UI como consecutivo. |
| `nombre` | `String(20)` | Nombre completo. |
| `colonia` | `String(12)` | Colonia. |
| `telefono` | `Integer` | 10 dígitos. |

**Relaciones:**
- `pedidos` → `relationship("SheinPedido")` — un cliente Shein tiene muchos pedidos.

---

### 2.8 `shein_cortes`

**Clase ORM:** `SheinCorte` (`models.py` L236–246)

**Propósito de negocio:** cortes periódicos que calculan el bono por volumen que
Shein otorga. El bono no pertenece a ningún cliente individual — es resultado
agregado del corte.

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_shein_corte` | `Integer`, PK | Clave interna. |
| `fecha_corte` | `Date` | Fecha en que se cierra el corte. |
| `total_pedidos` | `Integer` | Cantidad de artículos incluidos. Calculado por backend. |
| `suma_montos` | `Float` | Suma de montos. Calculado por backend. |
| `porcentaje_bono` | `Float` | Ej: `0.08` para 8%. |
| `bono_monto` | `Float` | `suma_montos × porcentaje_bono`. Calculado por backend. |

**Relaciones:**
- `pedidos` → `relationship("SheinPedido")` — un corte agrupa muchos pedidos.

---

### 2.9 `shein_pedidos`

**Clase ORM:** `SheinPedido` (`models.py` L249–261)

**Propósito de negocio:** cada artículo pedido por un cliente Shein. El pedido
nace sin corte (`id_shein_corte = NULL`) y se asigna a uno al cerrarlo.

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_shein_pedido` | `Integer`, PK | Clave interna. |
| `id_shein_cliente` | `Integer`, FK → `shein_clientes` | A quién pertenece. |
| `id_shein_corte` | `Integer`, FK → `shein_cortes`, nullable | `NULL` hasta que se asigna a un corte. |
| `producto` | `String` | Descripción libre. No hay catálogo formal de Shein. |
| `monto` | `Float` | Precio en app Shein al momento del pedido. |
| `monto_vigente` | `Float`, nullable | `NULL` hasta cerrar corte. Se llena si el precio varió. |
| `fecha` | `Date`, `server_default=func.current_date()` | Fecha de registro. |

**Relaciones:**
- `cliente` → `relationship("SheinCliente")` — cada pedido Shein pertenece a un cliente Shein.
- `corte` → `relationship("SheinCorte")` — cada pedido puede pertenecer a un corte.

---

### 2.10 `recargas`

**Clase ORM:** `Recarga` (`models.py` L268–274)

**Propósito de negocio:** registro de recargas telefónicas vendidas. Tabla
completamente independiente — sin relaciones con clientes ni inventario. Solo
trazabilidad de ingresos.

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_recarga` | `Integer`, PK | Clave interna. |
| `compania` | `Enum(Compania)` | `Telcel`, `Movistar`, `Unefon`, `AT&T`. |
| `monto` | `Float` | Monto de la recarga. Sin validación de tope. |
| `fecha` | `DateTime`, `server_default=func.now()` | Timestamp completo. |

---

### 2.11 `usuarios`

**Clase ORM:** `Usuario` (`models.py` L281–289)

**Propósito de negocio:** cuentas de acceso al sistema. Autenticación activa vía
JWT en todos los endpoints. Sin `AUTH_ENABLED` — la autenticación no se puede
desactivar.

| Columna | Tipo en código | Propósito |
|---|---|---|
| `id_usuario` | `Integer`, PK | Clave interna. |
| `usuario` | `String`, unique | Nombre de usuario para login. 4 a 16 caracteres. |
| `password_hash` | `String` | Hash bcrypt de la contraseña. Nunca texto plano. |
| `rol` | `String`, default `"estandar"` | `estandar` o `admin`. Permisos diferenciados pendientes de implementar. |
| `activo` | `Integer`, default `1` | `1` = activo, `0` = desactivado. |
| `fecha_registro` | `DateTime`, `server_default=func.now()` | Autogenerada. |

**Nota:** el campo se llama `usuario` en el modelo y `password_hash` en el modelo.
Los schemas viejos (`schemas/usuario.py`) aún usan `username` y `hashed_password` —
ver §6 Incongruencias.

---

### 2.12 `configuracion`

**Clase ORM:** `Configuracion` (`models.py` L296–300)

**Propósito de negocio:** tabla clave-valor que controla parámetros del sistema
(métodos de pago activos, CLABEs registradas, zona horaria).

| Columna | Tipo en código | Propósito |
|---|---|---|
| `clave` | `String`, PK | Identificador del parámetro. Ej: `pago_efectivo_activo`. |
| `valor` | `String` | Valor del parámetro. Ej: `"1"` para activo. |

Los valores iniciales (seed) están documentados en `00_FULLSTACK_DEVELOPMENT.md`
L2277–2287 pero **PENDIENTE** de implementar como seed real.

---

### 2.13 Mapa visual de relaciones

```
clientes ─────────┬────── pedidos ────── pedidos_articulos ──┐
  │                │                          │    │           │
  │  (FK)          │  (FK)              (FK auto-  (FK auto-  │
  │                │                   referencia  referencia  │
  │                │                   rol=alt)    sustituye)  │
  ▼                ▼                                          │
movimientos ◄─── inventario                                   │
                                                              │
precios_catalogo (sin FK, lookup por proveedor+id_producto)  ─┘
                                    [PENDIENTE]

shein_clientes ──── shein_pedidos ──── shein_cortes

recargas           (independiente)
usuarios           (independiente)
configuracion      (independiente)
```

---

## 3. Cómo viaja una request

El patrón es el mismo en todos los módulos construidos. Lo explico con el
ejemplo completo de **Registrar un Cliente** (POST `/api/v1/clientes`), que
es el flujo más ilustrativo porque toca todas las capas y está completamente
construido.

### 3.1 El frontend envía un POST

El frontend (Vite en `localhost:5173`) envía una petición HTTP al backend:

```
POST http://localhost:8000/api/v1/clientes
Content-Type: application/json
Authorization: Bearer <token_jwt>

{
  "nombre": "María López",
  "colonia": "Carrillos",
  "telefono": "5512345678",
  "ref_nombre": "Juan García",
  "ref_colonia": "Centro",
  "ref_telefono": null,
  "frecuencia_pago": "quincenal"
}
```

> **Nota sobre `frecuencia_pago`:** el schema actual `ClienteCreate`
> (`schemas/cliente.py` L6–19) **no incluye el campo `frecuencia_pago`** — ver
> §6 Incongruencias. Lo incluyo aquí porque la spec lo requiere
> (`00_FULLSTACK_DEVELOPMENT.md` L240).

### 3.2 FastAPI recibe la petición → Endpoint

FastAPI enruta la petición al endpoint `registrar_cliente` en
`api/v1/endpoints/clientes.py` L11–17:

```python
@router.post("", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
def registrar_cliente(
    data: ClienteCreate,            # ← paso 3.3
    db: Session = Depends(get_db),  # ← paso 3.4
    _: object = Depends(get_current_user),  # ← paso 3.5
):
    return crear_cliente(db, data)  # ← paso 3.6
```

### 3.3 Validación del JSON → Schema Pydantic

FastAPI toma el JSON del body y lo pasa a `ClienteCreate` (definido en
`schemas/cliente.py` L6–19). Pydantic valida automáticamente:

- Que todos los campos requeridos existan (`nombre`, `colonia`, `telefono`,
  `ref_nombre`, `ref_colonia`).
- Que sean del tipo correcto (`str` en este caso).
- Que pasen los validadores personalizados — aquí hay un `@field_validator`
  que rechaza cadenas vacías o solo con espacios (`L14–19`).

Si el JSON no pasa la validación, FastAPI devuelve automáticamente un
HTTP 422 con los detalles del error. El endpoint **nunca llega a ejecutarse**.

### 3.4 Sesión de base de datos → `get_db()`

`Depends(get_db)` inyecta una sesión de SQLAlchemy. Viene de `database.py`
L17–22:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db       # ← el endpoint la usa
    finally:
        db.close()     # ← al terminar, se cierra automáticamente
```

Es una sesión con `autocommit=False` — nada se escribe a disco hasta que el
servicio haga `db.commit()` explícitamente.

### 3.5 Autenticación → `get_current_user()`

`Depends(get_current_user)` extrae el token JWT del header `Authorization: Bearer`,
lo decodifica con la `SECRET_KEY`, y verifica que el usuario exista y esté activo.
Está en `services/auth_service.py` L81–110.

Si el token es inválido, expirado, o el usuario no existe, se devuelve HTTP 401
y el endpoint no se ejecuta.

### 3.6 Lógica de negocio → Servicio

El endpoint llama a `crear_cliente(db, data)` en `services/cliente_service.py`
L23–40:

```python
def crear_cliente(db: Session, data: ClienteCreate) -> Cliente:
    no_cliente = generar_no_cliente(db, data.colonia)    # genera "Carrillos-001"

    cliente = Cliente(                                    # crea el objeto ORM
        no_cliente=no_cliente,
        nombre=data.nombre,
        colonia=data.colonia,
        telefono=data.telefono,
        ref_nombre=data.ref_nombre,
        ref_colonia=data.ref_colonia,
        ref_telefono=data.ref_telefono,
        saldo=0.0,
        estatus="activo",
    )
    db.add(cliente)         # le dice a SQLAlchemy: "prepara un INSERT"
    db.commit()             # ejecuta el INSERT real en SQLite
    db.refresh(cliente)     # re-lee de la BD para obtener id_cliente y campos autogenerados
    return cliente
```

`generar_no_cliente()` (L6–20) cuenta cuántos clientes ya existen con ese
prefijo de colonia y asigna el siguiente consecutivo: `Carrillos-001`,
`Carrillos-002`, etc.

### 3.7 SQLAlchemy → SQLite

Cuando el servicio hace `db.commit()`, SQLAlchemy genera y ejecuta el SQL real:

```sql
INSERT INTO clientes (no_cliente, nombre, colonia, telefono, ref_nombre,
                      ref_colonia, ref_telefono, saldo, estatus)
VALUES ('Carrillos-001', 'María López', 'Carrillos', '5512345678',
        'Juan García', 'Centro', NULL, 0.0, 'activo');
```

`fecha_registro` lo genera SQLite automáticamente gracias al
`server_default=func.current_date()` definido en el modelo.

### 3.8 Respuesta al frontend

El endpoint devuelve el objeto `Cliente` — FastAPI lo serializa usando el schema
`ClienteRead` (`schemas/cliente.py` L22–35), que define exactamente qué campos
se incluyen en la respuesta JSON:

```json
{
  "id_cliente": 1,
  "no_cliente": "Carrillos-001",
  "nombre": "María López",
  "colonia": "Carrillos",
  "telefono": "5512345678",
  "ref_nombre": "Juan García",
  "ref_colonia": "Centro",
  "ref_telefono": null,
  "saldo": 0.0,
  "estatus": "activo",
  "fecha_registro": "2026-06-29T00:00:00"
}
```

### 3.9 El mismo patrón en Movimientos

El módulo de movimientos sigue exactamente el mismo flujo. Usando como ejemplo
**POST `/api/v1/movimientos`** (registrar un abono):

1. **Endpoint:** `api/v1/endpoints/movimientos.py` L11–17.
2. **Schema:** `MovimientoCreate` (`schemas/movimiento.py` L7–32) — valida que
   `monto > 0`, que `apartado`/`abono` tengan `id_cliente`, que `gasto` no
   lo tenga.
3. **Autenticación:** misma `Depends(get_current_user)`.
4. **Servicio:** `registrar_movimiento()` (`services/movimiento_service.py`
   L7–67) — valida que el cliente exista, calcula `saldo_resultante`, actualiza
   `cliente.saldo`, crea el `Movimiento`.
5. **Respuesta:** serializada con `MovimientoRead`.

---

## 4. Alembic en este proyecto

### 4.1 ¿Qué es una migración?

Una migración es un script de Python que dice "haz estos cambios al esquema de
la base de datos". En este proyecto, el esquema son las 11 tablas que existen
en `pos.db`. Cada migración tiene dos funciones:

- `upgrade()` — aplica el cambio (crear tabla, agregar columna, etc.).
- `downgrade()` — deshace el cambio (borrar tabla, quitar columna).

### 4.2 Archivos de Alembic en este repo

| Archivo | Propósito |
|---|---|
| `backend/alembic.ini` | Configuración principal. Define dónde está el directorio de scripts (`script_location = %(here)s/alembic`) y la URL de la base (`sqlalchemy.url = sqlite:///./pos.db`). |
| `backend/alembic/env.py` | Script que Alembic ejecuta al correr una migración. Importa `Base.metadata` desde `models.py` (L2, L22) — esto es lo que le permite a Alembic "ver" tus modelos y comparar contra la BD real. |
| `backend/alembic/versions/a1b2c3d4e5f6_esquema_inicial.py` | La **única migración vigente**. Crea las 11 tablas desde cero. |

### 4.3 La migración inicial en detalle

El archivo `a1b2c3d4e5f6_esquema_inicial.py` es el esquema inicial limpio:

- **Revision ID:** `a1b2c3d4e5f6`
- **down_revision:** `None` — no depende de ninguna migración anterior.
- **Fecha:** 2026-06-29.
- **Qué hace:** su `upgrade()` crea las 11 tablas con todos sus índices,
  foreign keys y constraints. Su `downgrade()` las borra en orden inverso
  (primero las tablas que dependen de otras, después las independientes).

La migración reemplazó por completo el historial anterior (migraciones
`38241ae2061c` y `97592862ac88` del esquema viejo). `pos.db` fue reseteado —
no hubo datos que migrar (decisión cerrada — REPORT.md §2).

### 4.4 Cómo se generan migraciones nuevas

Cuando necesites cambiar el esquema (por ejemplo, agregar la tabla
`precios_catalogo`), el proceso es:

1. **Modificas `models.py`** — agregas la nueva clase ORM.
2. **Generas la migración automáticamente:**
   ```bash
   cd backend
   alembic revision --autogenerate -m "agregar precios_catalogo"
   ```
   Alembic compara lo que dice `models.py` (a través de `Base.metadata`) contra
   lo que existe en `pos.db`, y genera un script con las diferencias.
3. **Revisas el script generado** — Alembic a veces no detecta todo
   perfectamente (por ejemplo, renombrados de columnas los interpreta como
   "borrar + crear"), así que siempre hay que revisar.
4. **Aplicas la migración:**
   ```bash
   alembic upgrade head
   ```
   Esto ejecuta la función `upgrade()` del script y aplica los cambios a `pos.db`.

### 4.5 ¿Qué pasa si modificas `models.py` sin generar una migración?

**El código se desincroniza de la base de datos.** Ejemplo: si agregas una
columna `email` a la clase `Cliente` en `models.py` pero no generas migración,
la tabla `clientes` en `pos.db` no tiene esa columna. El resultado:

- Las queries de SQLAlchemy que intenten leer o escribir `email` fallarán con
  un error de SQLite (columna no existe).
- Alembic no sabe que algo cambió hasta que le pidas comparar (`--autogenerate`).

### 4.6 El riesgo de `init_db.py`

`init_db.py` (`app/db/init_db.py` L1–9) llama a `Base.metadata.create_all()`.
Esa función crea las tablas **que no existan** en la base de datos, pero no
modifica tablas que ya existan. El riesgo era:

- Si se corría `init_db()` automáticamente en cada arranque del servidor **y**
  alguien modificaba `models.py` sin migración, las tablas nuevas aparecerían
  en `pos.db` pero sin pasar por Alembic — y Alembic no sabría que existen.
  Eso desincroniza la tabla `alembic_version` (donde Alembic registra qué
  migraciones ya se aplicaron) de la realidad del esquema.

**Estado actual (riesgo cerrado):** el `lifespan` de `main.py` ya no llama a
`init_db()` — el comentario en el código (L8–12) lo confirma explícitamente.
Alembic es ahora la **única forma** de crear o modificar tablas. `init_db.py`
queda como utilidad manual de desarrollo.

---

## 5. Glosario de términos técnicos

Cada término se define con un ejemplo tomado directamente del código del repo.

| Término | Definición | Ejemplo en el repo |
|---|---|---|
| **ORM** (Object-Relational Mapper) | Capa que traduce entre clases Python y tablas SQL. En vez de escribir `INSERT INTO clientes...`, haces `db.add(cliente)`. | `class Cliente(Base)` en `models.py` L114 corresponde a la tabla `clientes` en SQLite. |
| **FK** (Foreign Key / Clave foránea) | Columna que referencia la clave primaria de otra tabla. Garantiza que no puedas insertar un pedido para un cliente que no existe. | `id_cliente = Column(Integer, ForeignKey("clientes.id_cliente"))` en `Pedido` (`models.py` L145). |
| **PK** (Primary Key / Clave primaria) | Columna que identifica de manera única cada fila de una tabla. | `id_cliente = Column(Integer, primary_key=True)` en `Cliente` (`models.py` L117). |
| **Migración** | Script que aplica un cambio de esquema a la base de datos de forma controlada y versionada. | `a1b2c3d4e5f6_esquema_inicial.py` — crea las 11 tablas (`alembic/versions/`). |
| **Schema (Pydantic)** | Clase que define la estructura del JSON de entrada o salida de un endpoint. Valida tipos y reglas antes de que el código de negocio se ejecute. | `ClienteCreate` en `schemas/cliente.py` L6 — define qué campos necesita un POST de registro. |
| **Enum** | Tipo que restringe los valores posibles de una columna a una lista cerrada. | `class FrecuenciaPago(enum.Enum): semanal, quincenal, dia_especifico_mes, otro` en `models.py` L38–42. |
| **Lookup** | Consulta que busca un valor en otra tabla para autocompletar un campo. | Lookup de precio: `SELECT precio_venta FROM precios_catalogo WHERE proveedor = :p AND id_producto = :id ORDER BY fecha_catalogo DESC LIMIT 1` (documentado en `00_FULLSTACK_DEVELOPMENT.md` L688–696, **PENDIENTE** de implementar). |
| **Endpoint** | URL del backend que responde a un tipo específico de petición HTTP. | `POST /api/v1/clientes` → función `registrar_cliente()` en `api/v1/endpoints/clientes.py` L11. |
| **Router** | Agrupación lógica de endpoints por módulo. FastAPI los registra en `main.py`. | `router = APIRouter(prefix="/clientes", tags=["clientes"])` en `clientes.py` L8. |
| **Dependency Injection** | Mecanismo de FastAPI que inyecta objetos (sesión de BD, usuario autenticado) en los endpoints automáticamente. | `db: Session = Depends(get_db)` — inyecta la sesión. `_: object = Depends(get_current_user)` — inyecta la verificación de JWT. |
| **Relationship** | Declaración en un modelo ORM que permite navegar de una tabla a otra usando Python, sin escribir JOINs manuales. | `pedidos = relationship("Pedido", back_populates="cliente")` en `Cliente` (`models.py` L133). Permite hacer `cliente.pedidos` para obtener todos los pedidos de un cliente. |
| **Autorreferencia (self-referential FK)** | Foreign key que apunta a la misma tabla. Permite crear jerarquías dentro de una sola tabla. | `id_articulo_principal = Column(Integer, ForeignKey("pedidos_articulos.id_articulo"))` en `PedidoArticulo` (`models.py` L159). Una alternativa apunta al principal dentro de la misma tabla. |
| **`server_default`** | Valor por defecto que genera SQLite (no Python) al insertar una fila. | `server_default=func.current_date()` en `fecha_registro` de `Cliente` (`models.py` L129) — SQLite genera la fecha. |
| **Lifespan** | Hook de FastAPI que se ejecuta al iniciar y al apagar la aplicación. | El `lifespan` en `main.py` L6–13 — actualmente vacío (ya no llama a `init_db()`). |
| **JWT** (JSON Web Token) | Estándar para tokens de autenticación. El backend genera uno al login, el frontend lo incluye en cada petición posterior. | `crear_token({"sub": usuario.usuario, "rol": usuario.rol})` en `auth.py` L26. Se decodifica en `get_current_user()` (`auth_service.py` L97–98). |
| **Seed** | Datos iniciales que se insertan en la base de datos para que el sistema funcione desde el primer momento. | Usuarios iniciales documentados en `00_FULLSTACK_DEVELOPMENT.md` L2222–2229: `sonia` y `operador2`. Valores de configuración en L2277–2287. **PENDIENTE** de implementar como script real. |
| **CORS** | Política de seguridad del navegador que controla qué orígenes pueden hacer peticiones al backend. | `allow_origins=["http://localhost:5173"]` en `main.py` L23 — solo permite el frontend local. |

---

## 6. Estado real vs. documentado — Incongruencias detectadas

Las siguientes inconsistencias fueron encontradas comparando el código real
contra `00_FULLSTACK_DEVELOPMENT.md`, `REGLAS_NEGOCIO.md` y `REPORT.md`. No
se corrige ningún archivo — solo se documenta.

> **Nota:** varias de estas incongruencias ya están identificadas y documentadas
> en REPORT.md §3.1 y §5 como pendientes de ajuste. Las listo aquí para
> completitud y con referencia exacta de archivo y línea.

---

### INC-01: `schemas/cliente.py` — `telefono` definido como `str`, no como `int`

- **Código:** `schemas/cliente.py` L9: `telefono: str`; L12: `ref_telefono: Optional[str]`.
- **Spec:** `00_FULLSTACK_DEVELOPMENT.md` L115, L119: `telefono INTEGER`;
  `REGLAS_NEGOCIO.md` §2: `telefono Integer`.
- **Modelo ORM:** `models.py` L121: `Column(Integer)` — el modelo sí usa `Integer`.
- **Impacto:** el schema acepta strings y se los pasa al servicio, que los
  asigna a una columna `Integer` del ORM. SQLAlchemy puede hacer la conversión
  implícitamente en SQLite, pero es una divergencia respecto a la spec.
- **Estado en REPORT.md:** documentado como pendiente (§6 paso 5).

---

### INC-02: `schemas/cliente.py` — falta el campo `frecuencia_pago`

- **Código:** `schemas/cliente.py` L6–19 — `ClienteCreate` no incluye el campo
  `frecuencia_pago`.
- **Spec:** `00_FULLSTACK_DEVELOPMENT.md` L240: `frecuencia_pago` es campo
  obligatorio en el formulario de registro.
- **Modelo ORM:** `models.py` L122: `frecuencia_pago = Column(Enum(FrecuenciaPago), nullable=False)`.
- **Impacto:** el servicio `crear_cliente()` (`cliente_service.py` L26–36) crea
  el `Cliente` sin asignar `frecuencia_pago` — SQLAlchemy usará el default
  (no definido para este campo, `nullable=False`), lo que provocará un error
  en tiempo de ejecución al intentar hacer `INSERT`.
- **Estado en REPORT.md:** documentado como pendiente (§6 paso 5).

---

### INC-03: `schemas/movimiento.py` — campo `notas` en vez de `descripcion`

- **Código:** `schemas/movimiento.py` L13: `notas: Optional[str] = None`.
  `MovimientoRead` L43: `notas: Optional[str]`.
- **Spec:** `00_FULLSTACK_DEVELOPMENT.md` L1539–1541: la columna se llama
  `descripcion`. `REGLAS_NEGOCIO.md` §5: `descripcion String(60), nullable`.
- **Modelo ORM:** `models.py` L214: `descripcion = Column(String(60))`.
- **Impacto:** el schema le pone `notas`, pero el modelo tiene `descripcion`. En
  `movimiento_service.py` L61, se hace `notas=data.notas` — esto asignará el
  valor a un atributo `notas` que no existe en la clase `Movimiento`. El modelo
  no tiene un campo `notas`, tiene `descripcion`.
- **Estado en REPORT.md:** documentado como pendiente (§6 paso 6).

---

### INC-04: `schemas/movimiento.py` — sin validación de `descripcion` obligatoria para `gasto`

- **Código:** `schemas/movimiento.py` L22–32 — el `model_validator` valida que
  `gasto` no tenga `id_cliente`, pero **no** valida que tenga `notas`/`descripcion`
  presente.
- **Spec:** `00_FULLSTACK_DEVELOPMENT.md` L1539–1541: *"Obligatorio cuando
  operacion = 'gasto'"*. `REGLAS_NEGOCIO.md` §5: *"descripcion String(60),
  nullable — Obligatoria únicamente en 'gasto'"*.
- **Estado en REPORT.md:** documentado como pendiente (§6 paso 6).

---

### INC-05: `services/movimiento_service.py` — saldo se sobrescribe, no se suma

- **Código:** `movimiento_service.py` L37: `cliente.saldo = saldo_resultante`
  (en operación `apartado`).
- **Spec:** `00_FULLSTACK_DEVELOPMENT.md` L1682: `UPDATE clientes SET saldo = saldo + :saldo_resultante`.
  `REGLAS_NEGOCIO.md` §5, regla de Apartado punto 3: *"saldo_resultante = precio_producto − primer_pago, se suma al saldo existente del cliente"*.
  `REGLAS_NEGOCIO.md` §11: *"El saldo de un cliente nunca se sobrescribe — siempre saldo += monto o saldo -= monto"*.
- **Impacto:** si un cliente ya tiene saldo de un apartado anterior y hace un
  segundo apartado, el saldo del primer apartado se pierde.
- **Estado en REPORT.md:** documentado como riesgo activo §5 punto 1.

---

### INC-06: `services/movimiento_service.py` — sin validación de mínimo $100 en apartado

- **Código:** `movimiento_service.py` L28–36 — la rama de `apartado` solo
  valida `monto < 0`, no verifica que el primer pago sea ≥ $100.
- **Spec:** `00_FULLSTACK_DEVELOPMENT.md` L1579: *"El primer pago mínimo es $100.00.
  El backend rechaza si monto < 100"*. `REGLAS_NEGOCIO.md` §5: *"Primer pago
  mínimo: $100.00. El backend rechaza montos menores"*.
- **Estado en REPORT.md:** documentado como riesgo activo §5 punto 2.

---

### INC-07: `services/movimiento_service.py` y `cliente_service.py` — uso de estatus `"liquidado"`

- **Código:** `movimiento_service.py` L52: `cliente.estatus = "liquidado"` (cuando
  saldo llega a 0 tras un abono). `cliente_service.py` L67, L73: función
  `rehabilitar_cliente()` cambia de `"liquidado"` a `"activo"`.
- **Spec:** `00_FULLSTACK_DEVELOPMENT.md` L122, L158–161: el enum de estatus solo
  tiene `activo` e `inactivo`. `REGLAS_NEGOCIO.md` §2, regla 1:
  *"saldo = 0 no implica baja automática"*.
- **Modelo ORM:** `models.py` L45–47: `class EstatusCliente(enum.Enum): activo, inactivo`.
  No existe `liquidado`.
- **Impacto:** asignar `"liquidado"` a una columna con `Enum('activo', 'inactivo')`
  provocaría un error en tiempo de ejecución, o si SQLite lo acepta (por su
  sistema de tipos flexible), la fila quedaría con un valor fuera del enum que
  el ORM no reconoce.
- **Estado en REPORT.md:** documentado como riesgo activo §5 punto 3.

---

### INC-08: `schemas/usuario.py` — usa `username` y `hashed_password`, no `usuario` y `password_hash`

- **Código:** `schemas/usuario.py` L7: `username: str`; L28: `username: str`;
  L30: `activo: str` (debería ser `int`).
- **Spec:** decisión cerrada en REPORT.md §2: campo `usuario` (no `username`) y
  `password_hash` (no `hashed_password`).
- **Modelo ORM:** `models.py` L285: `usuario = Column(String)`;
  L286: `password_hash = Column(String)`; L288: `activo = Column(Integer)`.
- **Impacto:** `UsuarioRead` (`schemas/usuario.py` L26–33) define `username: str`,
  pero el modelo tiene `usuario`. Pydantic con `from_attributes = True`
  intentará leer `obj.username`, que no existe — causará error al serializar
  la respuesta. También define `activo: str` cuando debería ser `int`.
- **Estado en REPORT.md:** documentado como pendiente (§6 paso 7).

---

### INC-09: `schemas/token.py` — `TokenData.username` en vez de `TokenData.usuario`

- **Código:** `schemas/token.py` L13: `username: Optional[str] = None`.
- **Uso en `auth_service.py`** L103: `token_data = TokenData(username=usuario, rol=rol)`;
  L107: `obtener_usuario(db, token_data.username)`.
- **Comentario:** este no es un error funcional en el estado actual — el campo
  `username` en `TokenData` es un nombre interno del schema (no mapea al modelo
  con `from_attributes`), y `auth_service.py` lo usa consistentemente. Sin
  embargo, es confuso porque el modelo se llama `usuario`, no `username`.
  La decisión de renombrar está documentada en REPORT.md §2 y L46–48 de
  `auth_service.py` tiene un comentario que lo reconoce.

---

### INC-10: `schemas/cliente.py` — `ClienteRead` no incluye `fecha_pago_programada`

- **Código:** `schemas/cliente.py` L22–35 — `ClienteRead` incluye campos hasta
  `fecha_registro` pero no `fecha_pago_programada`.
- **Spec:** `00_FULLSTACK_DEVELOPMENT.md` L452: el encabezado de Consulta
  Historial incluye `fecha_pago_programada` como dato del cliente.
- **Modelo ORM:** `models.py` L130: `fecha_pago_programada = Column(Date, nullable=True)`.
- **Impacto:** el frontend no puede mostrar `fecha_pago_programada` en la
  respuesta del endpoint de detalle de cliente porque el schema de salida no
  lo incluye.

---

### INC-11: `movimiento_service.py` — asigna `notas=data.notas` al construir `Movimiento`

- **Código:** `movimiento_service.py` L61: `notas=data.notas`.
- **Modelo ORM:** la clase `Movimiento` (`models.py` L204–218) no tiene un
  campo `notas` — tiene `descripcion`.
- **Impacto:** al construir el objeto `Movimiento(notas=data.notas)`, SQLAlchemy
  recibirá un argumento que no corresponde a ninguna columna mapeada. El
  comportamiento depende de la versión de SQLAlchemy: puede ignorarlo
  silenciosamente o lanzar un `TypeError`.
- **Relación con INC-03:** es la otra cara del mismo problema — el schema usa
  `notas` y el servicio le pasa `notas` al modelo, que espera `descripcion`.

---

### INC-12: `main.py` — referencia al REPORT sobre `init_db()` ya resuelta

- **Código:** `main.py` L8–12 — el comentario dice que `init_db()` ya no se
  ejecuta y que Alembic es la fuente de verdad.
- **Estado en REPORT.md:** §2 registra esta decisión como cerrada, pero §5
  punto 4 aún la lista como "riesgo activo" diciendo: *"Base.metadata.create_all()
  corre en cada arranque del servidor"*. **Esto ya no es cierto** — el código
  actual de `main.py` ya no llama a `init_db()`.
- **Resultado:** el riesgo activo §5.4 del REPORT está desactualizado. La
  corrección ya se hizo en el código, pero el REPORT no se actualizó.

---

### Resumen de incongruencias

| ID | Archivos involucrados | Severidad | Ya documentada en REPORT |
|---|---|---|---|
| INC-01 | `schemas/cliente.py` vs `models.py` | Media | Sí (§6.5) |
| INC-02 | `schemas/cliente.py` vs `models.py` / spec | Alta | Parcialmente (§6.5) |
| INC-03 | `schemas/movimiento.py` vs `models.py` | Alta | Sí (§6.6) |
| INC-04 | `schemas/movimiento.py` vs spec | Media | Sí (§6.6) |
| INC-05 | `services/movimiento_service.py` vs spec | Crítica | Sí (§5.1) |
| INC-06 | `services/movimiento_service.py` vs spec | Alta | Sí (§5.2) |
| INC-07 | `services/movimiento_service.py` + `cliente_service.py` vs `models.py` | Crítica | Sí (§5.3) |
| INC-08 | `schemas/usuario.py` vs `models.py` | Alta | Sí (§6.7) |
| INC-09 | `schemas/token.py` vs convención | Baja | Parcialmente (§6.7) |
| INC-10 | `schemas/cliente.py` vs spec | Media | No |
| INC-11 | `services/movimiento_service.py` vs `models.py` | Alta | Implícita (§6.6) |
| INC-12 | `REPORT.md` §5.4 vs `main.py` | Informativa | No — REPORT desactualizado |

---

> **Fin del documento.** Si encuentras algún dato aquí que ya no corresponda al
> estado del código después de una sesión de trabajo, actualiza la sección
> correspondiente o marca la incongruencia como resuelta en la tabla de §6.
