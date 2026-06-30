# MAIN MENU — pos-boutique

> Especificación completa de UI/UX del `main_panel_multiventana`.
> Documenta módulo por módulo el flujo de navegación, modelo de datos, schemas JSON y reglas de negocio reflejadas en interfaz.
> Este documento tiene precedencia sobre `README.md`, `ARQUITECTURA.md` y `REGLAS_NEGOCIO.md` cuando haya contradicción.

---

## Tabla de contenidos

- [MAIN MENU — pos-boutique](#main-menu--pos-boutique)
  - [Tabla de contenidos](#tabla-de-contenidos)
  - [Módulo Clientes](#módulo-clientes)
    - [Modelo de datos](#modelo-de-datos)
    - [Notas de campo](#notas-de-campo)
    - [Enum `frecuencia_pago`](#enum-frecuencia_pago)
    - [Enum `estatus`](#enum-estatus)
    - [Ciclo de `fecha_pago_programada`](#ciclo-de-fecha_pago_programada)
    - [Sistema de banderas](#sistema-de-banderas)
    - [Menú Clientes](#menú-clientes)
    - [Opción 1 — Registrar Cliente](#opción-1--registrar-cliente)
    - [Opción 2 — Editar Cliente](#opción-2--editar-cliente)
    - [Opción 3 — Consulta Cliente](#opción-3--consulta-cliente)
    - [Opción 4 — Consulta Historial](#opción-4--consulta-historial)
    - [Schema JSON completo — Clientes](#schema-json-completo--clientes)
    - [Carga inicial de cartera existente](#carga-inicial-de-cartera-existente)
  - [Módulo Pedidos](#módulo-pedidos)
    - [Convención de identidades](#convención-de-identidades)
    - [Modelo de datos — Pedidos](#modelo-de-datos--pedidos)
      - [Tabla `pedidos` (cabecera)](#tabla-pedidos-cabecera)
      - [Tabla `pedidos_articulos` (líneas)](#tabla-pedidos_articulos-líneas)
      - [Notas de campo](#notas-de-campo-1)
      - [Enum `tipo_producto`](#enum-tipo_producto)
      - [Enum `proveedor`](#enum-proveedor)
      - [Enum `estatus_articulo`](#enum-estatus_articulo)
      - [Resolución de `monto` desde `tabla_precios`](#resolución-de-monto-desde-tabla_precios)
      - [Regla de saldo](#regla-de-saldo)
    - [Menú Pedidos](#menú-pedidos)
      - [Opción 1 — Registrar Pedido](#opción-1--registrar-pedido)
      - [Opción 2 — Registrar Devolución](#opción-2--registrar-devolución)
      - [Opción 3 — Cancelar Artículo](#opción-3--cancelar-artículo)
      - [Opción 4 — Lista de Surtido](#opción-4--lista-de-surtido)
    - [Formulario Registrar Pedido](#formulario-registrar-pedido)
    - [Flujo de una devolución](#flujo-de-una-devolución)
    - [Flujo de una cancelación](#flujo-de-una-cancelación)
    - [Schema JSON completo — Pedidos](#schema-json-completo--pedidos)
  - [Módulo Inventario](#módulo-inventario)
    - [Modelo de datos — Inventario](#modelo-de-datos--inventario)
    - [Notas de campo — Inventario](#notas-de-campo--inventario)
    - [Enum `categoria`](#enum-categoria)
    - [Enum `estatus` (inventario)](#enum-estatus-inventario)
    - [Regla de `precio_descuento`](#regla-de-precio_descuento)
    - [Menú Inventario](#menú-inventario)
      - [Opción 1 — Agregar Producto](#opción-1--agregar-producto)
      - [Opción 2 — Cambiar Estatus](#opción-2--cambiar-estatus)
      - [Opción 3 — Consulta Inventario](#opción-3--consulta-inventario)
    - [Schema JSON completo — Inventario](#schema-json-completo--inventario)
  - [Panel Principal — Main Panel](#panel-principal--main-panel)
    - [Tabla `movimientos`](#tabla-movimientos)
    - [Módulo Apartado](#módulo-apartado)
      - [Estatus `apartado` en `inventario`](#estatus-apartado-en-inventario)
      - [Ciclo de vida de un Apartado](#ciclo-de-vida-de-un-apartado)
      - [Reglas del Apartado](#reglas-del-apartado)
    - [Diseño de pantalla](#diseño-de-pantalla)
    - [Campos activos por operación](#campos-activos-por-operación)
    - [Comportamiento por operación](#comportamiento-por-operación)
      - [Contado](#contado)
      - [Apartado](#apartado)
      - [Abono](#abono)
      - [Gasto](#gasto)
    - [Schema JSON — Panel Principal](#schema-json--panel-principal)
  - [Módulo Shein](#módulo-shein)
    - [Decisiones de diseño — Shein](#decisiones-de-diseño--shein)
    - [Modelo de datos — Shein](#modelo-de-datos--shein)
      - [Tabla `shein_clientes`](#tabla-shein_clientes)
      - [Tabla `shein_pedidos`](#tabla-shein_pedidos)
      - [Tabla `shein_cortes`](#tabla-shein_cortes)
    - [Menú Shein](#menú-shein)
      - [Opción 1 — Registrar Cliente Shein](#opción-1--registrar-cliente-shein)
      - [Opción 2 — Registrar Pedido Shein](#opción-2--registrar-pedido-shein)
      - [Opción 3 — Lista de Pedidos](#opción-3--lista-de-pedidos)
      - [Opción 4 — Registrar Corte](#opción-4--registrar-corte)
    - [Cuello de botella — Variación de precios en app Shein](#cuello-de-botella--variación-de-precios-en-app-shein)
  - [Módulo Recargas Telefónicas](#módulo-recargas-telefónicas)
    - [Modelo de datos — Recargas](#modelo-de-datos--recargas)
    - [Menú Recargas](#menú-recargas)
      - [Ventana — Registro de Recarga Telefónica](#ventana--registro-de-recarga-telefónica)
  - [Módulo Consulta Global](#módulo-consulta-global)
    - [Consulta 1 — Ventas totales por período](#consulta-1--ventas-totales-por-período)
    - [Consulta 2 — Ventas por segmento en período](#consulta-2--ventas-por-segmento-en-período)
    - [Consulta 3 — Cartera de clientes por segmento](#consulta-3--cartera-de-clientes-por-segmento)
  - [Autenticación y Configuración](#autenticación-y-configuración)
    - [Autenticación](#autenticación)
    - [Módulo Setting](#módulo-setting)
      - [Opciones disponibles](#opciones-disponibles)
  - [Resumen de tablas del sistema](#resumen-de-tablas-del-sistema)

---

## Módulo Clientes

---

### Modelo de datos

La tabla `clientes` se extiende respecto al modelo base definido en `REGLAS_NEGOCIO.md`
con los campos nuevos documentados aquí.

```sql
CREATE TABLE clientes (
    id_cliente             INTEGER PRIMARY KEY AUTOINCREMENT,
    no_cliente             TEXT    NOT NULL UNIQUE,   -- Autogenerado: {Colonia}-{consecutivo:03d}
    nombre                 TEXT    NOT NULL,
    colonia                TEXT    NOT NULL,
    telefono               INTEGER NOT NULL,          -- 10 dígitos, obligatorio
    frecuencia_pago        TEXT    NOT NULL,          -- Enum: semanal | quincenal | dia_especifico_mes | otro
    ref_nombre             TEXT    NOT NULL,
    ref_colonia            TEXT    NOT NULL,
    ref_telefono           INTEGER,                   -- 10 dígitos, nullable
    saldo                  REAL    NOT NULL DEFAULT 0,
    estatus                TEXT    NOT NULL DEFAULT 'activo'
                               CHECK (estatus IN ('activo', 'inactivo')),
    fecha_registro         TEXT    NOT NULL,          -- ISO 8601: YYYY-MM-DD
    fecha_pago_programada  TEXT                       -- ISO 8601: YYYY-MM-DD. NULL hasta el primer abono.
);
```

---

### Notas de campo

| Campo                   | Nota                                                                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `no_cliente`            | Lo genera el sistema: `{colonia}-{consecutivo:03d}`. La operadora no lo captura. Ej: `Carrillos-001`.                                                  |
| `telefono`              | Tipo `INTEGER`, 10 dígitos. Obligatorio.                                                                                                               |
| `frecuencia_pago`       | Enum. Define la periodicidad esperada de abono del cliente.                                                                                            |
| `ref_telefono`          | Nullable. El teléfono del garante es opcional.                                                                                                         |
| `saldo`                 | Deuda acumulada del cliente. `saldo > 0` = deuda activa. `saldo = 0` = cuenta al corriente o liquidada.                                                |
| `estatus`               | Enum `activo` \| `inactivo`. Se cambia manualmente por la operadora. `saldo = 0` no implica baja automática — el cliente puede estar activo sin deuda. |
| `fecha_registro`        | Se guarda en `YYYY-MM-DD` (ISO 8601). Se muestra en UI como `DD-MM-YYYY`.                                                                              |
| `fecha_pago_programada` | `NULL` al registrar. Campo calculado internamente: se instancia y recalcula en cada abono en `movimientos`. Nunca se captura ni importa manualmente.   |

---

### Enum `frecuencia_pago`

| Valor                | Descripción                              |
| -------------------- | ---------------------------------------- |
| `semanal`            | Pago esperado cada 7 días                |
| `quincenal`          | Pago esperado cada 15 días               |
| `dia_especifico_mes` | Pago esperado en un día fijo del mes     |
| `otro`               | Acuerdo especial; sin cálculo automático |

---

### Enum `estatus`

| Valor      | Descripción                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------- |
| `activo`   | Cliente en operación. Puede tener saldo o estar al corriente. Default al registrar.         |
| `inactivo` | Cuenta cerrada o dada de baja. La operadora lo asigna manualmente desde **Editar Cliente**. |

> `saldo = 0` no provoca baja automática. Un cliente puede tener `saldo = 0` y estar
> `activo` porque acaba de liquidar y se espera un pedido nuevo, o porque aún no tiene
> pedidos. El cambio a `inactivo` es siempre una decisión operativa explícita.

---

### Ciclo de `fecha_pago_programada`

`fecha_pago_programada` es una fecha rodante. No se fija al registrar al cliente —
se instancia y recalcula en cada abono.

**Reglas:**

1. Al registrar el cliente: `fecha_pago_programada = NULL`.
2. Al registrar el **primer abono** en `movimientos`: el backend asigna `fecha_pago_programada = fecha_abono + frecuencia_pago`.
3. En cada abono subsiguiente: `fecha_pago_programada = fecha_abono_actual + frecuencia_pago`.
4. Si `frecuencia_pago = otro`: el backend no calcula. `fecha_pago_programada` permanece `NULL`.

**Ejemplo con `frecuencia_pago = quincenal`:**

```
Abono 1: 03-01-2026  →  fecha_pago_programada = 18-01-2026
Abono 2: 25-01-2026  →  fecha_pago_programada = 09-02-2026
Abono 3: 10-02-2026  →  fecha_pago_programada = 25-02-2026
```

> El sistema no castiga el retraso. La próxima fecha siempre se recalcula desde
> el abono real, no desde la fecha programada anterior.

---

### Sistema de banderas

El sistema evalúa `fecha_pago_programada` de cada cliente activo con saldo para
determinar alertas visuales.

| Bandera     | Condición                                                   | Indicador        |
| ----------- | ----------------------------------------------------------- | ---------------- |
| 🟡 Amarilla  | `fecha_pago_programada - hoy <= 2 días`                     | Próximo a vencer |
| 🔴 Roja      | `hoy > fecha_pago_programada`                               | Vencido          |
| Sin bandera | Ninguna de las anteriores, o `fecha_pago_programada = NULL` | Normal           |

**Notas de implementación:**

- La evaluación se ejecuta al cargar el panel principal o el módulo Clientes.
- Clientes con `frecuencia_pago = otro` y `fecha_pago_programada = NULL` no generan bandera.
- Clientes con `saldo = 0` no generan bandera aunque tengan `fecha_pago_programada` definida.
- La bandera es visual — no bloquea operaciones.

---

### Menú Clientes

El botón `Clientes` en el `main_menu` abre una ventana emergente con cuatro opciones.

```yaml
titulo_ventana: Clientes
opciones:
  1: Registrar Cliente
  2: Editar Cliente
  3: Consulta Cliente
  4: Consulta Historial
```

---

### Opción 1 — Registrar Cliente

Formulario de alta de nuevo cliente. Escribe en tabla `clientes`.

**Campos capturados por la operadora:**

| Etiqueta            | Modelo            | Tipo          | Longitud | Requerido |
| ------------------- | ----------------- | ------------- | -------- | --------- |
| Nombre              | `nombre`          | String        | 40       | ✅         |
| Colonia             | `colonia`         | String        | 20       | ✅         |
| Teléfono            | `telefono`        | Integer       | 10       | ✅         |
| Frecuencia de Pago  | `frecuencia_pago` | Enum / select | —        | ✅         |
| Referencia Nombre   | `ref_nombre`      | String        | 40       | ✅         |
| Referencia Colonia  | `ref_colonia`     | String        | 40       | ✅         |
| Referencia Teléfono | `ref_telefono`    | Integer       | 10       | ❌         |

**Campos autogenerados por el sistema al guardar:**

| Columna                 | Estrategia                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------------- |
| `no_cliente`            | `{colonia}-{consecutivo:03d}`. El backend consulta `COUNT` de clientes con esa colonia y asigna el siguiente. |
| `fecha_registro`        | Fecha actual. Almacenada en `YYYY-MM-DD`, mostrada en UI como `DD-MM-YYYY`.                                   |
| `saldo`                 | Default `0`.                                                                                                  |
| `estatus`               | Default `activo`.                                                                                             |
| `fecha_pago_programada` | `NULL`. Se asigna al primer abono.                                                                            |

**Botón Guardar:**

- Ejecuta `INSERT` en tabla `clientes`.
- En éxito: `"Cliente registrado correctamente."` y limpia el formulario.
- En error: `"No se pudo guardar. Intenta de nuevo."`

---

### Opción 2 — Editar Cliente

Permite modificar el registro de un cliente existente.

**Flujo:**

1. Se abre ventana emergente con campo de búsqueda `no_cliente`.
2. Al confirmar, se abre el formulario idéntico a **Registrar Cliente** con los datos precargados.
3. La operadora edita los campos necesarios y presiona **Guardar**.
4. El sistema ejecuta `UPDATE` en tabla `clientes`.

**Notas:**

- `id_cliente` nunca se muestra ni se modifica en UI. `no_cliente` es el identificador operativo.
- Esta ventana requiere permiso `admin`. En el MVP ambos usuarios tienen rol `estandar` — la restricción se implementa en versiones futuras sin cambio de arquitectura.

---

### Opción 3 — Consulta Cliente

Abre la tabla completa de `clientes` filtrable y ordenable por la operadora.

```yaml
titulo_ventana: Consulta Cliente
tabla_fuente: clientes
carga: al_abrir_ventana
columnas_visibles:
  - no_cliente
  - nombre
  - colonia
  - telefono
  - saldo
  - estatus
```

---

### Opción 4 — Consulta Historial

Muestra el historial consolidado de un cliente: pedidos, devoluciones, cancelaciones
y abonos en una sola vista cronológica.

**Flujo:**

1. Se abre ventana con campo de búsqueda `no_cliente`.
2. Al confirmar, se carga la ventana de historial.

**Encabezado:** datos del cliente (`no_cliente`, `nombre`, `saldo`, `estatus`,
`fecha_pago_programada`).

**Tabla consolidada** (ordenada por fecha descendente):

| Columna          | Fuente / Valor                                                   |
| ---------------- | ---------------------------------------------------------------- |
| Fecha            | `pedidos.fecha` / `movimientos.fecha`                            |
| Tipo             | `"Pedido"`, `"Devolución"`, `"Cancelación"` o `"Abono"`          |
| Detalle          | Producto (pedidos/devoluciones/cancelaciones) o monto (abonos)   |
| Monto            | Con signo negativo si es devolución o cancelación con monto      |
| Estatus artículo | `vigente` / `en_almacen` / `devuelto` / `cancelado` / — (abonos) |
| Saldo resultante | Calculado acumulativamente                                       |

**Fuente de datos:**

- `pedidos_articulos` JOIN `pedidos` → artículos por cliente.
- `movimientos` WHERE `operacion IN ('apartado', 'abono')` → movimientos con efecto en saldo.

> Los abonos no están vinculados a pedidos individuales. El cliente abona a su saldo
> total. Decisión de negocio: los clientes tienen entre 1 y 3 artículos simultáneos,
> por lo que no hay ambigüedad operativa.

---

### Schema JSON completo — Clientes

```json
{
  "main_menu": {
    "botones": [
      {
        "id": "btn_clientes",
        "etiqueta": "Clientes",
        "accion": { "tipo": "abrir_modal", "modal": "modal_clientes" }
      }
    ]
  },
  "modales": [
    {
      "id": "modal_clientes",
      "titulo": "Clientes",
      "tipo": "menu_opciones",
      "opciones": [
        { "id": 1, "etiqueta": "Registrar Cliente",  "accion": { "tipo": "abrir_ventana", "ventana": "ventana_registrar_cliente"  } },
        { "id": 2, "etiqueta": "Editar Cliente",     "accion": { "tipo": "abrir_ventana", "ventana": "ventana_editar_cliente"     } },
        { "id": 3, "etiqueta": "Consulta Cliente",   "accion": { "tipo": "abrir_ventana", "ventana": "ventana_consulta_cliente"   } },
        { "id": 4, "etiqueta": "Consulta Historial", "accion": { "tipo": "abrir_ventana", "ventana": "ventana_consulta_historial" } }
      ]
    }
  ],
  "ventanas": [
    {
      "id": "ventana_registrar_cliente",
      "titulo": "Registrar Cliente",
      "apartados": [
        {
          "id": "apartado_cliente",
          "titulo": "Cliente",
          "campos": [
            { "etiqueta": "Nombre",            "tipo": "String",  "longitud": 40, "modelo": "nombre",          "requerido": true  },
            { "etiqueta": "Colonia",            "tipo": "String",  "longitud": 20, "modelo": "colonia",         "requerido": true  },
            { "etiqueta": "Teléfono",           "tipo": "Integer", "longitud": 10, "modelo": "telefono",        "requerido": true  },
            {
              "etiqueta": "Frecuencia de Pago",
              "tipo": "Enum", "modelo": "frecuencia_pago", "control": "select", "requerido": true,
              "opciones": [
                { "valor": "semanal",            "etiqueta": "Semanal"               },
                { "valor": "quincenal",          "etiqueta": "Quincenal"             },
                { "valor": "dia_especifico_mes", "etiqueta": "Día específico del mes"},
                { "valor": "otro",               "etiqueta": "Otro"                  }
              ]
            }
          ]
        },
        {
          "id": "apartado_referencia",
          "titulo": "Referencia",
          "campos": [
            { "etiqueta": "Referencia Nombre",   "tipo": "String",  "longitud": 40, "modelo": "ref_nombre",   "requerido": true  },
            { "etiqueta": "Referencia Colonia",  "tipo": "String",  "longitud": 40, "modelo": "ref_colonia",  "requerido": true  },
            { "etiqueta": "Referencia Teléfono", "tipo": "Integer", "longitud": 10, "modelo": "ref_telefono", "requerido": false }
          ]
        }
      ],
      "acciones": [
        {
          "id": "btn_guardar", "etiqueta": "Guardar", "tipo": "button", "variante": "primary", "icono": "save",
          "accion": {
            "tipo": "db_insert", "tabla": "clientes",
            "campos_autogenerados": [
              { "columna": "no_cliente",     "estrategia": "consecutivo_por_colonia", "formato": "{colonia}-{consecutivo:03d}" },
              { "columna": "fecha_registro", "estrategia": "fecha_actual", "formato_almacenamiento": "YYYY-MM-DD", "formato_display": "DD-MM-YYYY" }
            ],
            "campos_mapeados": [
              { "modelo": "nombre",          "columna": "nombre"          },
              { "modelo": "colonia",         "columna": "colonia"         },
              { "modelo": "telefono",        "columna": "telefono"        },
              { "modelo": "frecuencia_pago", "columna": "frecuencia_pago" },
              { "modelo": "ref_nombre",      "columna": "ref_nombre"      },
              { "modelo": "ref_colonia",     "columna": "ref_colonia"     },
              { "modelo": "ref_telefono",    "columna": "ref_telefono"    }
            ],
            "valores_default": [
              { "columna": "saldo",                 "valor": 0        },
              { "columna": "estatus",               "valor": "activo" },
              { "columna": "fecha_pago_programada", "valor": null     }
            ],
            "en_exito": { "mensaje": "Cliente registrado correctamente.", "limpiar_formulario": true },
            "en_error": { "mensaje": "No se pudo guardar. Intenta de nuevo." }
          }
        }
      ]
    },
    {
      "id": "ventana_editar_cliente",
      "titulo": "Editar Cliente",
      "flujo": "busqueda_previa",
      "campo_busqueda": { "etiqueta": "No. Cliente", "modelo": "no_cliente", "tipo": "String" },
      "formulario": "ventana_registrar_cliente",
      "accion_guardar": { "tipo": "db_update", "tabla": "clientes", "clave": "no_cliente" },
      "permisos": { "rol_requerido": "admin", "estado_mvp": "pendiente" }
    },
    {
      "id": "ventana_consulta_cliente",
      "titulo": "Consulta Cliente",
      "tipo": "tabla", "tabla_fuente": "clientes", "carga": "al_abrir_ventana",
      "columnas_visibles": [
        { "campo": "no_cliente", "etiqueta": "ID Cliente" },
        { "campo": "nombre",     "etiqueta": "Nombre"     },
        { "campo": "colonia",    "etiqueta": "Colonia"    },
        { "campo": "telefono",   "etiqueta": "Teléfono"   },
        { "campo": "saldo",      "etiqueta": "Saldo"      },
        { "campo": "estatus",    "etiqueta": "Estatus"    }
      ]
    },
    {
      "id": "ventana_consulta_historial",
      "titulo": "Consulta Historial",
      "flujo": "busqueda_previa",
      "campo_busqueda": { "etiqueta": "No. Cliente", "modelo": "no_cliente", "tipo": "String" },
      "contenido": {
        "encabezado": ["no_cliente", "nombre", "saldo", "estatus", "fecha_pago_programada"],
        "tabla_historial": {
          "fuentes": ["pedidos_articulos", "movimientos"],
          "filtro_movimientos": "operacion IN ('apartado', 'abono')",
          "orden": "fecha DESC",
          "columnas": [
            { "campo": "fecha",             "etiqueta": "Fecha"            },
            { "campo": "tipo",              "etiqueta": "Tipo"             },
            { "campo": "detalle",           "etiqueta": "Detalle"          },
            { "campo": "monto",             "etiqueta": "Monto"            },
            { "campo": "estatus_articulo",  "etiqueta": "Estatus"          },
            { "campo": "saldo_resultante",  "etiqueta": "Saldo resultante" }
          ]
        }
      }
    }
  ]
}
```

---

### Carga inicial de cartera existente

El negocio cuenta con clientes activos con saldo al momento de salir a producción.
No deben capturarse uno a uno en el formulario.

**Fase 1 — Antes de producción (Libre Office)**

Capturar todos los clientes en una hoja con las columnas exactas de la tabla.
`fecha_pago_programada` se omite — es un campo calculado que el script dejará en `NULL`.

```
no_cliente | nombre | colonia | telefono | frecuencia_pago | ref_nombre | ref_colonia | ref_telefono | saldo | estatus | fecha_registro
```

- `no_cliente` en formato `{Colonia}-{consecutivo:03d}`.
- `fecha_registro` en formato `YYYY-MM-DD`.
- `estatus` en minúsculas: `activo` o `inactivo`.
- Guardar como `.csv` con codificación `UTF-8`.

**Fase 2 — Primer día de producción (script)**

```bash
python scripts/importar_clientes.py --archivo cartera_inicial.csv --db pos.db
```

El script debe:
- Validar que `no_cliente` sea único antes de insertar.
- Convertir `fecha_registro` si viene en `DD-MM-YYYY`.
- Rechazar filas con `estatus` fuera de `activo | inactivo`.
- Insertar `fecha_pago_programada = NULL` para todos, ignorando cualquier valor en el CSV.
- Reportar errores por fila sin abortar la importación completa.

**Fase 3 — Operación normal**

Clientes nuevos se registran directamente en el formulario. La cartera importada
queda disponible de inmediato en Consulta Cliente y Consulta Historial.

> Importación de única vez. Una vez verificada, el script puede archivarse.

---

## Módulo Pedidos

> Corrige y extiende la tabla `pedidos` definida en `REGLAS_NEGOCIO.md`.
> La convención de identidades documentada aquí aplica a todos los módulos.

---

### Convención de identidades

Toda tabla tiene una clave primaria interna (`id_cliente`, `id_pedido`, etc.)
generada con `AUTOINCREMENT`. Este identificador **nunca aparece en UI** — es
de uso exclusivo del backend para relacionar tablas.

El identificador operativo visible es `no_cliente`. Cuando un formulario recibe
`no_cliente`, el backend resuelve internamente:

```sql
SELECT id_cliente FROM clientes WHERE no_cliente = 'Carrillos-001'
```

El número de pedido dentro del historial de un cliente es un valor **calculado**:

```sql
SELECT p.*, ROW_NUMBER() OVER (PARTITION BY p.id_cliente ORDER BY p.id_pedido) AS pedido_num
FROM pedidos p
WHERE p.id_cliente = (SELECT id_cliente FROM clientes WHERE no_cliente = 'Carrillos-001')
```

---

### Modelo de datos — Pedidos

El rediseño introduce dos tablas. La tabla original `pedidos` en `REGLAS_NEGOCIO.md`
mezclaba cabecera y artículos en una sola fila, impidiendo registrar más de un
artículo por pedido.

#### Tabla `pedidos` (cabecera)

```sql
CREATE TABLE pedidos (
    id_pedido   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente  INTEGER NOT NULL REFERENCES clientes(id_cliente),
    fecha       TEXT    NOT NULL   -- ISO 8601: YYYY-MM-DD. Autogenerado al guardar.
);
```

#### Tabla `pedidos_articulos` (líneas)

Cada pedido tiene entre 1 y 4 artículos. Principal y alternativa son filas del
mismo tipo diferenciadas por `rol`.

```sql
CREATE TABLE pedidos_articulos (
    id_articulo            INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pedido              INTEGER NOT NULL REFERENCES pedidos(id_pedido),
    rol                    TEXT    NOT NULL DEFAULT 'principal'
                               CHECK (rol IN ('principal', 'alternativa')),
    id_articulo_principal  INTEGER REFERENCES pedidos_articulos(id_articulo),
                           -- NULL cuando rol = 'principal'.
                           -- FK al renglón principal cuando rol = 'alternativa'.
    tipo_producto          TEXT    NOT NULL CHECK (tipo_producto IN ('formal', 'informal')),
    proveedor              TEXT,
                           -- Enum: Price_Shoes | Pakar | Cklass | otro
                           -- NULL cuando tipo_producto = 'informal'.
    id_producto            TEXT(12),
                           -- Referencia al catálogo del proveedor. Informativo, sin FK.
                           -- Habilitado para cualquier valor de proveedor cuando tipo_producto = 'formal'.
                           -- NULL cuando tipo_producto = 'informal'.
    producto               TEXT(40) NOT NULL,
    marca                  TEXT(20),
    talla                  TEXT(8),
    monto                  REAL,
                           -- Autollenado si proveedor tiene lista; manual si proveedor = 'otro';
                           -- libre y opcional si tipo_producto = 'informal'.
    estatus_articulo       TEXT    NOT NULL DEFAULT 'vigente'
                               CHECK (estatus_articulo IN ('vigente', 'en_almacen', 'devuelto', 'cancelado')),
    id_articulo_sustituye  INTEGER REFERENCES pedidos_articulos(id_articulo)
                           -- NULL en artículos normales y cancelaciones.
                           -- En el artículo sustituto, apunta al original devuelto.
);
```

#### Notas de campo

| Campo                   | Nota                                                                                                                                                                                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id_articulo`           | PK interna. No aparece en UI.                                                                                                                                                                                                                  |
| `id_pedido`             | FK a cabecera. No aparece en UI.                                                                                                                                                                                                               |
| `rol`                   | `principal` o `alternativa`. Reemplaza las columnas `opcion_*` del modelo anterior.                                                                                                                                                            |
| `id_articulo_principal` | FK nullable. Solo se llena cuando `rol = 'alternativa'`.                                                                                                                                                                                       |
| `tipo_producto`         | Enum. Controla qué campos se habilitan en el formulario.                                                                                                                                                                                       |
| `proveedor`             | Enum. Solo aplica si `tipo_producto = 'formal'`.                                                                                                                                                                                               |
| `id_producto`           | Referencia al ID del catálogo del proveedor. Habilitado para todos los valores de `proveedor` cuando `tipo_producto = 'formal'`. Para `Price_Shoes`, `Pakar`, `Cklass` activa el lookup de precio. Para `otro` es referencia libre sin lookup. |
| `monto`                 | Ver [Resolución de `monto` desde `tabla_precios`](#resolución-de-monto-desde-tabla_precios).                                                                                                                                                   |
| `estatus_articulo`      | Controla el ciclo de vida del artículo. Ver [Enum `estatus_articulo`](#enum-estatus_articulo).                                                                                                                                                 |
| `id_articulo_sustituye` | Solo en artículos sustitutos de una devolución. `NULL` en todos los demás casos.                                                                                                                                                               |

#### Enum `tipo_producto`

| Valor      | Descripción                                                                                                      |
| ---------- | ---------------------------------------------------------------------------------------------------------------- |
| `formal`   | Producto de catálogo de proveedor. Habilita `proveedor` e `id_producto`. `monto` se resuelve según el proveedor. |
| `informal` | Producto sin catálogo. `proveedor` e `id_producto` deshabilitados. `monto` libre y opcional.                     |

#### Enum `proveedor`

Solo aplica cuando `tipo_producto = 'formal'`.

| Valor         | `id_producto` | `monto`                                              |
| ------------- | ------------- | ---------------------------------------------------- |
| `Price_Shoes` | Habilitado    | Autollenado desde `tabla_precios` (pestaña `PS`)     |
| `Pakar`       | Habilitado    | Autollenado desde `tabla_precios` (pestaña `Pakar`)  |
| `Cklass`      | Habilitado    | Autollenado desde `tabla_precios` (pestaña `Cklass`) |
| `otro`        | Habilitado    | Captura manual, obligatorio                          |

> `otro` cubre proveedores formales con catálogo e IDs propios pero sin lista de
> precios digitalizada en el sistema. El campo `id_producto` sirve como referencia
> al catálogo del proveedor para trazabilidad operativa.

#### Enum `estatus_articulo`

| Valor        | Descripción                                                               | Efecto en saldo                              |
| ------------ | ------------------------------------------------------------------------- | -------------------------------------------- |
| `vigente`    | Pedido registrado; artículo pendiente de surtir.                          | Sin efecto. El saldo **no se carga aún**.    |
| `en_almacen` | Artículo surtido y disponible en piso. La operadora lo marca manualmente. | `saldo += monto` — se carga en este momento. |
| `devuelto`   | Cliente devolvió el artículo. Se emite pedido sustituto.                  | `saldo -= monto`                             |
| `cancelado`  | Artículo no aceptado por el cliente. Sin sustituto. Pasa a inventario.    | `saldo -= monto` si `monto IS NOT NULL`      |

> **Decisión de negocio — cuándo sube el saldo:** el saldo del cliente se incrementa
> cuando el artículo llega al piso y se marca `en_almacen`, no al registrar el pedido.
> Esto refleja la realidad operativa: solo se cobra lo que se surtió. Si un artículo
> nunca se surte (`vigente` → `cancelado`), nunca impacta el saldo.

#### Resolución de `monto` desde `tabla_precios`

El archivo `tabla_precios.ods` es la fuente de verdad operativa de precios de proveedor.
Vive fuera del repo, se mantiene en LibreOffice Calc, y se sincroniza manualmente
a SQLite mediante el script `backend/app/scripts/importar_precios.py` cada vez que
un proveedor libera catálogo nuevo (frecuencia típica: mensual o bimestral).

**Estructura del archivo — 3 pestañas:**

| Pestaña | Campo identificador | Campo precio | Campo base | Formato `fecha` |
|---|---|---|---|---|
| `price_shoes` | `ID` | `precio_venta` | `Sug_credito` | texto `"02-mayo-2026"` |
| `pakar` | `CÓDIGO` | `precio_venta` | `2 PAGO` | texto `"02-mayo-2026"` |
| `cklass` | `modelo` | `precio_venta` | `precio_base` | ISO `YYYY-MM-DD` |

El script normaliza los tres campos identificadores a la columna `id_producto` en SQLite,
y normaliza ambos formatos de fecha a ISO antes de insertar.

**Tabla `precios_catalogo` en SQLite (destino del import):**

```sql
CREATE TABLE precios_catalogo (
    id_precio      INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor      TEXT    NOT NULL CHECK (proveedor IN ('Price_Shoes', 'Pakar', 'Cklass')),
    id_producto    TEXT(12) NOT NULL,
    precio_venta   INTEGER NOT NULL,
    fecha_catalogo DATE    NOT NULL,
    -- Columnas auxiliares preservadas por fidelidad al .ods (no usadas por el POS):
    catalogo       TEXT,
    temporada      TEXT,
    pagina         INTEGER,
    precio_base    INTEGER
);
```

Sin restricción `UNIQUE` — el mismo `id_producto` puede aparecer en catálogos futuros
(producto vigente temporada tras temporada). El import solo hace `INSERT` de combinaciones
`(proveedor, id_producto, fecha_catalogo)` que no existan ya en SQLite. Nunca borra,
nunca sobreescribe. SQLite acumula historial completo.

**Lookup en el backend al registrar un artículo formal:**

```sql
SELECT precio_venta
FROM precios_catalogo
WHERE proveedor = :proveedor AND id_producto = :id_producto
ORDER BY fecha_catalogo DESC
LIMIT 1
```

Gana siempre el precio del catálogo más reciente. Si no existe el `id_producto`,
el campo `monto` queda vacío con aviso y editable (mismo comportamiento que hoy).

**Disparador de sincronización:**

El usuario corre el script manualmente desde el POS (botón "Sincronizar precios"
en `Módulo Setting`) o desde terminal:

```bash
python -m app.scripts.importar_precios tabla_precios.ods
```

No hay sincronización automática ni watcher de archivo.

#### Regla de saldo

El saldo del cliente es único (modelo tarjeta bancaria sin intereses).
Toda operación impacta la misma variable `saldo` en `clientes`:

```
saldo += monto   →  al marcar artículo como en_almacen
saldo -= monto   →  al registrar devolución o cancelación (si monto IS NOT NULL)
saldo -= abono   →  al registrar un abono en movimientos
```

---

### Menú Pedidos

El botón `Pedidos` en el `main_menu` abre una ventana emergente con cuatro opciones.

```yaml
titulo_ventana: Pedidos
opciones:
  1: Registrar Pedido
  2: Registrar Devolución
  3: Cancelar Artículo
  4: Lista de Surtido
```

#### Opción 1 — Registrar Pedido

La operadora ingresa `no_cliente` y presiona **Registrar**. El sistema valida que
el cliente exista. Si no existe: `"Cliente no encontrado. Regístralo primero en
el módulo Clientes."` — el formulario no se abre.

#### Opción 2 — Registrar Devolución

El cliente devuelve un artículo entregado. El sistema marca el artículo como
`devuelto`, revierte el monto del saldo y abre el formulario de pedido sustituto
pre-cargado. Ver flujo completo en [Flujo de una devolución](#flujo-de-una-devolución).

#### Opción 3 — Cancelar Artículo

Un artículo surtido no es aceptado por el cliente. No genera pedido sustituto.
El artículo pasa a inventario físico. Ver flujo completo en [Flujo de una cancelación](#flujo-de-una-cancelación).

#### Opción 4 — Lista de Surtido

Genera la lista consolidada de artículos en estatus `vigente` dentro del período
de corte activo. Es la lista con la que se realizan las compras al proveedor.

**Período de corte:**

Configurable por la operadora (default: miércoles a martes).

```yaml
corte:
  dia_inicio: configurable  # default: miércoles
  dia_fin:    configurable  # default: martes
  editable:   true
```

**Contenido de la lista:**

| Columna      | Fuente                                                |
| ------------ | ----------------------------------------------------- |
| No. Cliente  | `clientes.no_cliente`                                 |
| Nombre       | `clientes.nombre`                                     |
| Rol          | `pedidos_articulos.rol` (`principal` / `alternativa`) |
| Producto     | `pedidos_articulos.producto`                          |
| Marca        | `pedidos_articulos.marca`                             |
| Talla        | `pedidos_articulos.talla`                             |
| Proveedor    | `pedidos_articulos.proveedor`                         |
| ID Producto  | `pedidos_articulos.id_producto`                       |
| Monto        | `pedidos_articulos.monto`                             |
| Fecha pedido | `pedidos.fecha`                                       |

La lista es editable mientras el artículo esté en `vigente`. Casos de uso:
- El cliente cambia de producto antes de la compra.
- Un pedido entra el mismo día de compra.
- La operadora ajusta de principal a alternativa.

Al surtir un artículo, la operadora cambia su `estatus_articulo` a `en_almacen`
desde esta misma lista — ese es el momento en que el saldo se carga al cliente.

**Consulta base:**

```sql
SELECT
    c.no_cliente, c.nombre,
    pa.rol, pa.producto, pa.marca, pa.talla,
    pa.proveedor, pa.id_producto, pa.monto,
    p.fecha
FROM pedidos_articulos pa
JOIN pedidos  p ON pa.id_pedido = p.id_pedido
JOIN clientes c ON p.id_cliente = c.id_cliente
WHERE p.fecha BETWEEN :fecha_inicio AND :fecha_fin
  AND pa.estatus_articulo = 'vigente'
ORDER BY p.fecha, c.no_cliente, pa.id_pedido, pa.rol DESC;
```

---

### Formulario Registrar Pedido

Se abre tras validar `no_cliente`. Muestra el nombre del cliente en el encabezado.

Contiene entre 1 y 4 artículos. Solo el Artículo 1 es obligatorio. Los artículos
2, 3 y 4 están colapsados hasta que el usuario los active.

Cada artículo captura un renglón `principal` y, opcionalmente, su `alternativa`
(botón **"+ Agregar alternativa"**). Ambos se guardan como filas independientes
en `pedidos_articulos`.

**Comportamiento por `tipo_producto`:**

| Campo         | `formal`                                               | `informal`            |
| ------------- | ------------------------------------------------------ | --------------------- |
| `proveedor`   | Habilitado — select enum                               | Deshabilitado / vacío |
| `id_producto` | Habilitado para todos los valores de `proveedor`       | Deshabilitado / vacío |
| `producto`    | Habilitado                                             | Habilitado            |
| `marca`       | Habilitado (opcional)                                  | Habilitado (opcional) |
| `talla`       | Habilitado (opcional)                                  | Habilitado (opcional) |
| `monto`       | Autollenado si proveedor tiene lista; manual si `otro` | Libre, opcional       |

**Secuencia de captura `formal`:**

1. Operadora selecciona `tipo_producto = formal`.
2. Aparece `proveedor` (select: `Price_Shoes`, `Pakar`, `Cklass`, `otro`).
3. Se habilita `id_producto` independientemente del proveedor seleccionado.
4. Si `proveedor ∈ {Price_Shoes, Pakar, Cklass}`: al ingresar `id_producto` el sistema hace lookup en `tabla_precios` y autollena `monto` (solo lectura). Si el ID no existe, `monto` queda vacío y editable con aviso.
5. Si `proveedor = otro`: `monto` queda vacío y editable (obligatorio).
6. `producto`, `marca`, `talla` siempre editables.

**Botón Guardar:**

- `INSERT` en `pedidos` (cabecera) + uno o más `INSERT` en `pedidos_articulos`.
- `estatus_articulo` se inserta siempre como `vigente`.
- El saldo **no se modifica** al guardar el pedido. Se modifica cuando el artículo se marca `en_almacen`.
- En éxito: `"Pedido registrado correctamente."` y cierra el formulario.
- En error: `"No se pudo guardar. Intenta de nuevo."`

---

### Flujo de una devolución

Aplica a `formal` e `informal` por igual. El sustituto mantiene siempre el mismo
`tipo_producto` que el original (el formulario se pre-carga con él).

```
1. Operadora abre Pedidos > Registrar Devolución
2. Ingresa no_cliente — el sistema muestra sus artículos con estatus_articulo = 'en_almacen'
3. Operadora selecciona el artículo a devolver y confirma
4. El sistema ejecuta en una sola transacción:
      a. UPDATE pedidos_articulos SET estatus_articulo = 'devuelto' WHERE id_articulo = :id
      b. UPDATE clientes SET saldo = saldo - :monto WHERE id_cliente = :id_cliente
5. El sistema abre el formulario Registrar Pedido pre-cargado con
   tipo_producto, proveedor, marca y talla del artículo devuelto
6. Operadora ajusta el sustituto y guarda
7. El artículo sustituto se inserta con id_articulo_sustituye = id del original
   y su monto se cargará al saldo cuando llegue a en_almacen
```

**UI — paso 2 (tabla de artículos a devolver):**

| Columna      | Fuente                        |
| ------------ | ----------------------------- |
| Fecha pedido | `pedidos.fecha`               |
| Producto     | `pedidos_articulos.producto`  |
| Marca        | `pedidos_articulos.marca`     |
| Talla        | `pedidos_articulos.talla`     |
| Proveedor    | `pedidos_articulos.proveedor` |
| Monto        | `pedidos_articulos.monto`     |

**Botón Confirmar devolución:**

- En éxito: abre formulario **Registrar Pedido** pre-cargado.
- En error: `"No se pudo registrar la devolución. Intenta de nuevo."`

---

### Flujo de una cancelación

```
1. Operadora abre Pedidos > Cancelar Artículo
2. Ingresa no_cliente — el sistema muestra artículos con estatus_articulo IN ('vigente', 'en_almacen')
3. Operadora selecciona el artículo y confirma
4. El sistema ejecuta en una sola transacción:
      a. UPDATE pedidos_articulos SET estatus_articulo = 'cancelado' WHERE id_articulo = :id
      b. Si estatus_articulo actual era 'en_almacen' Y monto IS NOT NULL:
         UPDATE clientes SET saldo = saldo - :monto WHERE id_cliente = :id_cliente
         (Si era 'vigente', el saldo nunca fue cargado — no hay nada que revertir)
5. Fin. No se abre formulario adicional.
```

> Los artículos `cancelado` pasan a inventario físico. La integración con el módulo
> Inventario se implementará cuando ese módulo se construya. En esta etapa el campo
> `estatus_articulo = 'cancelado'` es el marcador suficiente.

**Botón Confirmar cancelación:**

- En éxito: `"Artículo cancelado correctamente."` y cierra la ventana.
- En error: `"No se pudo cancelar el artículo. Intenta de nuevo."`

---

### Schema JSON completo — Pedidos

```json
{
  "main_menu": {
    "botones": [
      {
        "id": "btn_pedidos",
        "etiqueta": "Pedidos",
        "accion": { "tipo": "abrir_modal", "modal": "modal_pedidos" }
      }
    ]
  },
  "modales": [
    {
      "id": "modal_pedidos",
      "titulo": "Pedidos",
      "tipo": "menu_opciones",
      "opciones": [
        { "id": 1, "etiqueta": "Registrar Pedido",     "accion": { "tipo": "abrir_modal",   "modal": "modal_busqueda_cliente_pedido"   } },
        { "id": 2, "etiqueta": "Registrar Devolución", "accion": { "tipo": "abrir_ventana", "ventana": "ventana_registrar_devolucion" } },
        { "id": 3, "etiqueta": "Cancelar Artículo",    "accion": { "tipo": "abrir_ventana", "ventana": "ventana_cancelar_articulo"    } },
        { "id": 4, "etiqueta": "Lista de Surtido",     "accion": { "tipo": "abrir_ventana", "ventana": "ventana_lista_surtido"        } }
      ]
    },
    {
      "id": "modal_busqueda_cliente_pedido",
      "titulo": "Registrar Pedido",
      "tipo": "busqueda_previa",
      "campo_busqueda": { "etiqueta": "No. Cliente", "modelo": "no_cliente", "tipo": "String", "requerido": true },
      "validacion": { "tabla": "clientes", "campo": "no_cliente", "en_error": "Cliente no encontrado. Regístralo primero en el módulo Clientes." },
      "boton": { "etiqueta": "Registrar", "accion": { "tipo": "abrir_ventana", "ventana": "ventana_registrar_pedido" } }
    }
  ],
  "ventanas": [
    {
      "id": "ventana_registrar_pedido",
      "titulo": "Registrar Pedido",
      "encabezado": { "campo": "nombre", "fuente": "clientes" },
      "articulos": {
        "minimo": 1, "maximo": 4,
        "articulo_template": {
          "principal": {
            "campos": [
              {
                "etiqueta": "Tipo de Producto", "modelo": "tipo_producto", "tipo": "Enum", "control": "select", "requerido": true,
                "opciones": [
                  { "valor": "formal",   "etiqueta": "Formal (catálogo)" },
                  { "valor": "informal", "etiqueta": "Informal"          }
                ]
              },
              {
                "etiqueta": "Proveedor", "modelo": "proveedor", "tipo": "Enum", "control": "select",
                "habilitado_si": { "tipo_producto": "formal" },
                "opciones": [
                  { "valor": "Price_Shoes", "etiqueta": "Price Shoes" },
                  { "valor": "Pakar",       "etiqueta": "Pakar"       },
                  { "valor": "Cklass",      "etiqueta": "Cklass"      },
                  { "valor": "otro",        "etiqueta": "Otro"        }
                ]
              },
              {
                "etiqueta": "ID Producto", "modelo": "id_producto", "tipo": "String", "longitud": 12,
                "habilitado_si": { "tipo_producto": "formal" },
                "nota": "Habilitado para todos los valores de proveedor. Activa lookup de precio solo si proveedor IN [Price_Shoes, Pakar, Cklass]."
              },
              { "etiqueta": "Producto", "modelo": "producto", "tipo": "String", "longitud": 50, "requerido": true },
              { "etiqueta": "Marca",    "modelo": "marca",    "tipo": "String", "longitud": 20, "requerido": false },
              { "etiqueta": "Talla",    "modelo": "talla",    "tipo": "String", "longitud": 8,  "requerido": false },
              {
                "etiqueta": "Monto", "modelo": "monto", "tipo": "Real",
                "requerido_si": [{ "tipo_producto": "formal", "proveedor": "otro" }],
                "autollenado_si": { "proveedor": ["Price_Shoes", "Pakar", "Cklass"], "fuente": "tabla_precios", "solo_lectura": true },
                "opcional_si": { "tipo_producto": "informal" }
              }
            ]
          },
          "alternativa": {
            "activacion": "boton_agregar_alternativa",
            "etiqueta_boton": "+ Agregar alternativa",
            "campos": ["tipo_producto", "proveedor", "id_producto", "producto", "marca", "talla", "monto"]
          }
        }
      },
      "acciones": [
        {
          "id": "btn_guardar", "etiqueta": "Guardar", "tipo": "button", "variante": "primary",
          "accion": {
            "tipo": "db_insert_relacional",
            "nota_saldo": "El saldo NO se modifica al guardar. Se modifica cuando el artículo se marca en_almacen.",
            "tablas": [
              {
                "tabla": "pedidos",
                "campos_autogenerados": [{ "columna": "fecha", "estrategia": "fecha_actual", "formato_almacenamiento": "YYYY-MM-DD" }],
                "campos_resueltos": [{ "columna": "id_cliente", "estrategia": "lookup", "tabla_fuente": "clientes", "campo_busqueda": "no_cliente", "campo_retorno": "id_cliente" }]
              },
              {
                "tabla": "pedidos_articulos",
                "descripcion": "Un INSERT por renglón (principal + alternativa si aplica). estatus_articulo = 'vigente' siempre.",
                "clave_foranea": "id_pedido",
                "campos_mapeados": [
                  { "modelo": "rol",           "columna": "rol"           },
                  { "modelo": "tipo_producto", "columna": "tipo_producto" },
                  { "modelo": "proveedor",     "columna": "proveedor"     },
                  { "modelo": "id_producto",   "columna": "id_producto"   },
                  { "modelo": "producto",      "columna": "producto"      },
                  { "modelo": "marca",         "columna": "marca"         },
                  { "modelo": "talla",         "columna": "talla"         },
                  { "modelo": "monto",         "columna": "monto"         }
                ],
                "valores_default": [{ "columna": "estatus_articulo", "valor": "vigente" }]
              }
            ],
            "en_exito": { "mensaje": "Pedido registrado correctamente.", "cerrar_ventana": true },
            "en_error": { "mensaje": "No se pudo guardar. Intenta de nuevo." }
          }
        }
      ]
    },
    {
      "id": "ventana_lista_surtido",
      "titulo": "Lista de Surtido",
      "corte": {
        "dia_inicio": { "tipo": "Date", "default": "miércoles", "editable": true },
        "dia_fin":    { "tipo": "Date", "default": "martes",    "editable": true }
      },
      "tabla_resultado": {
        "columnas": ["no_cliente", "nombre", "rol", "producto", "marca", "talla", "proveedor", "id_producto", "monto", "fecha"],
        "filtro": "estatus_articulo = 'vigente'",
        "ordenado_por": ["fecha ASC", "no_cliente ASC", "id_pedido ASC", "rol DESC"],
        "editable": true,
        "accion_surtir": {
          "descripcion": "Al marcar un artículo como surtido, cambia estatus_articulo a 'en_almacen' y ejecuta saldo += monto.",
          "operaciones": [
            { "UPDATE": "pedidos_articulos SET estatus_articulo = 'en_almacen' WHERE id_articulo = :id" },
            { "UPDATE": "clientes SET saldo = saldo + :monto WHERE id_cliente = :id_cliente" }
          ]
        }
      }
    },
    {
      "id": "ventana_registrar_devolucion",
      "titulo": "Registrar Devolución",
      "paso_1": {
        "tipo": "busqueda_previa",
        "campo_busqueda": { "etiqueta": "No. Cliente", "modelo": "no_cliente", "tipo": "String", "requerido": true },
        "validacion": { "tabla": "clientes", "campo": "no_cliente", "en_error": "Cliente no encontrado." }
      },
      "paso_2": {
        "tipo": "tabla_seleccionable",
        "titulo": "Selecciona el artículo a devolver",
        "fuente": {
          "query": "SELECT pa.id_articulo, p.fecha, pa.tipo_producto, pa.proveedor, pa.producto, pa.marca, pa.talla, pa.monto FROM pedidos_articulos pa JOIN pedidos p ON pa.id_pedido = p.id_pedido JOIN clientes c ON p.id_cliente = c.id_cliente WHERE c.no_cliente = :no_cliente AND pa.estatus_articulo = 'en_almacen' AND pa.rol = 'principal'"
        },
        "columnas_visibles": ["fecha", "producto", "marca", "talla", "proveedor", "monto"],
        "seleccion": "una_fila"
      },
      "accion_confirmar": {
        "etiqueta": "Confirmar devolución", "tipo": "transaccion",
        "pasos": [
          { "operacion": "UPDATE", "tabla": "pedidos_articulos", "set": { "estatus_articulo": "devuelto" }, "where": "id_articulo = :id_articulo_seleccionado" },
          { "operacion": "UPDATE", "tabla": "clientes", "set": { "saldo": "saldo - :monto" }, "where": "no_cliente = :no_cliente" }
        ],
        "en_exito": {
          "accion": "abrir_ventana", "ventana": "ventana_registrar_pedido",
          "precarga": {
            "tipo_producto": ":tipo_producto_devuelto", "proveedor": ":proveedor_devuelto",
            "marca": ":marca_devuelto", "talla": ":talla_devuelto",
            "id_articulo_sustituye": ":id_articulo_seleccionado"
          }
        },
        "en_error": { "mensaje": "No se pudo registrar la devolución. Intenta de nuevo." }
      }
    },
    {
      "id": "ventana_cancelar_articulo",
      "titulo": "Cancelar Artículo",
      "paso_1": {
        "tipo": "busqueda_previa",
        "campo_busqueda": { "etiqueta": "No. Cliente", "modelo": "no_cliente", "tipo": "String", "requerido": true },
        "validacion": { "tabla": "clientes", "campo": "no_cliente", "en_error": "Cliente no encontrado." }
      },
      "paso_2": {
        "tipo": "tabla_seleccionable",
        "titulo": "Selecciona el artículo a cancelar",
        "fuente": {
          "query": "SELECT pa.id_articulo, pa.estatus_articulo, p.fecha, pa.producto, pa.marca, pa.talla, pa.proveedor, pa.monto FROM pedidos_articulos pa JOIN pedidos p ON pa.id_pedido = p.id_pedido JOIN clientes c ON p.id_cliente = c.id_cliente WHERE c.no_cliente = :no_cliente AND pa.estatus_articulo IN ('vigente','en_almacen') AND pa.rol = 'principal'"
        },
        "columnas_visibles": ["fecha", "producto", "marca", "talla", "proveedor", "monto", "estatus_articulo"],
        "seleccion": "una_fila"
      },
      "accion_confirmar": {
        "etiqueta": "Confirmar cancelación", "tipo": "transaccion",
        "pasos": [
          { "operacion": "UPDATE", "tabla": "pedidos_articulos", "set": { "estatus_articulo": "cancelado" }, "where": "id_articulo = :id_articulo_seleccionado" },
          { "operacion": "UPDATE_CONDICIONAL", "condicion": "estatus_articulo_previo = 'en_almacen' AND monto IS NOT NULL", "tabla": "clientes", "set": { "saldo": "saldo - :monto" }, "where": "no_cliente = :no_cliente" }
        ],
        "en_exito": { "mensaje": "Artículo cancelado correctamente.", "cerrar_ventana": true },
        "en_error": { "mensaje": "No se pudo cancelar el artículo. Intenta de nuevo." }
      }
    }
  ]
}
```

---

## Módulo Inventario

> Corrige la nomenclatura del `README.md` donde este módulo aparece como
> "Piso de Venta". El nombre correcto es **Inventario**. No existe almacén
> separado — el piso de venta y el almacén son el mismo espacio físico.
> El módulo gestiona las existencias propias de la boutique.

---

### Modelo de datos — Inventario

```sql
CREATE TABLE inventario (
    id_producto       INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria         TEXT    NOT NULL
                          CHECK (categoria IN ('dama', 'caballero', 'infantil', 'accesorio', 'calzado')),
    tipo_producto     TEXT    NOT NULL
                          CHECK (tipo_producto IN ('formal', 'informal')),
    descripcion       TEXT(40) NOT NULL,
    talla             TEXT(10),
    color             TEXT(10),
    marca             TEXT(12),
    precio_venta      INTEGER NOT NULL,
    precio_descuento  INTEGER,              -- NULL = sin descuento activo.
                                            -- NOT NULL = precio vigente con descuento.
    stock             INTEGER NOT NULL DEFAULT 0,
    estatus           TEXT    NOT NULL DEFAULT 'disponible'
                          CHECK (estatus IN ('disponible', 'vendido', 'disponible_c/descuento', 'en_ruta', 'apartado')),
    descripcion_ruta  TEXT,                 -- Obligatorio cuando estatus = 'en_ruta'. NULL en otros casos.
    created           TEXT    NOT NULL,     -- ISO 8601: YYYY-MM-DD. Autogenerado.
    changed_status    TEXT                  -- ISO 8601: YYYY-MM-DD. Autogenerado al cambiar estatus.
);
```

> **Nota:** `'apartado'` se añade al enum `estatus` para soportar la operación de apartado
> del Panel Principal. El producto físico queda reservado hasta que el cliente liquida o cancela.

---

### Notas de campo — Inventario

| Campo              | Nota                                                                                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id_producto`      | PK interna autoincremental. Los productos vendidos (`estatus = 'vendido'`) conservan su `id_producto` — no se reutilizan ni se recorren.              |
| `precio_venta`     | Precio base del artículo. Siempre visible en UI.                                                                                                      |
| `precio_descuento` | `NULL` = sin descuento. Cuando tiene valor, es el precio vigente. El porcentaje se calcula on-the-fly: `(1 - precio_descuento / precio_venta) * 100`. |
| `descripcion_ruta` | Solo aplica cuando `estatus = 'en_ruta'`. Describe quién tiene el producto y/o el motivo.                                                             |
| `created`          | Autogenerado al insertar. Almacenado en `YYYY-MM-DD`, mostrado como `DD-MM-YYYY`.                                                                     |
| `changed_status`   | Autogenerado cada vez que `estatus` cambia. Permite auditar cuándo fue el último cambio.                                                              |

---

### Enum `categoria`

| Valor       | Descripción       |
| ----------- | ----------------- |
| `dama`      | Ropa de dama      |
| `caballero` | Ropa de caballero |
| `infantil`  | Ropa infantil     |
| `accesorio` | Accesorios        |
| `calzado`   | Calzado           |

---

### Enum `estatus` (inventario)

| Valor                    | Descripción                                                                    | `precio_descuento` | `descripcion_ruta` |
| ------------------------ | ------------------------------------------------------------------------------ | ------------------ | ------------------ |
| `disponible`             | En piso, disponible para venta al precio base.                                 | `NULL`             | `NULL`             |
| `disponible_c/descuento` | En piso, disponible con descuento activo. Precio vigente = `precio_descuento`. | Requerido          | `NULL`             |
| `en_ruta`                | Fuera del piso; enviado a exhibición en campo. Puede volver a `disponible`.    | `NULL` o valor     | Requerido          |
| `apartado`               | Reservado por un cliente mediante operación de Apartado en Panel Principal.    | `NULL` o valor     | `NULL`             |
| `vendido`                | Vendido. El `id_producto` se conserva para historial; no se reutiliza.         | —                  | —                  |

**Transiciones válidas:**

| Estatus actual           | Transiciones permitidas                                          |
| ------------------------ | ---------------------------------------------------------------- |
| `disponible`             | → `en_ruta`, → `disponible_c/descuento`, → `apartado`, → `vendido` |
| `disponible_c/descuento` | → `disponible`, → `en_ruta`, → `apartado`, → `vendido`          |
| `en_ruta`                | → `disponible`, → `vendido`                                     |
| `apartado`               | → `disponible` (cancelación), → `vendido` (liquidación)         |
| `vendido`                | — (sin transición posible desde UI)                             |

---

### Regla de `precio_descuento`

`precio_descuento` es una columna nullable en `inventario`. No existe columna
`porcentaje_descuento` — el porcentaje se calcula en consulta cuando se necesita.

```sql
-- Precio vigente de un artículo
SELECT
    id_producto,
    descripcion,
    precio_venta,
    precio_descuento,
    COALESCE(precio_descuento, precio_venta) AS precio_vigente,
    CASE
        WHEN precio_descuento IS NOT NULL
        THEN ROUND((1.0 - precio_descuento * 1.0 / precio_venta) * 100, 1)
        ELSE NULL
    END AS pct_descuento
FROM inventario;
```

Al aplicar un descuento: `UPDATE inventario SET precio_descuento = :valor, estatus = 'disponible_c/descuento', changed_status = :hoy WHERE id_producto = :id`.

Al retirar el descuento: `UPDATE inventario SET precio_descuento = NULL, estatus = 'disponible', changed_status = :hoy WHERE id_producto = :id`.

---

### Menú Inventario

El botón `Inventario` en el `main_menu` abre una ventana emergente con tres opciones.

```yaml
titulo_ventana: Inventario
opciones:
  1: Agregar Producto
  2: Cambiar Estatus
  3: Consulta Inventario
```

#### Opción 1 — Agregar Producto

Formulario de alta de producto. Escribe en tabla `inventario`.

**Campos capturados por la operadora:**

| Etiqueta         | Modelo          | Tipo          | Longitud | Requerido |
| ---------------- | --------------- | ------------- | -------- | --------- |
| Categoría        | `categoria`     | Enum / select | —        | ✅         |
| Tipo de Producto | `tipo_producto` | Enum / select | —        | ✅         |
| Descripción      | `descripcion`   | String        | 40       | ✅         |
| Talla            | `talla`         | String        | 10       | ❌         |
| Color            | `color`         | String        | 10       | ❌         |
| Marca            | `marca`         | String        | 12       | ❌         |
| Precio Venta     | `precio_venta`  | Integer       | —        | ✅         |
| Stock            | `stock`         | Integer       | —        | ✅         |

**Campos autogenerados:**

| Columna            | Estrategia                                                       |
| ------------------ | ---------------------------------------------------------------- |
| `id_producto`      | `AUTOINCREMENT`. No se reutiliza aunque el producto sea vendido. |
| `estatus`          | Default `disponible`.                                            |
| `precio_descuento` | Default `NULL`.                                                  |
| `descripcion_ruta` | Default `NULL`.                                                  |
| `created`          | Fecha actual. `YYYY-MM-DD` en DB, `DD-MM-YYYY` en UI.            |
| `changed_status`   | `NULL` al crear. Se actualiza en cada cambio de `estatus`.       |

**Botón Guardar:**

- En éxito: `"Producto agregado correctamente."` y limpia el formulario.
- En error: `"No se pudo guardar. Intenta de nuevo."`

#### Opción 2 — Cambiar Estatus

**Flujo:**

1. Se abre ventana con campo de búsqueda `id_producto`.
2. La operadora ingresa el ID y presiona **Buscar**.
3. El sistema muestra el registro actual del producto (descripción, estatus actual, precio).
4. Se muestran solo las **transiciones válidas** desde el estatus actual (ver tabla de transiciones en [Enum `estatus`](#enum-estatus-inventario)).
5. La operadora selecciona el nuevo estatus:
   - Si elige `en_ruta`: se muestra campo obligatorio **Descripción** (texto libre).
   - Si elige `disponible_c/descuento`: se muestra campo **Precio con descuento** (Integer, obligatorio, debe ser menor que `precio_venta`).
   - Si elige `disponible` (desde `en_ruta` o `disponible_c/descuento`): sin campos adicionales.
   - Si elige `vendido`: confirmación simple.
6. Presiona **Aplicar cambio**.
7. El sistema ejecuta en una transacción: `UPDATE inventario SET estatus = :nuevo_estatus, changed_status = :hoy [, campos_condicionales] WHERE id_producto = :id`.

> **UX — regla de diseño:** no se presentan todas las opciones de estatus como
> lista plana. Solo se muestran las transiciones válidas desde el estatus actual,
> como botones o radio buttons claramente etiquetados. Esto elimina la ambigüedad
> y evita transiciones inválidas sin necesidad de validación adicional.

**Botón Aplicar cambio:**

- En éxito: `"Estatus actualizado correctamente."` y cierra la ventana.
- En error: `"No se pudo actualizar. Intenta de nuevo."`

#### Opción 3 — Consulta Inventario

Abre la tabla completa de `inventario` con filtros y ordenamiento desde la UI.

Columnas visibles por default:

| Columna        | Fuente                                     |
| -------------- | ------------------------------------------ |
| ID             | `id_producto`                              |
| Categoría      | `categoria`                                |
| Tipo           | `tipo_producto`                            |
| Descripción    | `descripcion`                              |
| Talla          | `talla`                                    |
| Color          | `color`                                    |
| Marca          | `marca`                                    |
| Precio venta   | `precio_venta`                             |
| Precio vigente | `COALESCE(precio_descuento, precio_venta)` |
| Stock          | `stock`                                    |
| Estatus        | `estatus`                                  |
| Fecha alta     | `created`                                  |

**Consultas rápidas disponibles:**

- Filtro por `categoria`
- Filtro por `estatus`
- Filtro por `tipo_producto`
- Suma de `precio_vigente` por `tipo_producto` (corte de importe)
- `GROUP BY categoria` con conteo y suma de importe

> La integración con `movimientos` para cruzar ventas contra inventario se
> implementará en versiones futuras (v0.2+).

---

### Schema JSON completo — Inventario

```json
{
  "main_menu": {
    "botones": [
      {
        "id": "btn_inventario",
        "etiqueta": "Inventario",
        "accion": { "tipo": "abrir_modal", "modal": "modal_inventario" }
      }
    ]
  },
  "modales": [
    {
      "id": "modal_inventario",
      "titulo": "Inventario",
      "tipo": "menu_opciones",
      "opciones": [
        { "id": 1, "etiqueta": "Agregar Producto",    "accion": { "tipo": "abrir_ventana", "ventana": "ventana_agregar_producto"    } },
        { "id": 2, "etiqueta": "Cambiar Estatus",     "accion": { "tipo": "abrir_ventana", "ventana": "ventana_cambiar_estatus"     } },
        { "id": 3, "etiqueta": "Consulta Inventario", "accion": { "tipo": "abrir_ventana", "ventana": "ventana_consulta_inventario" } }
      ]
    }
  ],
  "ventanas": [
    {
      "id": "ventana_agregar_producto",
      "titulo": "Agregar Producto",
      "campos": [
        {
          "etiqueta": "Categoría", "modelo": "categoria", "tipo": "Enum", "control": "select", "requerido": true,
          "opciones": [
            { "valor": "dama",       "etiqueta": "Dama"       },
            { "valor": "caballero",  "etiqueta": "Caballero"  },
            { "valor": "infantil",   "etiqueta": "Infantil"   },
            { "valor": "accesorio",  "etiqueta": "Accesorio"  },
            { "valor": "calzado",    "etiqueta": "Calzado"    }
          ]
        },
        {
          "etiqueta": "Tipo de Producto", "modelo": "tipo_producto", "tipo": "Enum", "control": "select", "requerido": true,
          "opciones": [
            { "valor": "formal",   "etiqueta": "Formal"   },
            { "valor": "informal", "etiqueta": "Informal" }
          ]
        },
        { "etiqueta": "Descripción",   "modelo": "descripcion",  "tipo": "String",  "longitud": 40, "requerido": true  },
        { "etiqueta": "Talla",         "modelo": "talla",         "tipo": "String",  "longitud": 10, "requerido": false },
        { "etiqueta": "Color",         "modelo": "color",         "tipo": "String",  "longitud": 10, "requerido": false },
        { "etiqueta": "Marca",         "modelo": "marca",         "tipo": "String",  "longitud": 12, "requerido": false },
        { "etiqueta": "Precio Venta",  "modelo": "precio_venta",  "tipo": "Integer",                 "requerido": true  },
        { "etiqueta": "Stock",         "modelo": "stock",         "tipo": "Integer",                 "requerido": true  }
      ],
      "acciones": [
        {
          "id": "btn_guardar", "etiqueta": "Guardar", "tipo": "button", "variante": "primary",
          "accion": {
            "tipo": "db_insert", "tabla": "inventario",
            "campos_autogenerados": [
              { "columna": "created", "estrategia": "fecha_actual", "formato_almacenamiento": "YYYY-MM-DD", "formato_display": "DD-MM-YYYY" }
            ],
            "valores_default": [
              { "columna": "estatus",           "valor": "disponible" },
              { "columna": "precio_descuento",  "valor": null         },
              { "columna": "descripcion_ruta",  "valor": null         },
              { "columna": "changed_status",    "valor": null         }
            ],
            "en_exito": { "mensaje": "Producto agregado correctamente.", "limpiar_formulario": true },
            "en_error": { "mensaje": "No se pudo guardar. Intenta de nuevo." }
          }
        }
      ]
    },
    {
      "id": "ventana_cambiar_estatus",
      "titulo": "Cambiar Estatus",
      "paso_1": {
        "tipo": "busqueda_previa",
        "campo_busqueda": { "etiqueta": "ID Producto", "modelo": "id_producto", "tipo": "Integer", "requerido": true },
        "descripcion": "El id_producto es el identificador interno del artículo en inventario."
      },
      "paso_2": {
        "tipo": "display_registro",
        "campos_visibles": ["descripcion", "categoria", "estatus", "precio_venta", "precio_descuento"],
        "transiciones_por_estatus": {
          "disponible":             ["en_ruta", "disponible_c/descuento", "apartado", "vendido"],
          "disponible_c/descuento": ["disponible", "en_ruta", "apartado", "vendido"],
          "en_ruta":                ["disponible", "vendido"],
          "apartado":               ["disponible", "vendido"]
        },
        "campos_condicionales": [
          {
            "visible_si": { "nuevo_estatus": "en_ruta" },
            "etiqueta": "Descripción",
            "modelo": "descripcion_ruta",
            "tipo": "String",
            "requerido": true
          },
          {
            "visible_si": { "nuevo_estatus": "disponible_c/descuento" },
            "etiqueta": "Precio con descuento",
            "modelo": "precio_descuento",
            "tipo": "Integer",
            "requerido": true,
            "validacion": "precio_descuento < precio_venta"
          }
        ]
      },
      "accion_confirmar": {
        "etiqueta": "Aplicar cambio",
        "tipo": "transaccion",
        "pasos": [
          {
            "operacion": "UPDATE", "tabla": "inventario",
            "set": {
              "estatus": ":nuevo_estatus",
              "changed_status": ":fecha_actual",
              "descripcion_ruta": ":descripcion_ruta_o_null",
              "precio_descuento": ":precio_descuento_o_null"
            },
            "where": "id_producto = :id_producto"
          }
        ],
        "en_exito": { "mensaje": "Estatus actualizado correctamente.", "cerrar_ventana": true },
        "en_error": { "mensaje": "No se pudo actualizar. Intenta de nuevo." }
      }
    },
    {
      "id": "ventana_consulta_inventario",
      "titulo": "Consulta Inventario",
      "tipo": "tabla",
      "tabla_fuente": "inventario",
      "carga": "al_abrir_ventana",
      "columnas_visibles": [
        { "campo": "id_producto",                                    "etiqueta": "ID"            },
        { "campo": "categoria",                                      "etiqueta": "Categoría"     },
        { "campo": "tipo_producto",                                  "etiqueta": "Tipo"          },
        { "campo": "descripcion",                                    "etiqueta": "Descripción"   },
        { "campo": "talla",                                          "etiqueta": "Talla"         },
        { "campo": "color",                                          "etiqueta": "Color"         },
        { "campo": "marca",                                          "etiqueta": "Marca"         },
        { "campo": "precio_venta",                                   "etiqueta": "Precio base"   },
        { "campo": "COALESCE(precio_descuento, precio_venta)",       "etiqueta": "Precio vigente"},
        { "campo": "stock",                                          "etiqueta": "Stock"         },
        { "campo": "estatus",                                        "etiqueta": "Estatus"       },
        { "campo": "created",                                        "etiqueta": "Fecha alta"    }
      ],
      "filtros_rapidos": [
        { "etiqueta": "Por categoría",  "campo": "categoria"     },
        { "etiqueta": "Por estatus",    "campo": "estatus"       },
        { "etiqueta": "Por tipo",       "campo": "tipo_producto" }
      ],
      "consultas_rapidas": [
        {
          "etiqueta": "Importe por tipo",
          "query": "SELECT tipo_producto, SUM(COALESCE(precio_descuento, precio_venta)) AS importe_total FROM inventario WHERE estatus != 'vendido' GROUP BY tipo_producto"
        },
        {
          "etiqueta": "Conteo por categoría",
          "query": "SELECT categoria, COUNT(*) AS cantidad, SUM(COALESCE(precio_descuento, precio_venta)) AS importe FROM inventario WHERE estatus != 'vendido' GROUP BY categoria"
        }
      ]
    }
  ]
}
```

---

## Panel Principal — Main Panel

> El Panel Principal es la pantalla de operación cotidiana: siempre visible, siempre
> disponible. Funciona como caja registradora. No requiere navegar a ningún módulo.
>
> Escribe en: `movimientos`. Dispara actualizaciones en `clientes.saldo` e `inventario.estatus`
> según la operación.

---

### Tabla `movimientos`

Registro de todas las operaciones de caja. Es la fuente de verdad para liquidez,
historial de abonos y consultas contables.

```sql
CREATE TABLE movimientos (
    id_movimiento    INTEGER PRIMARY KEY AUTOINCREMENT,
    operacion        TEXT    NOT NULL
                         CHECK (operacion IN ('contado', 'apartado', 'abono', 'gasto')),
    id_cliente       INTEGER REFERENCES clientes(id_cliente),
                     -- NULL para operacion = 'gasto' y 'contado' sin cliente.
    id_producto      INTEGER REFERENCES inventario(id_producto),
                     -- NULL para abono, gasto y contado desde catálogo.
    monto            REAL    NOT NULL,
    forma_pago       TEXT    NOT NULL
                         CHECK (forma_pago IN ('efectivo', 'transferencia', 'tarjeta')),
    saldo_resultante REAL,
                     -- NULL para contado y gasto. Valor calculado para apartado y abono.
    descripcion      TEXT,
                     -- Obligatorio cuando operacion = 'gasto'. NULL en los demás casos.
    fecha            TEXT    NOT NULL   -- ISO 8601: YYYY-MM-DD HH:MM:SS. Autogenerado.
);
```

**Regla de `forma_pago`:** los métodos disponibles dependen de la configuración activa en
`configuracion` (ver [Módulo Setting](#módulo-setting)). El frontend solo muestra las
formas de pago habilitadas.

---

### Módulo Apartado

> `Apartado` **no es un módulo independiente** con su propio botón en `main_menu`.
> Es una operación del Panel Principal — igual que `Contado`, `Abono` y `Gasto`.
> No existe tabla `apartados` separada: el modelo correcto usa `movimientos` + `inventario` + `clientes.saldo`.

#### Estatus `apartado` en `inventario`

El valor `'apartado'` ya está incluido en el `CHECK` constraint del Módulo Inventario.
El producto físico queda reservado en `inventario.estatus = 'apartado'` hasta que el
cliente liquida (`→ vendido`) o cancela (`→ disponible`).

#### Ciclo de vida de un Apartado

```
inventario.estatus:   disponible ──▶ apartado ──────────────────▶ vendido
                                          │ (cliente no liquida)
                                          └──▶ disponible  (cancelación)

clientes.saldo:       0  ──▶  precio − primer_pago  ──▶ ... ──▶ 0

movimientos:          [apartado: 1er pago]  [abono]  [abono]  [abono: saldo en 0]
```

#### Reglas del Apartado

1. El cliente debe estar registrado en `clientes`. Obligatorio.
2. El producto debe existir en `inventario` con `estatus IN ('disponible', 'disponible_c/descuento')`. El backend rechaza si no.
3. El primer pago mínimo es `$100.00`. El backend rechaza si `monto < 100`.
4. El saldo generado es `precio_producto − primer_pago`. Se suma al `clientes.saldo` existente.
5. El plazo de liquidación es un mes. El sistema no lo bloquea automáticamente — es operativo.
6. Al registrar el apartado, `inventario.estatus` cambia a `'apartado'` en la misma transacción.
7. Si el cliente cancela: `inventario.estatus` regresa a `'disponible'`. `clientes.saldo` se reduce por el monto pendiente (no se devuelve el primer pago salvo decisión de la operadora).

---

### Diseño de pantalla

```yaml
titulo: Boutique Zepeda
layout: formulario_central_siempre_visible
campos:
  - etiqueta: Operación
    modelo: operacion
    tipo: Enum
    control: radio_buttons
    opciones: [Contado, Apartado, Abono, Gasto]
    requerido: true
  - etiqueta: No. Cliente
    modelo: no_cliente
    tipo: String
    control: input_lookup
    requerido: condicional   # obligatorio en Apartado y Abono; opcional en Contado; deshabilitado en Gasto
  - etiqueta: Monto
    modelo: monto
    tipo: Float
    requerido: true
  - etiqueta: Forma de Pago
    modelo: forma_pago
    tipo: Enum
    control: radio_buttons
    opciones: [Efectivo, Transferencia, Tarjeta]
    requerido: true
campos_condicionales_por_operacion:
  Contado:
    - tipo_origen: [Catálogo, Inventario]   # select que determina si vincula id_producto
    - id_producto: condicional si origen = Inventario
    - descripcion_producto: texto libre si origen = Catálogo
  Apartado:
    - id_producto: obligatorio (solo Inventario)
    - precio_producto: autollenado al seleccionar id_producto (solo lectura)
    - saldo_resultante: calculado y mostrado (precio − monto). Solo lectura.
  Abono:
    - saldo_actual: mostrado al buscar cliente (solo lectura)
    - saldo_resultante: calculado (saldo_actual − monto). Solo lectura.
  Gasto:
    - descripcion: texto libre. Obligatorio. Reemplaza id_cliente y producto.
```

---

### Campos activos por operación

| Operación | No. Cliente        | Producto / Origen              | Monto                   | Forma Pago | `saldo_resultante`    | Descripción    |
| --------- | ------------------ | ------------------------------ | ----------------------- | ---------- | --------------------- | -------------- |
| Contado   | Opcional           | ✅ (Catálogo o Inventario)      | ✅                       | ✅          | NULL                  | —              |
| Apartado  | Obligatorio        | ✅ (solo Inventario)            | ✅ (1er pago, mín $100) | ✅          | ✅ precio − pago       | —              |
| Abono     | Obligatorio        | ❌                              | ✅                       | ✅          | ✅ saldo − monto       | —              |
| Gasto     | Deshabilitado      | ❌                              | ✅                       | ✅          | NULL                  | ✅ obligatorio  |

---

### Comportamiento por operación

#### Contado

El flujo varía según el origen del producto.

**Origen: Catálogo (pedido formal o informal)**

1. Operadora selecciona `tipo_origen = Catálogo`.
2. Ingresa descripción libre del producto (no vincula `id_producto`).
3. Ingresa monto y forma de pago.
4. El sistema inserta en `movimientos` con `operacion = 'contado'`, `id_producto = NULL`.
5. No impacta `inventario` ni `clientes.saldo`.

**Origen: Inventario**

1. Operadora selecciona `tipo_origen = Inventario`.
2. Ingresa `id_producto`. El sistema verifica `inventario.estatus IN ('disponible', 'disponible_c/descuento')` y muestra descripción y precio.
3. El backend rechaza si `inventario.stock = 0` o `estatus` no es disponible.
4. El sistema inserta en `movimientos` con `operacion = 'contado'`, `id_producto` vinculado.
5. Descuenta `inventario.stock -= 1`. Si `stock` llega a 0, actualiza `estatus = 'vendido'`.

#### Apartado

1. Operadora ingresa `no_cliente` — el sistema muestra nombre y saldo actual del cliente.
2. Ingresa `id_producto` (solo de `inventario`). El sistema muestra descripción y precio.
3. El backend valida: `inventario.estatus IN ('disponible', 'disponible_c/descuento')`. Si no: `"El producto no está disponible para apartar."`.
4. Operadora ingresa monto del primer pago. El sistema muestra `saldo_resultante = precio − monto`.
5. Backend valida: `monto >= 100`. Si no: `"El primer pago mínimo es $100.00."`.
6. Operadora selecciona forma de pago y confirma.

**Transacción al confirmar:**

```sql
-- 1. Registrar movimiento
INSERT INTO movimientos (operacion, id_cliente, id_producto, monto, forma_pago, saldo_resultante, fecha)
VALUES ('apartado', :id_cliente, :id_producto, :monto, :forma_pago, :saldo_resultante, :fecha_actual);

-- 2. Actualizar saldo del cliente
UPDATE clientes SET saldo = saldo + :saldo_resultante WHERE id_cliente = :id_cliente;

-- 3. Marcar producto como apartado
UPDATE inventario SET estatus = 'apartado', changed_status = :fecha_actual
WHERE id_producto = :id_producto;
```

#### Abono

1. Operadora ingresa `no_cliente`. El sistema muestra nombre y `saldo_actual`.
2. Operadora ingresa monto del abono. El sistema muestra `saldo_resultante = saldo_actual − monto`.
3. Backend valida: `monto <= saldo_actual`. Si no: `"El abono supera el saldo del cliente."`.
4. Operadora selecciona forma de pago y confirma.

**Transacción al confirmar:**

```sql
-- 1. Registrar movimiento
INSERT INTO movimientos (operacion, id_cliente, monto, forma_pago, saldo_resultante, fecha)
VALUES ('abono', :id_cliente, :monto, :forma_pago, :saldo_resultante, :fecha_actual);

-- 2. Actualizar saldo del cliente
UPDATE clientes SET saldo = saldo - :monto WHERE id_cliente = :id_cliente;

-- 3. Recalcular fecha_pago_programada según frecuencia_pago del cliente
-- Ver ciclo de fecha_pago_programada en Módulo Clientes.
```

Si `saldo_resultante = 0`: el sistema muestra `"¡Cuenta liquidada!"` en el mismo toast de éxito.
El `estatus` de `clientes` no cambia automáticamente — el cliente permanece `activo`.
La operadora puede cambiar el estatus manualmente desde **Editar Cliente** si lo considera.

#### Gasto

1. El campo `no_cliente` se deshabilita visualmente.
2. El campo `descripcion` se activa y es obligatorio.
3. Operadora ingresa monto, forma de pago y descripción.
4. El sistema inserta en `movimientos` con `operacion = 'gasto'`, `id_cliente = NULL`, `id_producto = NULL`.
5. `saldo_resultante = NULL`. El monto es salida de caja (negativo para el negocio).

> El saldo del negocio no existe como campo en la DB — se deriva mediante consultas
> agregadas sobre `movimientos`. Ver [Módulo Consulta Global](#módulo-consulta-global).

---

### Schema JSON — Panel Principal

```json
{
  "panel_principal": {
    "titulo": "Boutique Zepeda",
    "campos": [
      {
        "etiqueta": "Operación", "modelo": "operacion", "tipo": "Enum",
        "control": "radio_buttons", "requerido": true,
        "opciones": ["Contado", "Apartado", "Abono", "Gasto"]
      },
      {
        "etiqueta": "No. Cliente", "modelo": "no_cliente", "tipo": "String",
        "control": "input_lookup", "requerido": "condicional",
        "visible_en": ["Contado", "Apartado", "Abono"],
        "deshabilitado_en": ["Gasto"]
      },
      {
        "etiqueta": "Monto", "modelo": "monto", "tipo": "Float", "requerido": true
      },
      {
        "etiqueta": "Forma de Pago", "modelo": "forma_pago", "tipo": "Enum",
        "control": "radio_buttons", "requerido": true,
        "opciones": ["Efectivo", "Transferencia", "Tarjeta"]
      }
    ],
    "campos_condicionales": [
      {
        "visible_si": {"operacion": "Contado"},
        "campos": [
          { "etiqueta": "Origen", "modelo": "tipo_origen", "tipo": "Enum",
            "opciones": ["Catálogo", "Inventario"], "requerido": true },
          { "etiqueta": "ID Producto", "modelo": "id_producto", "tipo": "Integer",
            "visible_si": {"tipo_origen": "Inventario"}, "requerido": true },
          { "etiqueta": "Producto", "modelo": "descripcion_producto", "tipo": "String",
            "visible_si": {"tipo_origen": "Catálogo"}, "requerido": false }
        ]
      },
      {
        "visible_si": {"operacion": "Apartado"},
        "campos": [
          { "etiqueta": "ID Producto", "modelo": "id_producto", "tipo": "Integer", "requerido": true },
          { "etiqueta": "Precio", "modelo": "precio_producto", "tipo": "Float",
            "solo_lectura": true, "autollenado": "inventario.precio_venta" },
          { "etiqueta": "Saldo resultante", "modelo": "saldo_resultante", "tipo": "Float",
            "solo_lectura": true, "calculado": "precio_producto - monto" }
        ]
      },
      {
        "visible_si": {"operacion": "Abono"},
        "campos": [
          { "etiqueta": "Saldo actual", "modelo": "saldo_actual", "tipo": "Float",
            "solo_lectura": true, "autollenado": "clientes.saldo" },
          { "etiqueta": "Saldo resultante", "modelo": "saldo_resultante", "tipo": "Float",
            "solo_lectura": true, "calculado": "saldo_actual - monto" }
        ]
      },
      {
        "visible_si": {"operacion": "Gasto"},
        "campos": [
          { "etiqueta": "Descripción", "modelo": "descripcion", "tipo": "String",
            "longitud": 60, "requerido": true }
        ]
      }
    ]
  }
}
```

---

## Módulo Shein

> **Naturaleza del módulo:** la boutique actúa como intermediaria. El cliente solicita un
> artículo visto en la app de Shein. La tienda ejecuta la compra, lo entrega y cobra al
> mismo precio de la app. Siempre de contado. Sin devoluciones.
>
> El valor que aporta `pos-boutique` en este módulo es doble: registro limpio de cada
> operación individual y acumulación de artículos por corte para calcular el `bono_descuento`
> que Shein otorga por volumen.

---

### Decisiones de diseño — Shein

**Cartera propia vs. tabla `clientes`.**
Los clientes de Shein son transaccionales: no tienen saldo, no tienen garante, no tienen
`frecuencia_pago`. Forzarlos en `clientes` introduciría datos obligatorios que no aplican
(campos de referencia, `estatus`, `saldo`) y contaminaría la cartera de crédito.
Decisión: tabla independiente `shein_clientes` con los campos mínimos necesarios.

**`bono_descuento` — dónde vive.**
El bono no pertenece a un cliente ni a un artículo — es el resultado de un corte de
operaciones del negocio. Vive en su propia tabla `shein_cortes` sin FK a clientes
ni a artículos individuales. El cálculo (porcentaje × suma de montos del período) lo
ejecuta el backend al registrar el corte.

---

### Modelo de datos — Shein

#### Tabla `shein_clientes`

```sql
CREATE TABLE shein_clientes (
    id_shein_cliente  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre            TEXT(20) NOT NULL,
    colonia           TEXT(12) NOT NULL,
    telefono          INTEGER  NOT NULL   -- 10 dígitos
);
```

| Campo              | Nota                                                                    |
| ------------------ | ----------------------------------------------------------------------- |
| `id_shein_cliente` | PK interna. Identificador operativo visible en UI como consecutivo.     |
| `nombre`           | Nombre completo. Máximo 20 caracteres.                                  |
| `colonia`          | Máximo 12 caracteres.                                                   |
| `telefono`         | 10 dígitos. Obligatorio. Sin guiones ni espacios.                       |

> Esta tabla es independiente de `clientes`. No existe FK entre ellas. Un cliente que tenga
> crédito en la tienda y también compre por Shein tiene registros en ambas tablas — eso es
> correcto y no genera inconsistencia.

#### Tabla `shein_pedidos`

```sql
CREATE TABLE shein_pedidos (
    id_shein_pedido   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_shein_cliente  INTEGER NOT NULL REFERENCES shein_clientes(id_shein_cliente),
    id_shein_corte    INTEGER REFERENCES shein_cortes(id_shein_corte),
                      -- NULL mientras el pedido no ha sido asignado a un corte.
    producto          TEXT    NOT NULL,
    monto             REAL    NOT NULL,   -- Precio en app Shein al momento del pedido.
    monto_vigente     REAL,              -- NULL hasta cerrar corte. Se llena al asignar al corte si el precio varió.
    fecha             TEXT    NOT NULL    -- ISO 8601: YYYY-MM-DD
);
```

| Campo             | Nota                                                                                               |
| ----------------- | -------------------------------------------------------------------------------------------------- |
| `id_shein_corte`  | `NULL` mientras el pedido está pendiente de corte. Se asigna al cerrar un corte.                  |
| `producto`        | Descripción libre. No hay catálogo formal de Shein en el sistema.                                  |
| `monto`           | Precio vigente en la app **al momento del pedido**.                                                |
| `monto_vigente`   | `NULL` en pedidos pendientes. Se llena en **Registrar Corte** si el precio varió. Ver [Cuello de botella](#cuello-de-botella--variación-de-precios-en-app-shein). |

#### Tabla `shein_cortes`

```sql
CREATE TABLE shein_cortes (
    id_shein_corte    INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_corte       TEXT    NOT NULL,   -- ISO 8601: YYYY-MM-DD. Fecha en que se cierra el corte.
    total_pedidos     INTEGER NOT NULL,   -- Cantidad de artículos incluidos en el corte.
    suma_montos       REAL    NOT NULL,   -- Suma de todos los montos del corte.
    porcentaje_bono   REAL    NOT NULL,   -- Ej: 0.08 para 8 %.
    bono_monto        REAL    NOT NULL    -- suma_montos × porcentaje_bono. Calculado por backend.
);
```

---

### Menú Shein

El botón `Shein` en el `main_menu` abre una ventana emergente con cuatro opciones.

```yaml
titulo_ventana: Shein
opciones:
  1: Registrar Cliente Shein
  2: Registrar Pedido Shein
  3: Lista de Pedidos
  4: Registrar Corte
```

#### Opción 1 — Registrar Cliente Shein

Formulario de alta. Escribe en tabla `shein_clientes`.

| Etiqueta | Modelo    | Tipo    | Longitud | Requerido |
| -------- | --------- | ------- | -------- | --------- |
| Nombre   | `nombre`  | String  | 20       | ✅         |
| Colonia  | `colonia` | String  | 12       | ✅         |
| Teléfono | `telefono`| Integer | 10       | ✅         |

- En éxito: `"Cliente Shein registrado correctamente."` y limpia el formulario.
- En error: `"No se pudo guardar. Intenta de nuevo."`

#### Opción 2 — Registrar Pedido Shein

**Paso 1 — Buscar cliente:**

Campo de búsqueda `id_shein_cliente` (consecutivo visible en UI) o `nombre` (búsqueda parcial).
Si no existe: `"Cliente no encontrado. Regístralo primero."` — el formulario no se abre.

**Paso 2 — Formulario de artículo:**

| Etiqueta | Modelo     | Tipo   | Requerido |
| -------- | ---------- | ------ | --------- |
| Producto | `producto` | String | ✅         |
| Monto    | `monto`    | Float  | ✅         |

- `fecha` se autogenera con la fecha actual (ISO 8601).
- `id_shein_corte` se inserta como `NULL` — se asignará al cerrar un corte.
- `monto_vigente` se inserta como `NULL` — se llenará en Registrar Corte si aplica.
- En éxito: `"Pedido Shein registrado."` y limpia el formulario.

#### Opción 3 — Lista de Pedidos

Tabla de pedidos pendientes de corte (`id_shein_corte IS NULL`), ordenados por fecha ascendente.

| Columna  | Fuente                                        |
| -------- | --------------------------------------------- |
| ID       | `shein_pedidos.id_shein_pedido`               |
| Fecha    | `shein_pedidos.fecha`                         |
| Cliente  | `shein_clientes.nombre`                       |
| Producto | `shein_pedidos.producto`                      |
| Monto    | `shein_pedidos.monto`                         |
| Corte    | `"Pendiente"` cuando `id_shein_corte IS NULL` |

Filtro rápido por fecha (rango `dd-mm-yyyy` a `dd-mm-yyyy`).

#### Opción 4 — Registrar Corte

Genera un registro en `shein_cortes` e impacta los pedidos seleccionados.

**Flujo:**

1. La operadora selecciona los pedidos a incluir (checkboxes sobre la Lista de Pedidos — solo `id_shein_corte IS NULL`).
2. El sistema calcula y muestra: cantidad de artículos y suma de montos.
3. La operadora verifica precio vigente de cada artículo en la app. Si alguno cambió, edita la columna `monto_vigente` directamente en la tabla. El sistema resalta en rojo los artículos donde `monto_vigente > monto`.
4. Si hay artículos con incremento, el sistema muestra: `"X artículos con incremento de precio. Confirmar notificación a clientes antes de continuar."`.
5. La operadora ingresa el `porcentaje_bono` (Float, ej: `0.08` para 8%).
6. El sistema calcula y muestra `bono_monto = suma_montos × porcentaje_bono`.
7. La operadora confirma.

**Transacción al confirmar:**

```sql
-- 1. Insertar corte
INSERT INTO shein_cortes (fecha_corte, total_pedidos, suma_montos, porcentaje_bono, bono_monto)
VALUES (:fecha_actual, :total_pedidos, :suma_montos, :porcentaje_bono, :bono_monto);

-- 2. Vincular pedidos seleccionados al corte (y persistir monto_vigente si fue editado)
UPDATE shein_pedidos
SET id_shein_corte = :id_shein_corte_nuevo,
    monto_vigente  = :monto_vigente_o_null
WHERE id_shein_pedido IN (:ids_seleccionados);
```

- En éxito: `"Corte registrado. Bono: $X.XX"` y cierra la ventana.
- En error: `"No se pudo registrar el corte. Intenta de nuevo."`

---

### Cuello de botella — Variación de precios en app Shein

> **Estado:** solución viable implementada en MVP (columna `monto_vigente`).
> Solución automatizada fuera de presupuesto en etapa actual.

**Situación:**
El `monto` registrado en `shein_pedidos` corresponde al precio de la app al momento
en que el cliente solicita el artículo. Entre ese momento y el día del corte, el precio
puede haber cambiado.

- Si el precio **bajó**: la tienda absorbe la diferencia favorablemente. No se notifica al cliente.
- Si el precio **subió**: la tienda debe consultar al cliente antes de ejecutar la compra.

**Solución implementada:** campo `monto_vigente` editable en la ventana de Registrar Corte.
La operadora ingresa el precio actual si varió. El sistema concentra la revisión en un solo
paso del flujo, aunque la verificación sigue siendo manual.

**Solución de referencia (fuera de presupuesto):** un agente automatizado consultaría precios
vigentes antes de cada corte y generaría alertas automáticas por artículos con incremento.
Requiere integración con Shein (scraping o API privada) — no viable en el presupuesto actual.

---

## Módulo Recargas Telefónicas

> Módulo sin FK externas. Opera como registro independiente de operaciones de recarga.
> Las recargas se ejecutan en la terminal de cobro (proceso externo al sistema).
> `pos-boutique` solo registra la operación para trazabilidad y suma de ingresos.

---

### Modelo de datos — Recargas

```sql
CREATE TABLE recargas (
    id_recarga  INTEGER PRIMARY KEY AUTOINCREMENT,
    compania    TEXT    NOT NULL
                    CHECK (compania IN ('Telcel', 'Movistar', 'Unefon', 'AT&T')),
    monto       REAL    NOT NULL,
    fecha       TEXT    NOT NULL   -- ISO 8601: YYYY-MM-DD HH:MM:SS (timestamp completo)
);
```

| Campo      | Nota                                                                          |
| ---------- | ----------------------------------------------------------------------------- |
| `compania` | Enum fijo. Ortografía correcta: `Unefon` (no `Unifon`).                      |
| `monto`    | Float. Sin validación de tope — la operadora captura el monto real.           |
| `fecha`    | Timestamp completo. El backend lo autogenera — la operadora no lo captura.    |

---

### Menú Recargas

El botón `Recargas` en el `main_menu` abre **directamente** la ventana de registro
(sin modal intermedio — es operación única).

#### Ventana — Registro de Recarga Telefónica

```yaml
titulo_ventana: Registro de Recargas Telefónicas
campos:
  - etiqueta: Compañía
    modelo: compania
    tipo: Enum
    control: select
    opciones: [Telcel, Movistar, Unefon, AT&T]
    requerido: true
  - etiqueta: Monto
    modelo: monto
    tipo: Float
    requerido: true
campos_autogenerados:
  - columna: fecha
    estrategia: timestamp_actual
    formato: YYYY-MM-DD HH:MM:SS
```

**Botón Guardar:**

- `INSERT` en `recargas`. `fecha` la genera el backend.
- En éxito: `"Recarga registrada."` y limpia el formulario (la operadora puede registrar varias seguidas sin cerrar la ventana).
- En error: `"No se pudo guardar. Intenta de nuevo."`

**Consulta de totales (pie de ventana, lectura rápida):**

```sql
SELECT compania, COUNT(*) AS qty, SUM(monto) AS total
FROM recargas
WHERE DATE(fecha) = DATE('now')
GROUP BY compania;
```

Se muestra como resumen del día actual. Sin filtros adicionales en MVP.

---

## Módulo Consulta Global

> El botón `Consulta` en `main_menu` abre una ventana administrativa de **solo lectura**.
> No reemplaza la **Consulta Historial** del módulo Clientes (esa es por cliente individual).
> Esta ventana responde preguntas del negocio en agregado.

Se implementan exactamente tres consultas en MVP. El módulo está diseñado para sumar más
sin refactoring — cada consulta es una vista independiente seleccionable desde pestañas
o selector.

---

### Consulta 1 — Ventas totales por período

**Pregunta:** ¿Cuánto ingresó la tienda entre dos fechas, en todas las operaciones?

```sql
SELECT
    operacion,
    COUNT(*)   AS cantidad,
    SUM(monto) AS total
FROM movimientos
WHERE DATE(fecha) BETWEEN :fecha_inicio AND :fecha_fin
  AND operacion != 'gasto'
GROUP BY operacion

UNION ALL

SELECT
    'TOTAL' AS operacion,
    COUNT(*),
    SUM(monto)
FROM movimientos
WHERE DATE(fecha) BETWEEN :fecha_inicio AND :fecha_fin
  AND operacion != 'gasto';
```

**UI:** dos date pickers (de / hasta) + tabla resultado + total consolidado.

---

### Consulta 2 — Ventas por segmento en período

**Pregunta:** ¿Cómo se distribuyen los ingresos entre Pedidos, Shein, Apartados, Inventario y Recargas en un período?

```sql
-- Movimientos de caja (contado desde catálogo, apartados, abonos)
SELECT 'Caja'     AS segmento, operacion, COUNT(*) AS qty, SUM(monto) AS total
FROM movimientos
WHERE DATE(fecha) BETWEEN :fecha_inicio AND :fecha_fin
GROUP BY operacion

UNION ALL

-- Shein (tabla propia)
SELECT 'Shein'    AS segmento, 'contado' AS operacion, COUNT(*), SUM(monto)
FROM shein_pedidos
WHERE DATE(fecha) BETWEEN :fecha_inicio AND :fecha_fin
  AND id_shein_corte IS NOT NULL

UNION ALL

-- Recargas (tabla propia)
SELECT 'Recargas' AS segmento, 'recarga' AS operacion, COUNT(*), SUM(monto)
FROM recargas
WHERE DATE(fecha) BETWEEN :fecha_inicio AND :fecha_fin;
```

**UI:** mismos date pickers que Consulta 1 + tabla con columna Segmento + gráfico de barras simple (opcional, se activa si el frontend lo soporta sin librería adicional).

---

### Consulta 3 — Cartera de clientes por segmento

**Pregunta:** ¿Qué clientes tienen saldo activo, agrupados por colonia o por monto?

```sql
SELECT
    c.colonia,
    COUNT(c.id_cliente) AS clientes_con_saldo,
    SUM(c.saldo)        AS saldo_total_colonia,
    AVG(c.saldo)        AS saldo_promedio
FROM clientes c
WHERE c.saldo > 0
  AND c.estatus = 'activo'
GROUP BY c.colonia
ORDER BY saldo_total_colonia DESC;
```

Consulta cruzada adicional (cliente × historial):

```sql
-- Clientes activos con su último movimiento registrado
SELECT
    c.no_cliente,
    c.nombre,
    c.colonia,
    c.saldo,
    c.fecha_pago_programada,
    MAX(m.fecha) AS ultimo_movimiento
FROM clientes c
LEFT JOIN movimientos m ON c.id_cliente = m.id_cliente
WHERE c.saldo > 0
GROUP BY c.id_cliente
ORDER BY c.fecha_pago_programada ASC NULLS LAST;
```

**UI:** tabla filtrable por `colonia` + indicador de bandera (🔴 / 🟡) heredado del
sistema de banderas del Módulo Clientes.

---

## Autenticación y Configuración

---

### Autenticación

Al abrir `pos-boutique` se presenta la ventana de login.

> **Estado actual:** la autenticación está **activa**. Todos los endpoints están
> protegidos con `Depends(get_current_user)`. `config.py` no tiene flag `AUTH_ENABLED`.
> La sesión se maneja con JWT real (`python-jose`). No se desactiva en MVP.

**Campos:**

| Etiqueta   | Modelo     | Tipo   | Reglas                                                   |
| ---------- | ---------- | ------ | -------------------------------------------------------- |
| Usuario    | `usuario`  | String | 4 a 16 caracteres. Sin espacios.                         |
| Contraseña | `password` | String | 4 a 10 caracteres. Al menos una mayúscula. Input oculto. |

**Tabla `usuarios`:**

```sql
CREATE TABLE usuarios (
    id_usuario    INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario       TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,   -- bcrypt. Nunca texto plano.
    rol           TEXT    NOT NULL DEFAULT 'estandar'
                      CHECK (rol IN ('estandar', 'admin')),
    activo        INTEGER NOT NULL DEFAULT 1   -- 1 = activo, 0 = desactivado
);
```

**Usuarios iniciales (seed):**

```python
# backend/db/seed.py
usuarios = [
    {"usuario": "sonia",     "password": "Cassandre", "rol": "estandar"},
    {"usuario": "operador2", "password": "Cambiar1",  "rol": "estandar"}
]
```

**Notas de seguridad:**
- Las contraseñas se almacenan como hash `bcrypt`. Nunca en texto plano.
- La sesión se maneja con JWT. El token se genera al hacer login y se incluye en cada request al backend vía header `Authorization: Bearer <token>`.
- No hay recuperación de contraseña por correo — el sistema opera offline. La recuperación la hace el desarrollador directamente en la DB.

---

### Módulo Setting

Botón `⚙️` visible en el Panel Principal. Abre una ventana de configuración del sistema.
Es un esqueleto funcional en MVP — no se construye flujo complejo hasta que el sistema
esté en producción.

#### Opciones disponibles

```yaml
titulo_ventana: Configuración del Sistema
secciones:
  - titulo: Usuarios
    opciones:
      - Agregar nuevo usuario
      - Cambiar contraseña
      - Cambiar rol de usuario   # solo edición de enum; sin lógica de permisos diferenciada en MVP
  - titulo: Información del sistema
    campos:
      - Zona horaria: heredada del sistema operativo. Solo lectura. Informativo.
  - titulo: Métodos de pago
    descripcion: Activa o desactiva las formas de pago disponibles en el Panel Principal.
    controles:
      - Efectivo:               activo, no desactivable
      - Transferencia bancaria: activo. Campo editable para CLABE.
                                Permite agregar múltiples CLABE (ej: BBVA + Banamex).
      - Tarjeta débito:         activo por defecto. Puede desactivarse.
      - Tarjeta crédito:        activo por defecto. Puede desactivarse.
      - Meses sin intereses (MSI): bloqueado por defecto. Puede activarse.
      - Vales:                  bloqueado por defecto. Puede activarse.
```

**Tabla `configuracion`:**

```sql
CREATE TABLE configuracion (
    clave   TEXT PRIMARY KEY,
    valor   TEXT NOT NULL
);

-- Valores iniciales (seed):
-- ('pago_efectivo_activo',        '1')
-- ('pago_transferencia_activo',   '1')
-- ('pago_tarjeta_debito_activo',  '1')
-- ('pago_tarjeta_credito_activo', '1')
-- ('pago_msi_activo',             '0')
-- ('pago_vales_activo',           '0')
-- ('clabe_1',                     '')
-- ('clabe_2',                     '')
-- ('zona_horaria',                'America/Mexico_City')
```

> Los permisos diferenciados entre `estandar` y `admin` se implementan en versiones futuras.
> La entidad `rol` ya existe en DB — cuando llegue el momento solo se añade lógica de
> verificación en el backend sin cambio de esquema.

---

## Resumen de tablas del sistema

| Tabla              | Módulo               | Relaciones principales                               |
| ------------------ | -------------------- | ---------------------------------------------------- |
| `clientes`         | Clientes             | Referenciada por `pedidos`, `movimientos`            |
| `pedidos`          | Pedidos              | FK → `clientes`                                      |
| `pedidos_articulos`| Pedidos              | FK → `pedidos`, autorreferencia para `rol`           |
| `precios_catalogo` | Pedidos              | Sin FK — lookup por `proveedor` + `id_producto`      |
| `inventario`       | Inventario           | Referenciada por `movimientos`                       |
| `movimientos`      | Panel Principal      | FK → `clientes`, FK → `inventario`                   |
| `shein_clientes`   | Shein                | Independiente de `clientes`                          |
| `shein_pedidos`    | Shein                | FK → `shein_clientes`, FK → `shein_cortes`           |
| `shein_cortes`     | Shein                | Independiente                                        |
| `recargas`         | Recargas Telefónicas | Independiente                                        |
| `usuarios`         | Autenticación        | Independiente                                        |
| `configuracion`    | Setting              | Independiente                                        |

> **Siguiente paso:** con este documento el mapa del sistema está completo.
> El siguiente documento de la secuencia es la especificación de la API REST
> (`docs/API.md`): endpoints, schemas Pydantic, respuestas de error y orden de
> implementación recomendado.
