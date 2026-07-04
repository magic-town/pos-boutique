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

| Pestaña       | Campo identificador | Campo precio   | Campo base    | Formato `fecha`        |
| ------------- | ------------------- | -------------- | ------------- | ---------------------- |
| `price_shoes` | `ID`                | `precio_venta` | `Sug_credito` | texto `"02-mayo-2026"` |
| `pakar`       | `CÓDIGO`            | `precio_venta` | `2 PAGO`      | texto `"02-mayo-2026"` |
| `cklass`      | `modelo`            | `precio_venta` | `precio_base` | ISO `YYYY-MM-DD`       |

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

Cada artículo captura un renglón `principal` y, opcionalmente, su
`alternativa` (botón **"+ Agregar alternativa"**). Si `proveedor = Price_Shoes`
en el principal, el botón puede presionarse hasta 3 veces (3 alternativas);
para cualquier otro proveedor o `tipo_producto = informal`, el botón
desaparece después de la primera alternativa (máximo 1). Todas se guardan
como filas independientes
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
              { "etiqueta": "Producto", "modelo": "producto", "tipo": "String", "longitud": 40, "requerido": true },
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
