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
    dia_pago_especifico    INTEGER,                   -- 1-31. Obligatorio solo si frecuencia_pago = 'dia_especifico_mes'
    frecuencia_pago_detalle TEXT,                      -- Obligatorio solo si frecuencia_pago = 'otro'
    ref_nombre             TEXT    NOT NULL,
    ref_colonia            TEXT    NOT NULL,
    ref_telefono           INTEGER,                   -- 10 dígitos, nullable
    saldo                  REAL    NOT NULL DEFAULT 0,
    estatus                TEXT    NOT NULL DEFAULT 'inactivo'
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
| `dia_pago_especifico`   | Entero 1-31. Obligatorio solo si `frecuencia_pago = dia_especifico_mes`. Se captura una sola vez al registrar y persiste mientras la cuenta esté activa (se edita solo desde **Editar Cliente**). |
| `frecuencia_pago_detalle` | Texto libre, hasta 60 caracteres. Obligatorio solo si `frecuencia_pago = otro`. Documenta el acuerdo especial de pago.                               |
| `ref_telefono`          | Nullable. El teléfono del garante es opcional.                                                                                                         |
| `saldo`                 | Deuda acumulada del cliente. `saldo >= 0` siempre. `saldo > 0` = deuda activa. `saldo = 0` = cuenta liquidada.                                          |
| `estatus`               | Enum `activo` \| `inactivo`. **Derivado automáticamente del `saldo`, nunca editable por la operadora.** Nace `inactivo`. Cambia a `activo` en cuanto un producto impacta el `saldo` del cliente. Cambia a `inactivo` en cuanto el `saldo` regresa a `0`. No bloquea ninguna operación. |
| `fecha_registro`        | Se guarda en `YYYY-MM-DD` (ISO 8601). Se muestra en UI como `DD-MM-YYYY`.                                                                              |
| `fecha_pago_programada` | `NULL` al registrar. Campo calculado internamente: se instancia y recalcula en cada abono en `movimientos`. Nunca se captura ni importa manualmente.   |

---

### Enum `frecuencia_pago`

| Valor                | Descripción                                                                                            | Campo adicional requerido               |
| -------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| `semanal`            | Pago esperado cada 7 días, rodante desde el abono real                                                  | —                                          |
| `quincenal`          | Pago esperado en fechas fijas de calendario: día `15` y último día del mes (28/29/30/31 según el mes)   | —                                          |
| `dia_especifico_mes` | Pago esperado en un día fijo del mes, elegido por la operadora al registrar                              | `dia_pago_especifico` (1-31)              |
| `otro`               | Acuerdo especial; sin cálculo automático de fecha                                                        | `frecuencia_pago_detalle` (texto libre)   |

---

### Enum `estatus`

| Valor      | Descripción                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------- |
| `activo`   | El cliente tiene producto(s) recibido(s) pendiente(s) de liquidar. Se asigna en automático en cuanto un movimiento impacta su `saldo` al alza. |
| `inactivo` | Default al registrar (`saldo = 0`). También el estado al que el sistema regresa en automático en cuanto el cliente liquida su `saldo` a `0`. No implica baja ni bloqueo — la cuenta sigue operando con normalidad. |

> `estatus` es un campo **derivado, nunca editable directamente** — no existe ninguna
> acción, endpoint o pantalla para cambiarlo a mano, ni siquiera desde Editar Cliente.
> Nace `inactivo` con `saldo = 0`. Cambia a `activo` automáticamente en el momento en
> que un producto impacta su `saldo` (lo recibe y acepta). Cambia de vuelta a
> `inactivo` automáticamente en el momento en que su `saldo` regresa a `0` por
> liquidación, sin importar cuántas compras haya tenido antes — el siguiente producto
> que reciba lo regresa a `activo` de nuevo. La operadora únicamente registra al
> cliente y sus movimientos; el sistema mantiene `estatus` sincronizado con `saldo`.

---

### Ciclo de `fecha_pago_programada`

`fecha_pago_programada` no se fija al registrar al cliente — se instancia y
recalcula en cada abono. La **fórmula** de cálculo depende del `frecuencia_pago`
del cliente.

**Reglas:**

1. Al registrar el cliente: `fecha_pago_programada = NULL`, sin importar la frecuencia.
2. Al registrar el **primer abono** en `movimientos` (y en cada abono subsiguiente),
   el backend recalcula `fecha_pago_programada` según el tipo de frecuencia:
   - **`semanal`:** rodante, sin cambios respecto al diseño original.
     `fecha_pago_programada = fecha_abono + 7 días`.
   - **`quincenal`:** deja de ser rodante. Se fija a las fechas de calendario
     `15` y **último día del mes** (28/29/30/31 según corresponda).
     `fecha_pago_programada` = la próxima de esas dos fechas posterior a la
     fecha del abono.
   - **`dia_especifico_mes`:** se fija al día capturado en `dia_pago_especifico`
     (definido una sola vez al registrar al cliente). `fecha_pago_programada`
     = la próxima ocurrencia de ese día posterior a la fecha del abono. Si el
     día no existe en un mes dado (p. ej. `31` en febrero), se aplica el mismo
     *clamp* al último día del mes que usa `quincenal`.
   - **`otro`:** el backend nunca calcula. `fecha_pago_programada` permanece
     `NULL` siempre; el acuerdo especial vive en `frecuencia_pago_detalle`.

**Ejemplo con `frecuencia_pago = semanal`** (sin cambios):

```
Abono 1: 03-01-2026 (sábado)  →  fecha_pago_programada = 10-01-2026
Abono 2: 12-01-2026           →  fecha_pago_programada = 19-01-2026
```

**Ejemplo con `frecuencia_pago = quincenal`** (fechas fijas, ya no rodante):

```
Abono 1: 03-01-2026  →  fecha_pago_programada = 15-01-2026  (próxima fecha fija)
Abono 2: 20-01-2026  →  fecha_pago_programada = 31-01-2026  (último día de enero)
Abono 3: 05-02-2026  →  fecha_pago_programada = 15-02-2026
```

**Ejemplo con `frecuencia_pago = dia_especifico_mes`** y `dia_pago_especifico = 31`:

```
Abono en enero:   fecha_pago_programada = 31-01-2026  (enero tiene 31 días)
Abono en febrero: fecha_pago_programada = 28-02-2026  (clamp: febrero no tiene 31)
```

> El sistema no castiga el retraso: en `semanal` y `dia_especifico_mes`, la
> próxima fecha se recalcula desde el abono real. En `quincenal`, al ser fechas
> fijas de calendario, el atraso simplemente mueve al cliente a la siguiente
> fecha fija disponible.

> **Pendiente de implementación:** esta fórmula se codifica en
> `movimiento_service.py` (ver docs/REPORT.md, punto de ajuste de Movimientos).
> Hoy `dia_pago_especifico` y `frecuencia_pago_detalle` ya se capturan y
> validan en el alta de Cliente.

---

### Sistema de banderas

El sistema evalúa `fecha_pago_programada` de cada cliente activo con saldo para
determinar alertas visuales.

| Bandera     | Condición                                                   | Indicador        |
| ----------- | ----------------------------------------------------------- | ---------------- |
| 🟡 Amarilla  | `fecha_pago_programada - hoy <= 2 días`                     | Próximo a vencer |
| 🔴 Roja      | `hoy > fecha_pago_programada`                               | Vencido          |
| 🟠 Naranja   | Cliente tiene apartado abierto a ≤ 5 días de vencer su mes  | Apartado x vencer|
| Sin bandera | Ninguna de las anteriores, o `fecha_pago_programada = NULL` | Normal           |

**Notas de implementación:**

- La evaluación se ejecuta al cargar el panel principal o el módulo Clientes.
- Clientes con `frecuencia_pago = otro` y `fecha_pago_programada = NULL` no generan bandera amarilla ni roja.
- Clientes con `saldo = 0` no generan bandera amarilla ni roja aunque tengan `fecha_pago_programada` definida.
- La bandera naranja depende de `apartados.fecha_apartado`, es independiente del ciclo normal de abonos y puede coexistir con las otras banderas.
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
| Día de pago específico | `dia_pago_especifico` | Integer (1-31) | — | ✅ solo si `frecuencia_pago = dia_especifico_mes` |
| Detalle de frecuencia  | `frecuencia_pago_detalle` | String | 60 | ✅ solo si `frecuencia_pago = otro` |
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
            },
            {
              "etiqueta": "Día de pago específico",
              "tipo": "Integer", "modelo": "dia_pago_especifico", "control": "select_numero", "min": 1, "max": 31,
              "requerido": true,
              "visible_si": { "campo": "frecuencia_pago", "valor": "dia_especifico_mes" }
            },
            {
              "etiqueta": "Detalle de frecuencia",
              "tipo": "String", "longitud": 60, "modelo": "frecuencia_pago_detalle", "control": "text",
              "requerido": true,
              "visible_si": { "campo": "frecuencia_pago", "valor": "otro" }
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
              { "modelo": "dia_pago_especifico", "columna": "dia_pago_especifico" },
              { "modelo": "frecuencia_pago_detalle", "columna": "frecuencia_pago_detalle" },
              { "modelo": "ref_nombre",      "columna": "ref_nombre"      },
              { "modelo": "ref_colonia",     "columna": "ref_colonia"     },
              { "modelo": "ref_telefono",    "columna": "ref_telefono"    }
            ],
            "valores_default": [
              { "columna": "saldo",                 "valor": 0        },
              { "columna": "estatus",               "valor": "inactivo" },
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
no_cliente | nombre | colonia | telefono | frecuencia_pago | dia_pago_especifico | frecuencia_pago_detalle | ref_nombre | ref_colonia | ref_telefono | saldo | estatus | fecha_registro
```

- `no_cliente` en formato `{Colonia}-{consecutivo:03d}`.
- `dia_pago_especifico` solo se llena si `frecuencia_pago = dia_especifico_mes`; vacío en los demás casos.
- `frecuencia_pago_detalle` solo se llena si `frecuencia_pago = otro`; vacío en los demás casos.
- `fecha_registro` en formato `YYYY-MM-DD`.
- `estatus` en minúsculas: `activo` o `inactivo`.
- Guardar como `.csv` con codificación `UTF-8`.

**Fase 2 — Primer día de producción (script)**

```bash
python scripts/importar_clientes.py --archivo cartera_inicial.csv --db pos.db
```

El script debe:
- Validar que `no_cliente` sea único antes de insertar.
- Rechazar filas donde `frecuencia_pago = dia_especifico_mes` sin `dia_pago_especifico`,
  o `frecuencia_pago = otro` sin `frecuencia_pago_detalle`.
- Convertir `fecha_registro` si viene en `DD-MM-YYYY`.
- Rechazar filas con `estatus` fuera de `activo | inactivo`.
- Insertar `fecha_pago_programada = NULL` para todos, ignorando cualquier valor en el CSV.
- Reportar errores por fila sin abortar la importación completa.

**Fase 3 — Operación normal**

Clientes nuevos se registran directamente en el formulario. La cartera importada
queda disponible de inmediato en Consulta Cliente y Consulta Historial.

> Importación de única vez. Una vez verificada, el script puede archivarse.

---

