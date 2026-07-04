## Módulo Shein

> **Naturaleza del módulo:** la boutique actúa como intermediaria. El cliente solicita
> uno o varios artículos vistos en la app de Shein. La tienda ejecuta la compra, la
> entrega y cobra al mismo precio de la app. Siempre de contado. Sin devoluciones.
>
> **Corrección de diseño respecto a la versión anterior:** `shein_pedidos` deja de ser
> una tabla plana de un artículo por renglón. Adopta la misma estructura cabecera-detalle
> que `pedidos` / `pedidos_articulos` (ver [Módulo Pedidos](#módulo-pedidos)): un
> `shein_pedido` es una cabecera con 1 a 4 artículos en `shein_pedidos_articulos`.
> A diferencia de Pedidos, **Shein no maneja artículo alternativo** — no aplica `rol`
> ni `id_articulo_principal`.
>
> El valor que aporta `pos-boutique` en este módulo es triple: registro limpio de cada
> solicitud individual, resolución transparente de variaciones de precio con el cliente,
> y trazabilidad de dónde está el dinero del negocio entre `fecha_corte` y el cobro final
> a cada cliente.

---

### Decisiones de diseño — Shein

**Cartera propia vs. tabla `clientes`.**
Los clientes de Shein son transaccionales: no tienen saldo, no tienen garante, no tienen
`frecuencia_pago`. Forzarlos en `clientes` introduciría datos obligatorios que no aplican
y contaminaría la cartera de crédito. Decisión: tabla independiente `shein_clientes` con
los campos mínimos necesarios.

**Cabecera-detalle, sin alternativa.**
El diseño anterior limitaba un `shein_pedido` a un solo artículo. Se reestructura
siguiendo el mismo patrón de `pedidos` / `pedidos_articulos`: `shein_pedidos` es la
cabecera (1 a 4 artículos, solo el primero obligatorio) y `shein_pedidos_articulos` es
el detalle. Se descarta deliberadamente el concepto de alternativa — Shein no tiene esa
funcionalidad operativa.

**`cupon` — de dónde sale y dónde vive.**
El bono (renombrado `cupon`) no se estima con un porcentaje interno como en el diseño
anterior. Shein lo determina externamente con sus propios cálculos y la tienda lo obtiene
junto con `total_ticket` al momento de pagar en caja OXXO. Por expertise de RDBMS se
decide almacenar `total_ticket` (el dato que sí capturamos directamente en caja) y
derivar `cupon = suma_pedidos - total_ticket`, calculado y persistido por el backend en
el mismo momento — el mismo patrón que ya usaba `bono_monto` en el diseño anterior, solo
que ahora sin `porcentaje_bono`.

**`estatus_pago` vive en el pedido, no en el cliente.**
Un cliente Shein puede tener pedidos en distintos cortes con distinto estatus de cobro
simultáneamente. Colocar `estatus_pago` en `shein_clientes` perdería esa granularidad.

**Variación de precio — corrección de negocio.**
El diseño anterior asumía que solo una subida de precio requería confirmación del
cliente ("si baja, la tienda absorbe la diferencia"). Esto es incorrecto: **tanto una
baja como una subida** de precio requieren notificar al cliente y obtener su
confirmación explícita del artículo al precio actualizado.

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

| Campo              | Nota                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `id_shein_cliente` | PK interna. Identificador operativo visible en UI como consecutivo. |
| `nombre`           | Nombre completo. Máximo 20 caracteres.                              |
| `colonia`          | Máximo 12 caracteres.                                               |
| `telefono`         | 10 dígitos. Obligatorio. Sin guiones ni espacios.                   |

> Esta tabla es independiente de `clientes`. No existe FK entre ellas. Un cliente que
> tenga crédito en la tienda y también compre por Shein tiene registros en ambas tablas
> — eso es correcto y no genera inconsistencia.

#### Tabla `shein_pedidos` (cabecera)

Equivalente a `pedidos` en el [Módulo Pedidos](#módulo-pedidos): solo agrupa artículos
bajo un cliente y una fecha. La asignación a un corte y el estatus de cobro viven aquí,
no en el detalle.

```sql
CREATE TABLE shein_pedidos (
    id_shein_pedido   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_shein_cliente  INTEGER NOT NULL REFERENCES shein_clientes(id_shein_cliente),
    id_shein_corte    INTEGER REFERENCES shein_cortes(id_shein_corte),
                      -- NULL mientras el pedido no ha sido asignado a un corte.
    estatus_pago      TEXT    CHECK (estatus_pago IN ('pago_pendiente', 'pagado')),
                      -- NULL hasta que el corte se guarda. Ver Opción 4 — Registrar Corte.
    fecha             TEXT    NOT NULL   -- ISO 8601: YYYY-MM-DD. Autogenerado al guardar.
);
```

| Campo             | Nota                                                                                                                                              |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id_shein_pedido` | PK interna. No aparece en UI — se muestra como consecutivo (`#1`, `#2`...).                                                                       |
| `id_shein_corte`  | `NULL` mientras el pedido está pendiente de corte. Se asigna al guardar un corte, y solo si el pedido conserva al menos un artículo `confirmado`. |
| `estatus_pago`    | `NULL` hasta que el corte se guarda → `pago_pendiente` → `pagado` conforme el cliente paga. Vive aquí, no en `shein_clientes`.                    |
| `fecha`           | Fecha de creación del pedido (momento en que el cliente solicita el primer artículo).                                                             |

#### Tabla `shein_pedidos_articulos` (detalle)

Cada pedido tiene entre 1 y 4 artículos. Sin concepto de alternativa — cada renglón es
un artículo independiente que el cliente solicitó.

```sql
CREATE TABLE shein_pedidos_articulos (
    id_shein_articulo  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_shein_pedido    INTEGER NOT NULL REFERENCES shein_pedidos(id_shein_pedido),
    id_articulo        TEXT(20),
                       -- Referencia libre al ID del artículo en la app Shein.
                       -- Informativo, sin catálogo digitalizado, sin FK real.
    producto           TEXT(60) NOT NULL,
                       -- Descripción libre del artículo. Coexiste con id_articulo.
    tipo_producto       TEXT    NOT NULL CHECK (tipo_producto IN ('Nacional', 'Importado')),
                       -- Informativo en MVP. Sin impacto operativo ni de cálculo.
    monto               REAL    NOT NULL,
                       -- Precio en la app Shein al momento en que el cliente solicita el artículo.
    monto_vigente        REAL,
                       -- NULL si el precio no cambió. Se llena solo si cambió al momento
                       -- del corte (sube o baja) — ver regla de resolución abajo.
    estatus_articulo     TEXT    NOT NULL DEFAULT 'vigente'
                            CHECK (estatus_articulo IN ('vigente', 'confirmado', 'cancelado'))
);
```

| Campo               | Nota                                                                                                                                             |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `id_shein_articulo` | PK interna. No aparece en UI.                                                                                                                    |
| `id_shein_pedido`   | FK a cabecera. No aparece en UI.                                                                                                                 |
| `id_articulo`       | Campo que captura el ejecutivo con el ID del artículo tal como aparece en la app Shein. Opcional, informativo, sin lookup.                       |
| `producto`          | Descripción libre. Obligatorio. Coexiste con `id_articulo` — no lo reemplaza.                                                                    |
| `tipo_producto`     | `Nacional` o `Importado`. Obligatorio, informativo, sin impacto operativo declarado en MVP.                                                      |
| `monto`             | Precio capturado al momento de la solicitud del cliente.                                                                                         |
| `monto_vigente`     | Se llena únicamente durante **Registrar Corte**, y solo si el precio en la app cambió respecto a `monto`.                                        |
| `estatus_articulo`  | Controla la resolución del artículo en el corte. Ver [Enum `estatus_articulo` (Shein)](#flujo-de-variación-de-precios-y-cancelación-en-cascada). |

#### Tabla `shein_cortes`

```sql
CREATE TABLE shein_cortes (
    id_shein_corte  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_corte     TEXT    NOT NULL,   -- ISO 8601: YYYY-MM-DD.
    total_pedidos   INTEGER NOT NULL,   -- shein_pedidos incluidos (>=1 artículo confirmado).
    suma_pedidos    REAL    NOT NULL,   -- Suma de monto_pedido de todos los pedidos incluidos.
    total_ticket    REAL    NOT NULL,   -- Lo efectivamente pagado en caja OXXO. Captura manual.
    cupon           REAL    NOT NULL    -- suma_pedidos - total_ticket. Calculado por backend.
);
```

> `porcentaje_bono` y `bono_monto` del diseño anterior quedan obsoletos. `cupon` no se
> estima con un porcentaje interno — lo determina Shein y se obtiene junto con
> `total_ticket` al pagar en OXXO, en la misma acción de guardar el corte.

**Cálculo de `monto_pedido` (no es columna, se deriva por consulta):**

```sql
-- Monto de un shein_pedido: suma de sus artículos confirmado, usando el precio
-- vigente si cambió, o el original si no.
SELECT
    id_shein_pedido,
    SUM(COALESCE(monto_vigente, monto)) AS monto_pedido
FROM shein_pedidos_articulos
WHERE estatus_articulo = 'confirmado'
GROUP BY id_shein_pedido;
```

`suma_pedidos` en `shein_cortes` es la suma de `monto_pedido` de todos los pedidos
incluidos en ese corte — sí se almacena, igual que hacía `bono_monto` en el diseño
anterior.

---

### Menú Shein

El botón `Shein` en el `main_menu` abre una ventana emergente con cinco opciones.

```yaml
titulo_ventana: Shein
opciones:
  1: Registrar Cliente Shein
  2: Registrar Pedido Shein
  3: Lista de Pedidos
  4: Registrar Corte
  5: Consulta de Cortes
```

#### Opción 1 — Registrar Cliente Shein

Formulario de alta. Escribe en tabla `shein_clientes`. Sin cambios respecto al diseño
anterior.

| Etiqueta | Modelo     | Tipo    | Longitud | Requerido |
| -------- | ---------- | ------- | -------- | --------- |
| Nombre   | `nombre`   | String  | 20       | ✅         |
| Colonia  | `colonia`  | String  | 12       | ✅         |
| Teléfono | `telefono` | Integer | 10       | ✅         |

- En éxito: `"Cliente Shein registrado correctamente."` y limpia el formulario.
- En error: `"No se pudo guardar. Intenta de nuevo."`

#### Opción 2 — Registrar Pedido Shein

**Paso 1 — Buscar cliente:**

Campo de búsqueda `id_shein_cliente` (consecutivo visible en UI) o `nombre` (búsqueda
parcial). Si no existe: `"Cliente no encontrado. Regístralo primero."` — el formulario
no se abre.

**Paso 2 — Formulario de pedido (1 a 4 artículos):**

Ver detalle completo en [Formulario Registrar Pedido Shein](#formulario-registrar-pedido-shein).
Solo el Artículo 1 es obligatorio; los artículos 2, 3 y 4 están colapsados hasta que el
ejecutivo los activa con **"+ Agregar artículo"**.

- `fecha` de la cabecera se autogenera con la fecha actual (ISO 8601).
- `id_shein_corte` y `estatus_pago` se insertan como `NULL`.
- Cada renglón de artículo se inserta con `estatus_articulo = 'vigente'` y `monto_vigente = NULL`.
- En éxito: `"Pedido Shein registrado."` y cierra el formulario.
- En error: `"No se pudo guardar. Intenta de nuevo."`

> **Pedido editable:** mientras `id_shein_corte IS NULL`, el pedido admite agregar
> artículos opcionales adicionales (hasta 4) o cancelar alguno ya capturado — mismo
> criterio de "editable" que en el Módulo Pedidos.

#### Opción 3 — Lista de Pedidos

Tabla de pedidos pendientes de corte (`id_shein_corte IS NULL`), a nivel **pedido**
(no artículo) — el desglose de artículos se consulta expandiendo el renglón.

| Columna         | Fuente                                                               |
| --------------- | -------------------------------------------------------------------- |
| No. Pedido      | `shein_pedidos.id_shein_pedido`                                      |
| Fecha           | `shein_pedidos.fecha`                                                |
| Cliente         | `shein_clientes.nombre`                                              |
| Total artículos | `COUNT(shein_pedidos_articulos.id_shein_articulo)`                   |
| Monto pedido    | `SUM(monto)` de artículos en `vigente` (aún sin resolver en corte)   |
| Estatus         | `"Pendiente de corte"` — constante mientras `id_shein_corte IS NULL` |

Al expandir un renglón se muestra el detalle: `id_articulo`, `producto`, `tipo_producto`, `monto`.

**Consulta base:**

```sql
SELECT
    sp.id_shein_pedido, sp.fecha, sc.nombre AS cliente,
    COUNT(spa.id_shein_articulo) AS total_articulos,
    SUM(spa.monto) AS monto_pedido
FROM shein_pedidos sp
JOIN shein_clientes sc ON sc.id_shein_cliente = sp.id_shein_cliente
JOIN shein_pedidos_articulos spa ON spa.id_shein_pedido = sp.id_shein_pedido
WHERE sp.id_shein_corte IS NULL
GROUP BY sp.id_shein_pedido
ORDER BY sp.fecha ASC;
```

Filtro rápido por fecha (rango `dd-mm-yyyy` a `dd-mm-yyyy`).

#### Opción 4 — Registrar Corte

Genera un registro en `shein_cortes`, resuelve el estatus de cada artículo revisado y
vincula al corte solo los pedidos que sobreviven la revisión de precio.

**Flujo:**

```
1. Operadora abre Shein > Registrar Corte.
2. El sistema muestra shein_pedidos con id_shein_corte IS NULL (checkboxes, a nivel pedido).
3. Operadora selecciona los pedidos a incluir.
4. Por cada pedido seleccionado, el sistema expande sus artículos en 'vigente'.
5. Operadora verifica el precio actual en la app Shein, artículo por artículo:
     - Si no cambió: no se toca nada — se autoconfirma al guardar.
     - Si cambió: captura monto_vigente. El sistema resalta el renglón y exige
       una resolución explícita una vez el cliente fue consultado:
         · Confirmar  -> el artículo quedará 'confirmado' al guardar
         · Cancelar   -> el artículo quedará 'cancelado' al guardar
6. Si al terminar la revisión un pedido queda sin ningún artículo confirmado
   (todos cancelados), el sistema lo excluye del corte automáticamente:
   no se le asigna id_shein_corte ni estatus_pago. Sin más impacto en la operación.
7. El sistema calcula y muestra: total_pedidos, suma_pedidos.
8. Operadora carga la lista resultante en la app Shein, paga en caja OXXO
   e ingresa total_ticket (obligatorio).
9. El sistema calcula y muestra cupon = suma_pedidos - total_ticket.
10. Operadora confirma.
```

**Transacción al confirmar:**

```sql
-- 1. Resolver artículos con precio revisado (uno o más UPDATE, uno por artículo)
UPDATE shein_pedidos_articulos
SET estatus_articulo = :estatus_resuelto,     -- 'confirmado' o 'cancelado'
    monto_vigente     = :monto_vigente_o_null
WHERE id_shein_articulo = :id_shein_articulo;

-- 2. Autoconfirmar artículos sin cambio de precio dentro de los pedidos seleccionados
UPDATE shein_pedidos_articulos
SET estatus_articulo = 'confirmado'
WHERE id_shein_pedido IN (:ids_pedidos_seleccionados)
  AND estatus_articulo = 'vigente';

-- 3. Insertar el corte
INSERT INTO shein_cortes (fecha_corte, total_pedidos, suma_pedidos, total_ticket, cupon)
VALUES (:fecha_actual, :total_pedidos, :suma_pedidos, :total_ticket,
        :suma_pedidos - :total_ticket);

-- 4. Vincular al corte SOLO los pedidos con al menos un artículo confirmado
UPDATE shein_pedidos
SET id_shein_corte = :id_shein_corte_nuevo,
    estatus_pago   = 'pago_pendiente'
WHERE id_shein_pedido IN (:ids_pedidos_con_articulo_confirmado);
```

- En éxito: `"Corte registrado. Cupón: $X.XX"` y cierra la ventana.
- En error: `"No se pudo registrar el corte. Intenta de nuevo."`

> Los pedidos excluidos por cancelación total nunca reciben `id_shein_corte` — quedan
> visibles únicamente en un histórico de cancelados (fuera del alcance de Lista de
> Pedidos, que solo muestra pendientes) si en el futuro se necesita auditarlos.

#### Opción 5 — Consulta de Cortes

> Responde: **¿dónde está el dinero del negocio en Shein?** — separado de la Consulta
> Global (§10 de `REGLAS_NEGOCIO.md`), que es transversal a todo el sistema.

**Vista 1 — Resumen general (pago_pendiente vs. pagado):**

```sql
SELECT
    sp.estatus_pago,
    COUNT(DISTINCT sp.id_shein_pedido) AS total_pedidos,
    SUM(COALESCE(spa.monto_vigente, spa.monto)) AS monto_total
FROM shein_pedidos sp
JOIN shein_pedidos_articulos spa
    ON spa.id_shein_pedido = sp.id_shein_pedido AND spa.estatus_articulo = 'confirmado'
WHERE sp.id_shein_corte IS NOT NULL
GROUP BY sp.estatus_pago;
```

**UI:** dos tarjetas — "Pago pendiente" y "Pagado" — cada una con cantidad de pedidos y
monto total. Filtro opcional por rango de fechas (`fecha_corte`).

**Vista 2 — Listado de cortes:**

```sql
SELECT
    sc.id_shein_corte, sc.fecha_corte, sc.total_pedidos, sc.suma_pedidos,
    sc.total_ticket, sc.cupon,
    SUM(CASE WHEN sp.estatus_pago = 'pago_pendiente' THEN 1 ELSE 0 END) AS pedidos_pendientes,
    SUM(CASE WHEN sp.estatus_pago = 'pagado'         THEN 1 ELSE 0 END) AS pedidos_pagados
FROM shein_cortes sc
JOIN shein_pedidos sp ON sp.id_shein_corte = sc.id_shein_corte
GROUP BY sc.id_shein_corte
ORDER BY sc.fecha_corte DESC;
```

**UI:** tabla con una fila por `fecha_corte`. Cada fila es expandible.

**Vista 3 — Detalle de un corte (al expandir):**

```sql
SELECT
    sp.id_shein_pedido, sc2.nombre AS cliente, sp.estatus_pago,
    SUM(COALESCE(spa.monto_vigente, spa.monto)) AS monto_pedido
FROM shein_pedidos sp
JOIN shein_clientes sc2 ON sc2.id_shein_cliente = sp.id_shein_cliente
JOIN shein_pedidos_articulos spa
    ON spa.id_shein_pedido = sp.id_shein_pedido AND spa.estatus_articulo = 'confirmado'
WHERE sp.id_shein_corte = :id_shein_corte
GROUP BY sp.id_shein_pedido;
```

**Acción — Marcar como pagado** (por renglón, solo si `estatus_pago = 'pago_pendiente'`):

```sql
UPDATE shein_pedidos SET estatus_pago = 'pagado' WHERE id_shein_pedido = :id_shein_pedido;
```

> El pago de la tienda al proveedor (OXXO) es informativo y no se registra — no hay
> estatus "confirmado → pagado" a nivel `shein_corte`. Lo único que este módulo rastrea
> después de `fecha_corte` es el cobro al cliente.

---

### Formulario Registrar Pedido Shein

Se abre tras validar `id_shein_cliente`. Muestra el nombre del cliente en el encabezado.

Contiene entre 1 y 4 artículos. Solo el Artículo 1 es obligatorio. Los artículos 2, 3 y
4 están colapsados hasta que el ejecutivo los activa (botón **"+ Agregar artículo"**).
Sin concepto de alternativa — cada artículo es un renglón independiente.

**Campos por renglón de artículo:**

| Etiqueta          | Modelo          | Tipo           | Requerido | Nota                                                                                                                                                                                                                                                   |
| ----------------- | --------------- | -------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ID Artículo       | `id_articulo`   | String(20)     | No        | Referencia libre al ID en la app Shein. Coexiste con `producto`.                                                                                                                                                                                       |
| Producto          | `producto`      | String(60)     | ✅         | Descripción del artículo.                                                                                                                                                                                                                              |
| Tipo Producto     | `tipo_producto` | Enum (select)  | ✅         | `Nacional` \| `Importado`. Informativo en MVP.                                                                                                                                                                                                         |
| Monto             | `monto`         | Float          | ✅         | Precio en la app al momento de la solicitud.                                                                                                                                                                                                           |
| Monto actualizado | `monto_vigente` | Float          | —         | Deshabilitado en este formulario. Solo se habilita en Registrar Corte.                                                                                                                                                                                 |
| Cancelar          | —               | Acción (botón) | —         | Antes de guardar: remueve el renglón opcional. Después de guardado, con el pedido aún editable: cancela el artículo (`estatus_articulo = 'cancelado'`), sujeto a la [cascada de cancelación](#flujo-de-variación-de-precios-y-cancelación-en-cascada). |

**Botón Guardar:**

- `INSERT` en `shein_pedidos` (cabecera) + un `INSERT` por cada renglón de artículo en `shein_pedidos_articulos`.
- `estatus_articulo` se inserta siempre como `vigente`; `monto_vigente` siempre `NULL`.
- `id_shein_corte` y `estatus_pago` de la cabecera se insertan como `NULL`.
- Ningún saldo de cliente se modifica — Shein siempre es de contado, sin cartera de crédito.
- En éxito: `"Pedido Shein registrado."` y cierra el formulario.
- En error: `"No se pudo guardar. Intenta de nuevo."`

---

### Flujo de variación de precios y cancelación en cascada

> **Estado:** solución viable implementada en MVP (columnas `monto_vigente` +
> `estatus_articulo`). Solución automatizada de scraping/API fuera de presupuesto en
> esta etapa.

**Situación:**
El `monto` registrado en `shein_pedidos_articulos` corresponde al precio de la app al
momento en que el cliente solicita el artículo. Entre ese momento y el día del corte,
el precio puede haber cambiado — hacia arriba o hacia abajo.

**Corrección respecto al diseño anterior:** ya no importa la dirección del cambio.
**Cualquier variación** (sube o baja) exige notificar al cliente y obtener su
confirmación explícita del artículo al precio actualizado.

**Enum `estatus_articulo` (Shein):**

| Valor        | Cuándo se asigna                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------------------ |
| `vigente`    | Al registrar el pedido. Artículo pendiente de pasar por un corte.                                            |
| `confirmado` | En Registrar Corte: automático si el precio no cambió; manual si cambió y el cliente aceptó el nuevo precio. |
| `cancelado`  | En Registrar Corte: el precio cambió y el cliente no aceptó el nuevo precio.                                 |

**Cascada de cancelación:**

```
1. Se revisan los artículos vigentes de un shein_pedido durante Registrar Corte.
2. Cada artículo se resuelve a 'confirmado' o 'cancelado'.
3. Si TODOS los artículos del pedido terminan 'cancelado':
      → el pedido completo se considera cancelado.
      → NO se le asigna id_shein_corte ni estatus_pago.
      → sin ningún otro impacto en la operación (no hay saldo que revertir:
        Shein nunca cargó nada a ningún saldo).
4. Si el pedido conserva AL MENOS UN artículo 'confirmado':
      → el pedido continúa vivo.
      → se le asigna id_shein_corte y estatus_pago = 'pago_pendiente'.
      → monto_pedido se calcula usando únicamente los artículos 'confirmado'.
```

Este es el motivo por el que `monto_pedido` y `suma_pedidos` se calculan siempre
filtrando `estatus_articulo = 'confirmado'` — un artículo `cancelado` nunca contribuye
al monto del corte.

---

### Schema JSON completo — Shein

```json
{
  "main_menu": {
    "botones": [
      {
        "id": "btn_shein",
        "etiqueta": "Shein",
        "accion": { "tipo": "abrir_modal", "modal": "modal_shein" }
      }
    ]
  },
  "modales": [
    {
      "id": "modal_shein",
      "titulo": "Shein",
      "tipo": "menu_opciones",
      "opciones": [
        { "id": 1, "etiqueta": "Registrar Cliente Shein", "accion": { "tipo": "abrir_ventana", "ventana": "ventana_registrar_cliente_shein" } },
        { "id": 2, "etiqueta": "Registrar Pedido Shein",  "accion": { "tipo": "abrir_modal",   "modal": "modal_busqueda_cliente_shein" } },
        { "id": 3, "etiqueta": "Lista de Pedidos",        "accion": { "tipo": "abrir_ventana", "ventana": "ventana_lista_pedidos_shein" } },
        { "id": 4, "etiqueta": "Registrar Corte",         "accion": { "tipo": "abrir_ventana", "ventana": "ventana_registrar_corte_shein" } },
        { "id": 5, "etiqueta": "Consulta de Cortes",      "accion": { "tipo": "abrir_ventana", "ventana": "ventana_consulta_cortes_shein" } }
      ]
    },
    {
      "id": "modal_busqueda_cliente_shein",
      "titulo": "Registrar Pedido Shein",
      "tipo": "busqueda_previa",
      "campo_busqueda": { "etiqueta": "Cliente Shein", "modelo": "id_shein_cliente_o_nombre", "tipo": "String", "requerido": true },
      "validacion": { "tabla": "shein_clientes", "en_error": "Cliente no encontrado. Regístralo primero." },
      "boton": { "etiqueta": "Continuar", "accion": { "tipo": "abrir_ventana", "ventana": "ventana_registrar_pedido_shein" } }
    }
  ],
  "ventanas": [
    {
      "id": "ventana_registrar_cliente_shein",
      "titulo": "Registrar Cliente Shein",
      "campos": [
        { "etiqueta": "Nombre",   "modelo": "nombre",   "tipo": "String",  "longitud": 20, "requerido": true },
        { "etiqueta": "Colonia",  "modelo": "colonia",  "tipo": "String",  "longitud": 12, "requerido": true },
        { "etiqueta": "Teléfono", "modelo": "telefono", "tipo": "Integer", "longitud": 10, "requerido": true }
      ],
      "acciones": [
        {
          "id": "btn_guardar", "etiqueta": "Guardar", "tipo": "button", "variante": "primary",
          "accion": {
            "tipo": "db_insert", "tabla": "shein_clientes",
            "en_exito": { "mensaje": "Cliente Shein registrado correctamente.", "limpiar_formulario": true },
            "en_error": { "mensaje": "No se pudo guardar. Intenta de nuevo." }
          }
        }
      ]
    },
    {
      "id": "ventana_registrar_pedido_shein",
      "titulo": "Registrar Pedido Shein",
      "encabezado": { "campo": "nombre", "fuente": "shein_clientes" },
      "articulos": {
        "minimo": 1, "maximo": 4,
        "articulo_template": {
          "campos": [
            { "etiqueta": "ID Artículo",       "modelo": "id_articulo",   "tipo": "String", "longitud": 20, "requerido": false },
            { "etiqueta": "Producto",          "modelo": "producto",     "tipo": "String", "longitud": 60, "requerido": true },
            {
              "etiqueta": "Tipo Producto", "modelo": "tipo_producto", "tipo": "Enum", "control": "select", "requerido": true,
              "opciones": [
                { "valor": "Nacional",  "etiqueta": "Nacional"  },
                { "valor": "Importado", "etiqueta": "Importado" }
              ]
            },
            { "etiqueta": "Monto",             "modelo": "monto",         "tipo": "Real", "requerido": true },
            { "etiqueta": "Monto actualizado", "modelo": "monto_vigente", "tipo": "Real", "requerido": false, "habilitado": false, "nota": "Solo se habilita en la ventana Registrar Corte." }
          ],
          "acciones_renglon": [
            { "id": "btn_cancelar_articulo", "etiqueta": "Cancelar", "tipo": "button", "variante": "danger" }
          ]
        },
        "activacion_articulos_opcionales": { "etiqueta_boton": "+ Agregar artículo" }
      },
      "acciones": [
        {
          "id": "btn_guardar", "etiqueta": "Guardar", "tipo": "button", "variante": "primary",
          "accion": {
            "tipo": "db_insert_relacional",
            "nota": "Ningún saldo de cliente se modifica — Shein es siempre de contado.",
            "tablas": [
              {
                "tabla": "shein_pedidos",
                "campos_autogenerados": [{ "columna": "fecha", "estrategia": "fecha_actual", "formato_almacenamiento": "YYYY-MM-DD" }],
                "valores_default": [
                  { "columna": "id_shein_corte", "valor": null },
                  { "columna": "estatus_pago",   "valor": null }
                ]
              },
              {
                "tabla": "shein_pedidos_articulos",
                "descripcion": "Un INSERT por renglón de artículo capturado.",
                "clave_foranea": "id_shein_pedido",
                "campos_mapeados": [
                  { "modelo": "id_articulo",   "columna": "id_articulo"   },
                  { "modelo": "producto",      "columna": "producto"      },
                  { "modelo": "tipo_producto", "columna": "tipo_producto" },
                  { "modelo": "monto",         "columna": "monto"         }
                ],
                "valores_default": [
                  { "columna": "estatus_articulo", "valor": "vigente" },
                  { "columna": "monto_vigente",     "valor": null }
                ]
              }
            ],
            "en_exito": { "mensaje": "Pedido Shein registrado.", "cerrar_ventana": true },
            "en_error": { "mensaje": "No se pudo guardar. Intenta de nuevo." }
          }
        }
      ]
    },
    {
      "id": "ventana_lista_pedidos_shein",
      "titulo": "Lista de Pedidos",
      "tabla_resultado": {
        "columnas": ["id_shein_pedido", "fecha", "cliente", "total_articulos", "monto_pedido", "estatus"],
        "filtro": "id_shein_corte IS NULL",
        "ordenado_por": ["fecha ASC"],
        "expandible": { "descripcion": "Muestra id_articulo, producto, tipo_producto, monto por renglón." }
      }
    },
    {
      "id": "ventana_registrar_corte_shein",
      "titulo": "Registrar Corte",
      "paso_1": {
        "tipo": "tabla_seleccionable",
        "titulo": "Selecciona los pedidos a incluir",
        "fuente": { "tabla": "shein_pedidos", "filtro": "id_shein_corte IS NULL" },
        "seleccion": "multiple",
        "expandible_por_pedido": {
          "columnas": ["id_articulo", "producto", "tipo_producto", "monto", "monto_vigente"],
          "campo_editable": "monto_vigente",
          "resaltado": "monto_vigente IS NOT NULL AND monto_vigente != monto",
          "acciones_renglon": [
            { "id": "btn_confirmar_articulo", "etiqueta": "Confirmar", "variante": "primary" },
            { "id": "btn_cancelar_articulo",  "etiqueta": "Cancelar",  "variante": "danger"  }
          ]
        }
      },
      "resumen": { "campos_calculados": ["total_pedidos", "suma_pedidos"] },
      "paso_2": {
        "tipo": "captura_pago",
        "campos": [
          { "etiqueta": "Total ticket (OXXO)", "modelo": "total_ticket", "tipo": "Real", "requerido": true }
        ],
        "campo_calculado": { "etiqueta": "Cupón", "formula": "suma_pedidos - total_ticket" }
      },
      "acciones": [
        {
          "id": "btn_confirmar_corte", "etiqueta": "Confirmar Corte", "tipo": "button", "variante": "primary",
          "accion": {
            "tipo": "transaccion",
            "pasos": [
              { "operacion": "UPDATE_MASIVO", "tabla": "shein_pedidos_articulos", "descripcion": "Aplica estatus_articulo y monto_vigente resueltos por el usuario, renglón por renglón." },
              { "operacion": "UPDATE", "tabla": "shein_pedidos_articulos", "set": { "estatus_articulo": "confirmado" }, "where": "id_shein_pedido IN (:ids_seleccionados) AND estatus_articulo = 'vigente'" },
              { "operacion": "INSERT", "tabla": "shein_cortes", "campos": ["fecha_corte", "total_pedidos", "suma_pedidos", "total_ticket", "cupon"] },
              { "operacion": "UPDATE", "tabla": "shein_pedidos", "set": { "id_shein_corte": ":id_shein_corte_nuevo", "estatus_pago": "pago_pendiente" }, "where": "id_shein_pedido IN (:ids_pedidos_con_articulo_confirmado)" }
            ],
            "en_exito": { "mensaje": "Corte registrado. Cupón: $X.XX", "cerrar_ventana": true },
            "en_error": { "mensaje": "No se pudo registrar el corte. Intenta de nuevo." }
          }
        }
      ]
    },
    {
      "id": "ventana_consulta_cortes_shein",
      "titulo": "Consulta de Cortes",
      "vista_resumen": {
        "descripcion": "Tarjetas pago_pendiente vs pagado, cantidad y monto. Filtro opcional por rango de fecha_corte.",
        "campos": ["estatus_pago", "total_pedidos", "monto_total"]
      },
      "vista_cortes": {
        "columnas": ["fecha_corte", "total_pedidos", "suma_pedidos", "total_ticket", "cupon", "pedidos_pendientes", "pedidos_pagados"],
        "ordenado_por": ["fecha_corte DESC"],
        "expandible_por_corte": {
          "columnas": ["id_shein_pedido", "cliente", "monto_pedido", "estatus_pago"],
          "accion_renglon": {
            "etiqueta": "Marcar pagado",
            "visible_si": { "estatus_pago": "pago_pendiente" },
            "accion": { "tipo": "db_update", "tabla": "shein_pedidos", "set": { "estatus_pago": "pagado" } }
          }
        }
      }
    }
  ]
}
```

---

