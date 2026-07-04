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

