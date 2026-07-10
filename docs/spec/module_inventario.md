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
    marca             TEXT(20),
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

| Estatus actual           | Transiciones permitidas                                            |
| ------------------------ | ------------------------------------------------------------------ |
| `disponible`             | → `en_ruta`, → `disponible_c/descuento`, → `apartado`, → `vendido` |
| `disponible_c/descuento` | → `disponible`, → `en_ruta`, → `apartado`, → `vendido`             |
| `en_ruta`                | → `disponible`, → `vendido`                                        |
| `apartado`               | → `disponible` (cancelación), → `vendido` (liquidación)            |
| `vendido`                | — (sin transición posible desde UI)                                |

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
| Marca            | `marca`         | String        | 20       | ❌         |
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
        { "etiqueta": "Marca",         "modelo": "marca",         "tipo": "String",  "longitud": 20, "requerido": false },
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
          "disponible_c_descuento": ["disponible", "en_ruta", "apartado", "vendido"],
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

## Funcionalidad nueva (agregada en esta sesión, no forma parte del spec original)

> Todo lo de aquí en adelante es adición posterior a `00_FULLSTACK_DEVELOPMENT.md`.
> No requirió cambios en `models.py` — `precio_descuento` (nullable) y el
> enum `EstatusInventario.disponible_c/descuento` ya existían en el modelo
> original, sin usarse todavía desde ningún endpoint.

### Carga inicial desde `inventario_bz.ods`

Alimenta la tabla `inventario` en bloque, en vez de capturar producto por
producto vía "Agregar Producto". Uso previsto: alta inicial del inventario
físico existente al arrancar el sistema, y/o cada vez que llega un lote
nuevo de mercancía.

**Columnas esperadas** (mismas de `Modelo de datos — Inventario`; se
confirman/ajustan contra el archivo real cuando se suba con rótulos + 2
registros de muestra, mismo proceso que se siguió con `tabla_precios.ods`):

`categoria`, `tipo_producto`, `descripcion`, `talla`, `color`, `marca`,
`precio_venta`, `stock`.

**Reglas:**

- **Solo `INSERT`, nunca `UPDATE`.** Cada fila del `.ods` se convierte en un
  producto nuevo (`id_producto` autoincremental). Re-subir el mismo archivo
  dos veces crea productos duplicados — no hay una clave natural en el
  `.ods` que permita distinguir "ya existe" de "es nuevo" (a diferencia de
  `tabla_precios.ods`, que se identifica por `proveedor + id_producto +
  fecha_catalogo`). Responsabilidad operativa: correr el script solo cuando
  hay mercancía genuinamente nueva que dar de alta.
- **`precio_descuento` nunca viene del `.ods`.** Es un campo exclusivo del
  sistema (ver más abajo) — el import siempre lo deja en `NULL`, igual que
  "Agregar Producto".
- Mismos valores por defecto que "Agregar Producto": `estatus = 'disponible'`,
  `descripcion_ruta = NULL`, `changed_status = NULL`, `created = fecha actual`.

### Opción 4 — Aplicar Descuento Masivo

Aplica el mismo `precio_descuento` a varios productos en una sola operación,
en vez de repetir "Cambiar Estatus" producto por producto.

**Dos formas de definir el segmento (no excluyentes — se puede combinar filtro + selección manual dentro del resultado filtrado):**

1. **Por filtro de campos:** cualquier combinación de `categoria`,
   `tipo_producto`, `marca`, `talla`, `color`. Ejemplo: "todos los
   `caballero`" o "todos los de `marca = Aspik`".
2. **Por selección manual:** lista explícita de `id_producto` (elegidos
   desde la tabla de Consulta Inventario, ej. checkboxes).

**Valor del descuento — dos formas de capturarlo:**

- **Porcentaje** (`pct`): `precio_descuento = ROUND(precio_venta * (1 - pct/100))` por cada producto (el monto resultante varía por producto, ya que `precio_venta` varía).
- **Precio fijo** (`precio_fijo`): mismo `precio_descuento` para todos los productos del segmento, sin importar su `precio_venta`. Se usa cuando se quiere vender parejo, ej. "$99 toda la ropa rezagada de esta categoría".

**Reglas:**

- Solo aplica a productos en estatus `disponible` (no toca `vendido`,
  `apartado`, `en_ruta` — un producto reservado o fuera de piso no debería
  cambiar de precio silenciosamente).
- Si `precio_fijo >= precio_venta` para algún producto del segmento, ese
  producto se **omite** (no sería un descuento) y se reporta en la
  respuesta — no se aborta la operación completa por un producto fuera de
  rango.
- Transacción única: `UPDATE inventario SET precio_descuento = :valor, estatus = 'disponible_c/descuento', changed_status = :hoy WHERE <filtro> AND estatus = 'disponible'`.
- No existe fecha de expiración — el descuento queda activo hasta que se
  retira manualmente (Opción 5). Decisión explícita: no se programan
  descuentos por fecha.

### Opción 5 — Retirar Descuento Masivo

Simétrico a la Opción 4, mismo mecanismo de segmento (filtro y/o selección
manual). `UPDATE inventario SET precio_descuento = NULL, estatus = 'disponible', changed_status = :hoy WHERE <filtro> AND estatus = 'disponible_c/descuento'`.

Solo revierte productos que estén actualmente `disponible_c/descuento` — un
producto ya vendido o apartado mientras tenía descuento activo conserva su
`precio_descuento` histórico (no se toca retroactivamente).
