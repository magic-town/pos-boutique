# ROADMAP FRONTEND — pos-boutique

> **Qué es este documento:** plan de trabajo para construir el frontend. No es
> código ni spec de componentes — es la ruta de construcción sesión a sesión,
> pensada para ajustarse conforme se implemente. Equivalente en espíritu a
> `docs/REPORT.md`, pero para frontend.
>
> **Convención:** todo lo que viene de un documento fuente (`ARQUITECTURA.md`,
> `REGLAS_NEGOCIO.md`, `module_*.md`, `REPORT.md`) se cita explícitamente.
> Lo que es recomendación o inferencia propia se marca con **[Recomendación]**
> o **[Inferido]**. Una sesión nueva puede retomar el trabajo sin releer todo
> el repo.

---

## 1. Decisiones abiertas de stack/UI

`ARQUITECTURA.md` §2 confirma **React + TypeScript + Vite**. No cierra lo
siguiente — para cada punto se incluye una recomendación de arranque.

### 1.1 Librería de componentes

**[Recomendación]** No usar librería de terceros (MUI, Ant Design, Chakra).
Construir componentes propios con CSS vanilla.

**Justificación:** el sistema tiene una UI altamente específica (modales de menú
de opciones, formularios condicionales por `frecuencia_pago`, tabla con renglones
expandibles para cortes Shein, descuento masivo con doble modo de segmento).
Una librería genérica impone convenciones de layout y theming que habría que
pelear constantemente. Componentes propios permiten control total y alineación
exacta a los `module_*.md` sin adapter layers.

### 1.2 Manejo de formularios y validación

**[Recomendación]** `react-hook-form` + `zod`.

**Justificación:**
- Los formularios del sistema son medianos (Registrar Cliente: 9 campos, Registrar
  Pedido: hasta 4 artículos × 8 campos, Registrar Apartado: N artículos × 4 campos),
  con validación condicional compleja (campos que aparecen/desaparecen según
  `frecuencia_pago`, `proveedor`, `tipo_producto`).
- `react-hook-form` evita re-renders por campo y maneja arrays de artículos
  (`useFieldArray`) de forma nativa.
- `zod` permite declarar schemas de validación que espejean las reglas del backend
  (longitudes de campo, enums, condicionales) sin duplicar lógica de negocio — solo
  UX (mensajes y feedback visual antes de enviar).

### 1.3 Cliente HTTP

**[Recomendación]** Wrapper delgado sobre `fetch` nativo, no Axios.

**Justificación:** el proyecto no tiene necesidades complejas de interceptores,
upload progress ni cancelación masiva. Un wrapper propio de ~50 líneas cubre:
- Base URL configurable (`/api/v1`).
- Inyección automática de `Authorization: Bearer <token>`.
- Manejo centralizado de 401 (redirect a login, ver §3.1).
- Serialización/deserialización JSON.
- Tipado de respuesta con generics de TypeScript.

### 1.4 Manejo de estado / datos remotos

**[Recomendación]** `@tanstack/react-query` (TanStack Query).

**Justificación:**
- El 100% de los datos del sistema vive en el backend — no hay estado puramente
  local que justifique Redux o Zustand.
- TanStack Query resuelve cache, invalidación, loading states, error states y
  refetch automático, que son exactamente los patrones que necesita cada pantalla
  de consulta (Consulta Cliente, Consulta Historial, Lista de Surtido, Consulta
  Inventario, Lista de Pedidos Shein, Consulta de Cortes, Consulta Global).
- Estado local mínimo (formularios en curso, modal abierto/cerrado) se maneja con
  `useState` / `useReducer` — sin store global.

### 1.5 Routing

**[Recomendación]** `react-router` v6+ (o v7 si ya es estable al momento de
implementar).

**Justificación:** el sistema tiene un patrón de navegación claro derivado de los
`module_*.md`:

```
/login
/                          ← Panel Principal (home, siempre visible)
/clientes/consulta         ← Consulta Cliente (página completa)
/clientes/historial        ← Consulta Historial (página completa)
/inventario/consulta       ← Consulta Inventario (página completa)
/pedidos/surtido           ← Lista de Surtido (página completa)
/shein/pedidos             ← Lista de Pedidos Shein (página completa)
/shein/cortes              ← Consulta de Cortes (página completa)
/consulta-global           ← Consulta Global (página completa)
```

Los formularios cortos (Registrar Cliente, Editar Cliente, Agregar Producto,
Cambiar Estatus, Registrar Pedido, Registrar Devolución, Cancelar Artículo,
Registrar Cliente Shein, Registrar Pedido Shein, Registrar Corte, Registrar
Recarga, Registrar Apartado, todas las opciones de Setting) son **modales** que
se abren sobre la ruta actual — no rutas propias.

> **Fuente:** `ROADMAP_FRONTEND.md` (prompt) — decisiones ya tomadas: formularios
> cortos = modal, tablas/consultas grandes = página completa.

---

## 2. Inventario de pantallas por módulo

Derivado del patrón `main_menu → modal de opciones → formulario/consulta`.
Cada pantalla indica su tipo (modal vs. página) y la spec de referencia.

### 2.1 Login

| Pantalla | Tipo | Spec |
|---|---|---|
| Login | Página (`/login`) | `module_setting.md` — Autenticación |

Campos: `usuario`, `password`. JWT al backend, token en memoria (o `localStorage`).

### 2.2 Panel Principal (Home)

| Pantalla | Tipo | Spec |
|---|---|---|
| Panel Principal | Página (`/`) | `module_movimientos.md` |

Siempre visible tras login. Contiene:
- Radio buttons: `Contado` / `Apartado` / `Abono` / `Gasto`.
- Campos condicionales por operación (ver tabla "Campos activos por operación"
  en `module_movimientos.md`).
- Botón `⚙️` → abre modal de Setting.
- `main_menu` con botones por módulo → cada uno abre su modal de opciones.

### 2.3 Módulo Clientes

| Pantalla | Tipo | Spec |
|---|---|---|
| Modal menú Clientes | Modal (menú de opciones) | `module_clientes.md` |
| Registrar Cliente | Modal (formulario) | `module_clientes.md` — Opción 1 |
| Editar Cliente | Modal (búsqueda + formulario) | `module_clientes.md` — Opción 2 |
| Consulta Cliente | Página (`/clientes/consulta`) | `module_clientes.md` — Opción 3 |
| Consulta Historial | Página (`/clientes/historial`) | `module_clientes.md` — Opción 4 |

### 2.4 Módulo Pedidos

| Pantalla | Tipo | Spec |
|---|---|---|
| Modal menú Pedidos | Modal (menú de opciones) | `module_pedidos.md` |
| Registrar Pedido | Modal (búsqueda cliente + formulario multi-artículo) | `module_pedidos.md` — Opción 1 |
| Registrar Devolución | Modal (búsqueda + selección de artículo + formulario sustituto) | `module_pedidos.md` — Opción 2 |
| Cancelar Artículo | Modal (búsqueda + selección) | `module_pedidos.md` — Opción 3 |
| Lista de Surtido | Página (`/pedidos/surtido`) | `module_pedidos.md` — Opción 4 |

### 2.5 Módulo Inventario

| Pantalla | Tipo | Spec |
|---|---|---|
| Modal menú Inventario | Modal (menú de opciones) | `module_inventario.md` |
| Agregar Producto | Modal (formulario) | `module_inventario.md` — Opción 1 |
| Cambiar Estatus | Modal (búsqueda + transiciones válidas) | `module_inventario.md` — Opción 2 |
| Consulta Inventario | Página (`/inventario/consulta`) | `module_inventario.md` — Opción 3 |
| Aplicar Descuento Masivo | Modal (filtro/selección + valor) | `module_inventario.md` — Opción 4 |
| Retirar Descuento Masivo | Modal (filtro/selección) | `module_inventario.md` — Opción 5 |

### 2.6 Módulo Shein

| Pantalla | Tipo | Spec |
|---|---|---|
| Modal menú Shein | Modal (menú de opciones) | `module_shein.md` |
| Registrar Cliente Shein | Modal (formulario) | `module_shein.md` — Opción 1 |
| Registrar Pedido Shein | Modal (búsqueda + formulario multi-artículo) | `module_shein.md` — Opción 2 |
| Lista de Pedidos Shein | Página (`/shein/pedidos`) | `module_shein.md` — Opción 3 |
| Registrar Corte | Página o modal grande (`/shein/registrar-corte`) | `module_shein.md` — Opción 4 |
| Consulta de Cortes | Página (`/shein/cortes`) | `module_shein.md` — Opción 5 |

> **Nota sobre Registrar Corte:** el flujo de 10 pasos con tabla seleccionable,
> expansión por artículo, resolución de variación de precios, captura de
> `total_ticket` y cálculo de `cupon` es demasiado complejo para un modal
> estándar. **[Recomendación]** implementar como página completa.

### 2.7 Módulo Recargas

| Pantalla | Tipo | Spec |
|---|---|---|
| Registro de Recarga | Modal (formulario directo, sin menú intermedio) | `module_recargas.md` |

> Excepción: el botón `Recargas` en `main_menu` abre directamente la ventana de
> registro, sin modal de menú de opciones.

### 2.8 Módulo Setting

| Pantalla | Tipo | Spec |
|---|---|---|
| Modal Setting | Modal (secciones: Usuarios, Info sistema, Métodos de pago) | `module_setting.md` |
| Agregar Usuario | Sub-modal o sección inline | `module_setting.md` |
| Cambiar Contraseña | Sub-modal o sección inline | `module_setting.md` |
| Cambiar Rol | Sub-modal o sección inline | `module_setting.md` |

### 2.9 Módulo Consulta Global

**[Inferido]** — no existe `module_consulta.md` en el filesystem (ver §5).
Diseñado a partir de `REGLAS_NEGOCIO.md` §10.

| Pantalla | Tipo | Spec |
|---|---|---|
| Consulta Global | Página (`/consulta-global`) | `REGLAS_NEGOCIO.md` §10 |

**Tres sub-vistas dentro de la misma página (tabs o secciones):**

#### Vista 1 — Ventas totales por período

- Filtro: rango de fechas (`fecha_inicio`, `fecha_fin`).
- Tabla: filas por `operacion` (`contado`, `apartado`, `abono`), excluyendo `gasto`.
- Columnas: operación, cantidad de movimientos, suma de montos.
- Fila de total consolidado.
- **[Inferido]** Posibilidad de incluir gastos en sección separada o como fila
  diferenciada (salida de caja vs. ingreso).

> Fuente: `REGLAS_NEGOCIO.md` §10 punto 1.

#### Vista 2 — Ventas por segmento

- Filtro: rango de fechas.
- Distribución entre:
  - **Caja** — suma de `movimientos` (excluyendo `gasto`).
  - **Shein** — suma de `shein_cortes.suma_pedidos` (o `total_ticket`; depende
    de qué métrica se prefiera — documentar como hueco en §5).
  - **Recargas** — suma de `recargas.monto`.
- **[Inferido]** Presentación: tarjetas resumen + gráfico de barras o donut.

> Fuente: `REGLAS_NEGOCIO.md` §10 punto 2.

#### Vista 3 — Cartera de clientes por segmento

- Sin filtro de fecha (es el estado actual de la cartera).
- Agrupación por `colonia`.
- Columnas: colonia, cantidad de clientes con `saldo > 0`, saldo total, saldo
  promedio.
- **[Inferido]** Fila de total general.

> Fuente: `REGLAS_NEGOCIO.md` §10 punto 3.

---

## 3. Piezas transversales a construir una sola vez

Antes de tocar cualquier módulo, se construyen estas piezas compartidas.

### 3.1 Manejo de sesión / JWT

**Fuente:** `ARQUITECTURA.md` §5, `module_setting.md` — Autenticación.

- Login: `POST /api/v1/auth/login` con `OAuth2PasswordRequestForm` → recibe
  `{ access_token, token_type }`.
- Almacenamiento del token: en memoria (React state/context). Si se elige
  `localStorage` para persistir entre recargas, documentar la decisión.
- Inyección: header `Authorization: Bearer <token>` en toda request al backend.
- **Manejo de 401:** cualquier respuesta 401 del backend debe:
  1. Limpiar el token almacenado.
  2. Redirigir a `/login`.
  3. Mostrar mensaje genérico (`"Sesión expirada. Inicia sesión de nuevo."`).
- **Ruta protegida:** todas las rutas excepto `/login` requieren token válido.
  Implementar como wrapper de ruta (`ProtectedRoute` o similar).

> **Fuente de contrato:** `REPORT.md` §4.1 — `app/api/v1/endpoints/auth.py`:
> `POST /auth/login` retorna `Token`. Mismo status/mensaje para usuario
> inexistente y password incorrecto (seguridad).

### 3.2 Cliente API

**[Recomendación]** Archivo `src/api/client.ts`:

```typescript
// Pseudocódigo de estructura — no es código final
const API_BASE = '/api/v1';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  // Inyecta Bearer token
  // Maneja 401 → logout
  // Parsea JSON
  // Tipado genérico de respuesta
}
```

Archivos de servicio por módulo (`src/api/clientes.ts`, `src/api/inventario.ts`,
etc.) que exponen funciones tipadas:

```typescript
// src/api/clientes.ts
export const crearCliente = (data: ClienteCreate) => apiFetch<Cliente>('/clientes', { method: 'POST', body: ... });
export const listarClientes = () => apiFetch<ClienteResumen[]>('/clientes');
```

### 3.3 Componente de banderas de color

**Fuente:** `module_clientes.md` — Sistema de banderas, `REGLAS_NEGOCIO.md` §2
regla 3.

| Bandera | Indicador visual | Condición |
|---|---|---|
| 🟡 Amarilla | Próximo a vencer | `fecha_pago_programada - hoy <= 2 días` |
| 🔴 Roja | Vencido | `hoy > fecha_pago_programada` |
| 🟠 Naranja | Apartado por vencer | Apartado abierto a ≤ 5 días de cumplir 1 mes |
| Sin bandera | Normal | Ninguna condición, o `fecha_pago_programada = NULL`, o `saldo = 0` |

Componente reutilizable `<BanderaCliente>` que recibe los datos del cliente y
calcula qué bandera(s) mostrar. La naranja puede coexistir con amarilla o roja.

> El backend ya calcula `bandera_naranja: bool` en `ClienteRead` (`REPORT.md`
> §4.1). Las banderas amarilla y roja se pueden calcular en frontend (comparación
> de fechas) o solicitar al backend. **[Recomendación]** calcular amarilla/roja en
> frontend (evita un campo más en el schema del backend; la lógica es trivial:
> comparar `fecha_pago_programada` con la fecha actual del cliente).

### 3.4 Formato de fecha y moneda

**Fuente:** `REGLAS_NEGOCIO.md` §11 — invariante global.

- **Fechas:** el backend almacena `YYYY-MM-DD`. La UI muestra `DD-MM-YYYY`.
  Función utilitaria `formatDate(isoDate: string): string` y su inversa
  `parseDate(displayDate: string): string` para enviar al backend.
- **Moneda:** valores monetarios se muestran con formato `$1,234.00` (pesos
  mexicanos, 2 decimales). Función `formatCurrency(amount: number): string`.
- **Timestamps:** `movimientos.fecha` y `recargas.fecha` son `YYYY-MM-DD HH:MM:SS`.
  La UI debe mostrar fecha y hora separadas si la pantalla lo requiere.

### 3.5 Patrón de validación de formularios

**Fuente:** decisión del `ROADMAP_FRONTEND.md` (prompt) — "espejear reglas del
backend para UX, sin duplicar lógica de negocio en el cliente".

**Principio:** la validación del frontend es **solo UX** — feedback inmediato
antes de enviar. La validación de verdad vive en el backend. Si el backend
rechaza una request, el frontend muestra el error del backend al usuario.

**Lo que sí se valida en frontend:**
- Campos requeridos (marcados en cada `module_*.md`).
- Longitudes máximas (`nombre`: 40, `colonia`: 20, `telefono`: 10 dígitos, etc.).
- Enums (opciones válidas de `select`).
- Condicionales de visibilidad (ej. `dia_pago_especifico` solo si
  `frecuencia_pago = dia_especifico_mes`).
- Formatos (teléfono: exactamente 10 dígitos numéricos).

**Lo que NO se valida en frontend:**
- Unicidad (`no_cliente` duplicado — eso lo valida el backend con la DB).
- Reglas de negocio complejas (ej. "solo un apartado abierto por cliente",
  "monto primer pago >= $100" — se valida en frontend como UX pero el backend
  es la autoridad final).
- Transiciones de estatus (las decide el backend).

### 3.6 Layout principal

**[Inferido]** de la estructura descrita en los `module_*.md`:

```
┌──────────────────────────────────────────────┐
│  Header: logo/nombre del negocio  │  ⚙️      │
├──────────────────────────────────────────────┤
│                                              │
│  Panel Principal (formulario de caja)        │
│  [Contado] [Apartado] [Abono] [Gasto]        │
│  + campos condicionales                      │
│                                              │
├──────────────────────────────────────────────┤
│  main_menu: botones de módulo                │
│  [Clientes] [Pedidos] [Inventario]           │
│  [Shein] [Recargas] [Consulta Global]        │
└──────────────────────────────────────────────┘
```

Las páginas completas (consultas) reemplazan el contenido central, con un botón
de regreso al Panel Principal.

---

## 4. Orden de construcción sugerido

### Fase 0 — Scaffolding (una sesión)

**Qué:** Inicializar proyecto Vite + React + TypeScript. Configurar estructura
de carpetas, instalar dependencias (react-router, react-hook-form, zod,
@tanstack/react-query). Crear el cliente API, las utilidades de formato,
el `AuthContext` y la ruta protegida. Pantalla de Login funcional.

**Por qué primero:** sin auth funcional no se puede probar ningún endpoint.
Además, establece la base técnica para todo lo que sigue.

**Entregable:** `/login` funcional, token en memoria, redirect a `/` en éxito,
layout principal vacío con `main_menu` placeholder.

---

### Fase 1 — Panel Principal + Movimientos (2-3 sesiones)

**Qué:** Construir la pantalla home con los 4 radio buttons de operación y la
lógica condicional de campos. Implementar `Contado` y `Gasto` primero (no
requieren búsqueda de cliente ni lotes). Luego `Abono` (requiere búsqueda de
cliente, impacta saldo). Finalmente `Apartado` (cabecera-detalle, N artículos,
lookup en inventario, primer pago mínimo).

**Por qué primero:** es la pantalla de uso diario. La operadora vive aquí.
Además, `movimientos` es la tabla que alimenta Consulta Global — validar que
los movimientos se registren correctamente es prerequisito para cualquier
consulta posterior. Los endpoints ya existen y tienen test en verde
(`REPORT.md` §4.1 — `POST /movimientos`, `DELETE /movimientos/{id}/cancelar`).

**Dependencias:** requiere que el componente de búsqueda de cliente funcione
(para `Apartado` y `Abono`), lo cual se construye como pieza reutilizable en
esta fase.

**Entregable:** las 4 operaciones funcionales end-to-end. Cancelar movimiento
funcional.

---

### Fase 2 — Clientes (1-2 sesiones)

**Qué:** Modal de menú + las 4 opciones. `Registrar Cliente` (formulario con
campos condicionales de `frecuencia_pago`). `Editar Cliente` (búsqueda +
formulario precargado). `Consulta Cliente` (tabla completa, filtrable).
`Consulta Historial` (búsqueda → encabezado + tabla consolidada).

**Por qué aquí:** Panel Principal ya necesita buscar clientes (Fase 1).
Construir el módulo Clientes completo en Fase 2 permite: (a) reutilizar el
componente de búsqueda de cliente ya creado, (b) tener la tabla de clientes
funcional para poder verificar las banderas de color, (c) dar a la operadora
la capacidad de registrar clientes nuevos antes de mover Pedidos o Inventario.

**Entregable:** las 4 opciones funcionales. Banderas de color visibles en
Consulta Cliente y Panel Principal.

---

### Fase 3 — Inventario (1-2 sesiones)

**Qué:** Modal de menú + 5 opciones. `Agregar Producto`. `Cambiar Estatus`
(con transiciones válidas dinámicas). `Consulta Inventario` (tabla con filtros
y agregados). `Descuento Masivo` (dos modos de segmento, dos modos de valor).
`Retirar Descuento Masivo`.

**Por qué aquí:** el Panel Principal ya referencia `inventario` en `Contado`
(lookup de `id_producto`) y `Apartado` (cambio de estatus a `apartado`). Tener
Inventario completo permite verificar end-to-end que los cambios de estatus
desde el Panel Principal se reflejan correctamente.

**Entregable:** las 5 opciones funcionales. Carga desde `.ods` (si hay
endpoint, o dejar como nota para script).

---

### Fase 4 — Pedidos (2-3 sesiones)

**Qué:** Modal de menú + 4 opciones. `Registrar Pedido` (formulario
multi-artículo con principal + alternativas, lookup de precio). `Registrar
Devolución` (selección de artículo `en_almacen` → marca `devuelto` → abre
formulario sustituto pre-cargado). `Cancelar Artículo`. `Lista de Surtido`
(tabla con periodo de corte, acción de marcar `en_almacen`).

**Por qué aquí:** es el módulo más complejo en lógica de formularios
(alternativas, lookup de precios, artículo sustituto). Se beneficia de tener
Clientes e Inventario ya funcionales. La Lista de Surtido es la pantalla
donde la operadora marca artículos como `en_almacen`, lo cual impacta el saldo
del cliente — cadena que ya fue probada en fases anteriores.

**Entregable:** las 4 opciones funcionales. Ciclo completo de
registrar → surtir → devolver → sustituir verificado.

---

### Fase 5 — Shein (2-3 sesiones)

**Qué:** Modal de menú + 5 opciones. `Registrar Cliente Shein` (formulario
simple). `Registrar Pedido Shein` (búsqueda cliente + 1-4 artículos, sin
alternativa). `Lista de Pedidos` (tabla expandible). `Registrar Corte` (flujo
de 10 pasos — la pantalla más compleja del sistema). `Consulta de Cortes`
(resumen + lista expandible con acción "Marcar pagado").

**Por qué aquí:** Shein es un módulo aislado (no comparte clientes ni
inventario). Se deja después de Pedidos para reutilizar la experiencia de
construir formularios multi-artículo. Registrar Corte es la pantalla de mayor
complejidad de toda la aplicación.

**Entregable:** las 5 opciones funcionales. Ciclo pedido → corte → pago
verificado.

---

### Fase 6 — Recargas + Setting (1 sesión)

**Qué:**
- **Recargas:** formulario directo (2 campos: compañía, monto) + resumen del
  día al pie.
- **Setting:** modal con secciones (Usuarios, Info sistema, Métodos de pago).
  Agregar usuario, cambiar contraseña, cambiar rol. Toggles de métodos de pago.
  Campos de CLABE.

**Por qué aquí:** son módulos simples, sin dependencias de otros módulos. Se
juntan en una sola fase para no dedicar sesiones individuales.

**Entregable:** ambos módulos funcionales.

---

### Fase 7 — Consulta Global (1 sesión)

**Qué:** página con 3 vistas (tabs o secciones). Implementar las consultas
agregadas de `REGLAS_NEGOCIO.md` §10.

**Por qué al final:** requiere que todos los demás módulos estén alimentando
datos para que las consultas tengan sentido. Además, los endpoints de Consulta
Global aún no existen en el backend (`REPORT.md` §4.3 — punto 16 pendiente),
por lo que la implementación frontend puede ir en paralelo con la del backend
o esperar a que este esté listo.

**Entregable:** las 3 vistas funcionales con filtros de fecha.

---

### Fase 8 — Pulido y carga inicial (1 sesión)

**Qué:**
- Carga inicial de cartera (`importar_clientes.py` — `module_clientes.md`).
- Carga inicial de inventario (`inventario_bz.ods` — `module_inventario.md`).
- Carga de `tabla_precios.ods` (ya existe script, `REPORT.md` §4.1).
- Ajustes de UX tras pruebas con la operadora.
- Responsive (el sistema corre en una sola máquina, pero el tamaño de pantalla
  puede variar).

---

## 5. Huecos y puntos que requieren confirmación

### 5.1 `module_consulta.md` — discrepancia entre REPORT.md y filesystem

`REPORT.md` §4.3 dice: *"Consulta Global — `module_consulta.md` — completa"*.
Sin embargo, `module_consulta.md` **no existe** en `docs/FULLSTACK/`. El
`README.md` de FULLSTACK lista el archivo pero marca Código y Test como `❌`.

**Impacto:** la spec de Consulta Global se tomó exclusivamente de
`REGLAS_NEGOCIO.md` §10 (3 consultas de solo lectura). Si existe un
`module_consulta.md` con spec más detallada que no fue comiteado, se necesita
antes de implementar la Fase 7.

**Acción requerida:** confirmar si `module_consulta.md` existe en algún lado
o si `REGLAS_NEGOCIO.md` §10 es la spec definitiva.

### 5.2 Endpoints de Consulta Global

`REPORT.md` §5 punto 16: *"Construir Consulta Global (3 vistas de solo
lectura)"* — pendiente en backend. El frontend puede construir la UI con datos
mock, pero necesita los endpoints reales antes de ir a producción.

**Acción requerida:** confirmar si el backend de Consulta Global se construirá
antes o en paralelo con el frontend.

### 5.3 Endpoint de Apartado

`REPORT.md` §4.1 señala: *"No expone `crear_apartado()` — no hay endpoint para
registrar un apartado todavía, solo capa de servicio (`app/api/v1/endpoints/
apartados.py` sigue sin existir)"*.

**Impacto:** el Panel Principal necesita este endpoint para la operación
`Apartado`. La capa de servicio ya está lista (`crear_apartado()`,
`obtener_apartado_abierto()`, `cancelar_articulo_apartado()` en
`movimiento_service.py`) — solo falta el router/endpoint.

**Acción requerida:** crear el endpoint antes de la Fase 1 o durante ella.

### 5.4 Endpoint de Consulta Historial

`module_clientes.md` — Opción 4 define la Consulta Historial con tabla
consolidada (pedidos + movimientos). No hay evidencia en `REPORT.md` de un
endpoint `GET /clientes/{id}/historial` ni similar.

**Acción requerida:** verificar si existe o crearlo antes de la Fase 2.

### 5.5 Endpoint de Lista de Surtido

`module_pedidos.md` — Opción 4 define la Lista de Surtido con filtro de
periodo de corte y acción de marcar `en_almacen`. Verificar que el endpoint
`GET /pedidos/surtido` o equivalente exista con los filtros necesarios.

### 5.6 Color de marca / identidad visual

Ningún documento del repo describe el color de marca, el logo, la paleta de
colores ni la tipografía del negocio. Esto impacta directamente la construcción
del layout y los componentes de UI.

**Acción requerida:** definir paleta de colores, tipografía y si existe un
logo antes de la Fase 0.

### 5.7 Ventas por segmento — métrica de Shein

`REGLAS_NEGOCIO.md` §10 punto 2 menciona "distribución entre Caja, Shein y
Recargas". No está claro si la métrica de Shein debe ser `suma_pedidos` (lo que
pagaron los clientes) o `total_ticket` (lo que la tienda pagó en OXXO).

**Acción requerida:** definir la métrica antes de implementar Vista 2 de
Consulta Global.

### 5.8 Carga desde `.ods` — ¿frontend o terminal?

`module_inventario.md` describe la carga desde `inventario_bz.ods` como
funcionalidad del sistema. `module_pedidos.md` describe `importar_precios.py`
como script de terminal. No queda claro si alguna carga desde `.ods` debe
tener UI en el frontend (botón de upload + progreso) o si todas se ejecutan
por terminal.

**Acción requerida:** confirmar si se necesita UI de importación o si todos
los scripts de carga se ejecutan por terminal.

### 5.9 Formato de `forma_pago` — enum extendido

`module_setting.md` describe 6 métodos de pago configurables (efectivo,
transferencia, tarjeta débito, tarjeta crédito, MSI, vales), pero
`movimientos.forma_pago` solo tiene 3 valores: `efectivo`, `transferencia`,
`tarjeta`. Confirmar si el enum de `forma_pago` se extenderá para acomodar
los 6 métodos o si `tarjeta` cubre débito/crédito/MSI.

### 5.10 `cancelar_movimiento` en UI — ¿desde dónde?

`REPORT.md` documenta `DELETE /movimientos/{id}/cancelar`. La spec de UI en
`module_movimientos.md` no describe explícitamente desde qué pantalla la
operadora cancela un movimiento. **[Inferido]** probablemente un botón en el
Panel Principal que cancela el último movimiento registrado, o una acción desde
la Consulta Historial.

**Acción requerida:** definir el flujo de UI para cancelar movimiento.

---

## Resumen de estructura de carpetas sugerida

**[Recomendación]** — punto de partida, no obligación.

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── src/
│   ├── main.tsx                    # Entry point
│   ├── App.tsx                     # Router setup
│   ├── api/
│   │   ├── client.ts              # Fetch wrapper + auth
│   │   ├── clientes.ts            # Funciones tipadas por módulo
│   │   ├── inventario.ts
│   │   ├── pedidos.ts
│   │   ├── movimientos.ts
│   │   ├── shein.ts
│   │   ├── recargas.ts
│   │   ├── setting.ts
│   │   └── auth.ts
│   ├── components/
│   │   ├── ui/                    # Primitivos reutilizables
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Badge.tsx          # Banderas de color
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── MainLayout.tsx
│   │   │   ├── Header.tsx
│   │   │   └── MainMenu.tsx
│   │   └── shared/
│   │       ├── ClienteSearch.tsx   # Búsqueda de cliente reutilizable
│   │       ├── BanderaCliente.tsx
│   │       └── ...
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── PanelPrincipal.tsx
│   │   ├── clientes/
│   │   │   ├── ConsultaCliente.tsx
│   │   │   └── ConsultaHistorial.tsx
│   │   ├── inventario/
│   │   │   └── ConsultaInventario.tsx
│   │   ├── pedidos/
│   │   │   └── ListaSurtido.tsx
│   │   ├── shein/
│   │   │   ├── ListaPedidos.tsx
│   │   │   ├── RegistrarCorte.tsx
│   │   │   └── ConsultaCortes.tsx
│   │   └── consulta-global/
│   │       └── ConsultaGlobal.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── ...
│   ├── context/
│   │   └── AuthContext.tsx
│   ├── utils/
│   │   ├── format.ts              # formatDate, formatCurrency
│   │   └── validation.ts          # Schemas Zod compartidos
│   ├── types/
│   │   └── index.ts               # Tipos TypeScript (espejan schemas del backend)
│   └── styles/
│       ├── index.css              # Variables CSS, reset, sistema de diseño
│       └── ...
```

---

> **Siguiente paso inmediato:** confirmar los huecos de §5 (especialmente 5.1,
> 5.3 y 5.6) y arrancar con la Fase 0 — scaffolding del proyecto.
