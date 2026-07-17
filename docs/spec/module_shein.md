## Módulo Shein

> **Naturaleza del módulo:** la boutique actúa como intermediaria. El cliente solicita
> uno o varios artículos vistos en la app de Shein. La tienda ejecuta la compra, la
> entrega y cobra al mismo precio de la app. A diferencia del modelo anterior de pago
> de contado en OXXO, los clientes Shein ahora tienen una **cartera de crédito propia**:
> el monto del pedido se carga a su saldo al momento del corte y se liquida mediante
> abonos. Sin devoluciones.
>
> `shein_pedidos` adopta la estructura cabecera-detalle: un `shein_pedido` es una
> cabecera con 1 a 4 artículos en `shein_pedidos_articulos`. **Shein no maneja artículo
> alternativo** — no aplica `rol` ni `id_articulo_principal`.

---

### Decisiones de diseño — Shein

**Cartera propia vs. tabla `clientes`.**
Los clientes de Shein son transaccionales con sus propias condiciones. Forzarlos en
`clientes` introduciría dependencias sobre el módulo de crédito principal y contaminaría
la cartera de crédito de la boutique. Decisión: tabla independiente `shein_clientes` con
cartera de crédito propia, sin FK a `clientes`.

**Cabecera-detalle, sin alternativa.**
`shein_pedidos` es la cabecera (1 a 4 artículos, solo el primero obligatorio) y
`shein_pedidos_articulos` es el detalle. Se descarta el concepto de alternativa —
Shein no tiene esa funcionalidad operativa.

**`cupon` — de dónde sale y dónde vive.**
El bono (`cupon`) no se estima con un porcentaje interno. Shein lo determina externamente
y la tienda lo obtiene junto con `total_ticket` al momento de pagar en caja OXXO.
Se almacena `total_ticket` y se deriva `cupon = suma_pedidos - total_ticket`, calculado
y persistido por el backend al guardar el corte.

**`estatus_pago` vive en el pedido, no en el cliente.**
Un cliente Shein puede tener pedidos en distintos cortes con distinto estatus de cobro
simultáneamente. Colocar `estatus_pago` en `shein_clientes` perdería esa granularidad.

**Variación de precio.**
**Cualquier variación** de precio (sube o baja) exige notificar al cliente y obtener
su confirmación explícita del artículo al precio actualizado. La tienda nunca absorbe
la diferencia en silencio.

**`sku` no es la PK de `shein_pedidos_articulos`.**
`sku` identifica el artículo en el catálogo Shein y es obligatorio en cada renglón —
es la variable que cruza todo el proceso: alta del pedido, resolución de variación de
precio en el corte, y el monto que termina cargado al cliente. Pero el mismo `sku` se
repite en muchos renglones a lo largo del tiempo (mismo artículo, distintos pedidos y
clientes), así que no cumple la unicidad que exige una PK. La PK de la tabla sigue
siendo `id_shein_articulo` — autoincrement, interno, identifica el renglón (la
instancia de "este artículo en este pedido"), no el artículo en sí.

**Saldo y abonos.**
Al guardar un corte, el `monto_pedido` de cada pedido incluido se suma al `saldo` del
`shein_cliente`. Los clientes liquidan vía abonos registrados en `shein_movimientos`.
La cartera Shein sigue las mismas reglas que la cartera principal: `saldo` nunca se
sobreescribe, siempre `+= monto` o `-= monto`.

---

### Modelo de datos — Shein

#### Tabla `shein_clientes`

```sql
CREATE TABLE shein_clientes (
    id_shein_cliente        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre                  TEXT(20) NOT NULL,
    colonia                 TEXT(12) NOT NULL,
    telefono                INTEGER  NOT NULL,          -- 10 dígitos
    frecuencia_pago         TEXT     NOT NULL,          -- Enum: semanal | quincenal | dia_especifico_mes | otro
    dia_pago_especifico     INTEGER,                    -- 1-31. Solo si frecuencia_pago = 'dia_especifico_mes'
    frecuencia_pago_detalle TEXT,                       -- Solo si frecuencia_pago = 'otro'
    saldo                   REAL     NOT NULL DEFAULT 0,
    estatus                 TEXT     NOT NULL DEFAULT 'inactivo'
                                CHECK (estatus IN ('activo', 'inactivo')),
    fecha_pago_programada   TEXT                        -- ISO 8601. NULL hasta el primer abono.
);
```

| Campo                    | Nota                                                                                                            |
| ------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `id_shein_cliente`       | PK interna. Identificador operativo visible en UI como consecutivo.                                             |
| `nombre`                 | Nombre completo. Máximo 20 caracteres.                                                                          |
| `colonia`                | Máximo 12 caracteres.                                                                                           |
| `telefono`               | 10 dígitos. Obligatorio. Sin guiones ni espacios.                                                               |
| `frecuencia_pago`        | Enum. Define la periodicidad esperada de abono.                                                                 |
| `dia_pago_especifico`    | 1-31. Obligatorio solo si `frecuencia_pago = dia_especifico_mes`.                                               |
| `frecuencia_pago_detalle`| Texto libre, hasta 60 caracteres. Obligatorio solo si `frecuencia_pago = otro`.                                 |
| `saldo`                  | Deuda acumulada. `saldo >= 0` siempre. `saldo > 0` = deuda activa. `saldo = 0` = cuenta liquidada.             |
| `estatus`                | Derivado automáticamente del `saldo`, nunca editable. `inactivo` por defecto. Pasa a `activo` cuando hay saldo. |
| `fecha_pago_programada`  | `NULL` hasta el primer abono. Se instancia y recalcula en cada abono según `frecuencia_pago`.                   |

> Esta tabla es independiente de `clientes`. No existe FK entre ellas. Un cliente que
> tenga crédito en la tienda y también compre por Shein tiene registros en ambas tablas —
> eso es correcto y no genera inconsistencia.

#### Tabla `shein_movimientos`

Registro de abonos a la cartera Shein. Tabla independiente de `movimientos`.

```sql
CREATE TABLE shein_movimientos (
    id_shein_movimiento  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_shein_cliente     INTEGER NOT NULL REFERENCES shein_clientes(id_shein_cliente),
    monto                REAL    NOT NULL,
    forma_pago           TEXT    NOT NULL
                             CHECK (forma_pago IN ('efectivo', 'transferencia', 'tarjeta')),
    saldo_resultante     REAL    NOT NULL,
    fecha                TEXT    NOT NULL   -- ISO 8601: YYYY-MM-DD HH:MM:SS
);
```

| Campo                  | Nota                                                                        |
| ---------------------- | --------------------------------------------------------------------------- |
| `id_shein_movimiento`  | PK interna.                                                                 |
| `id_shein_cliente`     | FK al cliente Shein que abona.                                              |
| `monto`                | Monto del abono. Mayor que 0. No puede exceder `shein_clientes.saldo`.      |
| `forma_pago`           | Método de pago. Depende de los métodos activos en `configuracion`.          |
| `saldo_resultante`     | `saldo_shein_cliente - monto` al momento del abono. Informativo.            |
| `fecha`                | Timestamp completo. Autogenerado al registrar.                              |

#### Tabla `shein_pedidos` (cabecera)

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
| `estatus_pago`    | `NULL` hasta que el corte se guarda → `pago_pendiente` (saldo cargado) → `pagado` (saldo liquidado vía abonos). Vive aquí, no en `shein_clientes`.|
| `fecha`           | Fecha de creación del pedido.                                                                                                                     |

#### Tabla `shein_pedidos_articulos` (detalle)

```sql
CREATE TABLE shein_pedidos_articulos (
    id_shein_articulo  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_shein_pedido    INTEGER NOT NULL REFERENCES shein_pedidos(id_shein_pedido),
    sku                TEXT(25) NOT NULL,
    producto           TEXT(60) NOT NULL,
    tipo_producto      TEXT    NOT NULL CHECK (tipo_producto IN ('Nacional', 'Importado')),
    monto              REAL    NOT NULL,
    monto_vigente      REAL,
    estatus_articulo   TEXT    NOT NULL DEFAULT 'vigente'
                           CHECK (estatus_articulo IN ('vigente', 'confirmado', 'cancelado'))
);
```

| Campo               | Nota                                                                                                                    |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `id_shein_articulo` | PK interna, autoincrement. Consecutivo generado por la base de datos al insertar cada renglón — nunca capturado ni mostrado en UI. |
| `id_shein_pedido`   | FK a cabecera. No aparece en UI.                                                                                        |
| `sku`               | Identificador del artículo en el catálogo Shein. Obligatorio. Es la variable que cruza todo el proceso del módulo: con ella se registra y se actualiza el renglón en `shein_pedidos_articulos` (incluida cualquier variación de precio, al alza o a la baja, resuelta en el corte), y el `monto`/`monto_vigente` que termina cargado al `saldo` del cliente está asociado a este `sku`. |
| `producto`          | Descripción libre. Obligatorio.                                                                                         |
| `tipo_producto`     | `Nacional` o `Importado`. Obligatorio, informativo, sin impacto operativo en MVP.                                       |
| `monto`             | Precio capturado al momento de la solicitud del cliente.                                                                |
| `monto_vigente`     | Se llena únicamente durante **Registrar Corte**, y solo si el precio cambió respecto a `monto`.                         |
| `estatus_articulo`  | Controla la resolución del artículo en el corte. Ver [Flujo de variación de precios](#flujo-de-variación-de-precios-y-cancelación-en-cascada). |

#### Tabla `shein_cortes`

```sql
CREATE TABLE shein_cortes (
    id_shein_corte  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_corte     TEXT    NOT NULL,
    total_pedidos   INTEGER NOT NULL,
    suma_pedidos    REAL    NOT NULL,
    total_ticket    REAL    NOT NULL,
    cupon           REAL    NOT NULL
);
```

| Campo           | Nota                                                                                         |
| --------------- | -------------------------------------------------------------------------------------------- |
| `fecha_corte`   | Fecha del corte. ISO 8601.                                                                   |
| `total_pedidos` | Cantidad de `shein_pedidos` incluidos (con al menos 1 artículo `confirmado`). Calculado.     |
| `suma_pedidos`  | Suma de `monto_pedido` de todos los pedidos incluidos. Calculada por backend. Sí se almacena.|
| `total_ticket`  | Lo efectivamente pagado en caja OXXO. Captura manual.                                        |
| `cupon`         | `suma_pedidos - total_ticket`. Calculado por backend al guardar.                              |

**Cálculo de `monto_pedido` (no es columna, se deriva por consulta):**

```sql
SELECT
    id_shein_pedido,
    SUM(COALESCE(monto_vigente, monto)) AS monto_pedido
FROM shein_pedidos_articulos
WHERE estatus_articulo = 'confirmado'
GROUP BY id_shein_pedido;
```

---

### Reglas de negocio

1. **Independencia de `clientes`.** `shein_clientes` no tiene FK a `clientes`. Son carteras separadas que no se mezclan.
2. **Un `shein_pedido` tiene de 1 a 4 artículos.** Solo el primero es obligatorio al crear; los demás se pueden agregar mientras el pedido sea editable (`id_shein_corte IS NULL`, con al menos un artículo en `vigente`).
3. **Cartera de crédito.** Al guardar el corte, el `monto_pedido` de cada pedido incluido se carga al `saldo` del `shein_cliente` (`saldo += monto_pedido`). Si el `estatus` era `inactivo`, cambia a `activo` en la misma transacción. El cliente liquida mediante abonos registrados en `shein_movimientos` (`saldo -= monto_abono`). Si el `saldo` llega a `0`, el `estatus` vuelve a `inactivo` automáticamente.
4. **`estatus` derivado del `saldo`.** Nunca editable manualmente. Misma regla que `clientes.estatus`.
5. **Ciclo de `fecha_pago_programada`.** `NULL` al registrar el cliente. Se instancia y recalcula en cada abono de `shein_movimientos`, con la misma lógica de `frecuencia_pago` que en `clientes` (semanal, quincenal, dia_especifico_mes, otro).
6. **Sistema de banderas.** `bandera_amarilla` (`fecha_pago_programada - hoy <= 2 días`) y `bandera_roja` (`hoy > fecha_pago_programada`) calculadas al vuelo. Visuales, no bloqueantes. Misma semántica que en `clientes`.
7. **Variación de precios.** Cualquier variación (sube o baja) exige notificación al cliente y confirmación explícita.
8. **Resolución de `estatus_articulo` en el corte:**
   - Si el precio no cambió: artículo pasa automáticamente a `confirmado` (`monto_vigente = NULL`).
   - Si el precio cambió y el cliente confirma: `estatus_articulo = 'confirmado'`, `monto_vigente` se llena con el nuevo precio.
   - Si el precio cambió y el cliente cancela: `estatus_articulo = 'cancelado'`.
9. **Cascada de cancelación a nivel pedido:**
   - Si todos los artículos quedan `cancelado`: el pedido no recibe `id_shein_corte` ni `estatus_pago`. Su `monto_pedido` no se carga a ningún saldo.
   - Si al menos un artículo está `confirmado`: el pedido recibe `id_shein_corte`, `estatus_pago = 'pago_pendiente'` y su `monto_pedido` (calculado sobre artículos `confirmado`) se carga al `saldo` del cliente.
10. **`cupon` no se calcula internamente.** Shein lo determina externamente. La tienda obtiene `total_ticket` junto con el cupón al pagar en OXXO — ambos se capturan al guardar el corte.
11. **El proceso de `corte_pedido` no cambia.** La confirmación de artículos, cálculo de `monto_pedido`, `suma_pedidos`, `total_ticket` y `cupon` son idénticos al diseño anterior. El único cambio es que al vincular al corte, el saldo se carga al `shein_cliente`.
12. **Sin script de migración.** No existe tabla ODS ni script de importación para Shein. Todos los clientes se registran directamente en el sistema mediante `Crear Cliente Shein`.

---

### Menú Shein

El botón `Shein` en el `main_menu` abre una ventana emergente con seis opciones.

```yaml
titulo_ventana: Shein
opciones:
  1: Registrar Cliente Shein
  2: Registrar Pedido Shein
  3: Registrar Abono Shein
  4: Lista de Pedidos
  5: Registrar Corte
  6: Consulta de Cortes
```

#### Opción 1 — Registrar Cliente Shein

Formulario de alta. Escribe en tabla `shein_clientes`.

| Etiqueta              | Modelo                    | Tipo    | Longitud | Requerido |
| --------------------- | ------------------------- | ------- | -------- | --------- |
| Nombre                | `nombre`                  | String  | 20       | ✅         |
| Colonia               | `colonia`                 | String  | 12       | ✅         |
| Teléfono              | `telefono`                | Integer | 10       | ✅         |
| Frecuencia de Pago    | `frecuencia_pago`         | Enum    | —        | ✅         |
| Día de pago específico| `dia_pago_especifico`     | Integer | 1-31     | ✅ solo si `frecuencia_pago = dia_especifico_mes` |
| Detalle de frecuencia | `frecuencia_pago_detalle` | String  | 60       | ✅ solo si `frecuencia_pago = otro` |

**Campos autogenerados:** `saldo = 0`, `estatus = 'inactivo'`, `fecha_pago_programada = NULL`.

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

- `fecha` de la cabecera se autogenera con la fecha actual.
- `id_shein_corte` y `estatus_pago` se insertan como `NULL`.
- Cada artículo se inserta con `estatus_articulo = 'vigente'` y `monto_vigente = NULL`.
- En éxito: `"Pedido Shein registrado."` y cierra el formulario.
- En error: `"No se pudo guardar. Intenta de nuevo."`

> **Pedido editable:** mientras `id_shein_corte IS NULL`, el pedido admite agregar
> artículos opcionales adicionales (hasta 4) o cancelar alguno ya capturado.

#### Opción 3 — Registrar Abono Shein

Registra un abono de un cliente Shein a su cartera de crédito.

**Flujo:**

1. Campo de búsqueda `id_shein_cliente` o `nombre`.
2. El sistema muestra: `nombre`, `saldo` actual, `fecha_pago_programada`.
3. La operadora captura `monto` y `forma_pago`.
4. El backend valida: `monto > 0` y `monto <= shein_clientes.saldo`.
5. El sistema ejecuta:
   ```sql
   INSERT INTO shein_movimientos (id_shein_cliente, monto, forma_pago, saldo_resultante, fecha)
   VALUES (:id, :monto, :forma_pago, :saldo - :monto, :now);

   UPDATE shein_clientes
   SET saldo = saldo - :monto,
       estatus = CASE WHEN saldo - :monto = 0 THEN 'inactivo' ELSE 'activo' END,
       fecha_pago_programada = :nueva_fecha_calculada
   WHERE id_shein_cliente = :id;
   ```
6. En éxito: `"Abono registrado correctamente."` y limpia el formulario.
7. En error si `monto > saldo`: `"El abono excede el saldo del cliente."`

#### Opción 4 — Lista de Pedidos

Tabla de pedidos pendientes de corte (`id_shein_corte IS NULL`), a nivel **pedido**.

| Columna         | Fuente                                                               |
| --------------- | -------------------------------------------------------------------- |
| No. Pedido      | `shein_pedidos.id_shein_pedido`                                      |
| Fecha           | `shein_pedidos.fecha`                                                |
| Cliente         | `shein_clientes.nombre`                                              |
| Total artículos | `COUNT(shein_pedidos_articulos.id_shein_articulo)`                   |
| Monto pedido    | `SUM(monto)` de artículos en `vigente` (aún sin resolver en corte)   |
| Estatus         | `"Pendiente de corte"` — constante mientras `id_shein_corte IS NULL` |

Al expandir un renglón se muestra el detalle: `sku`, `producto`, `tipo_producto`, `monto`.

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

#### Opción 5 — Registrar Corte

Genera un registro en `shein_cortes`, resuelve el estatus de cada artículo revisado,
vincula al corte los pedidos que sobreviven la revisión de precio, y **carga el saldo**
al `shein_cliente` de cada pedido incluido.

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
   no se le asigna id_shein_corte ni estatus_pago. Su monto no carga al saldo.
7. El sistema calcula y muestra: total_pedidos, suma_pedidos.
8. Operadora carga la lista resultante en la app Shein, paga en caja OXXO
   e ingresa total_ticket (obligatorio).
9. El sistema calcula y muestra cupon = suma_pedidos - total_ticket.
10. Operadora confirma.
```

**Transacción al confirmar:**

```sql
-- 1. Resolver artículos con precio revisado
UPDATE shein_pedidos_articulos
SET estatus_articulo = :estatus_resuelto,
    monto_vigente     = :monto_vigente_o_null
WHERE id_shein_articulo = :id_shein_articulo;

-- 2. Autoconfirmar artículos sin cambio de precio
UPDATE shein_pedidos_articulos
SET estatus_articulo = 'confirmado'
WHERE id_shein_pedido IN (:ids_pedidos_seleccionados)
  AND estatus_articulo = 'vigente';

-- 3. Insertar el corte
INSERT INTO shein_cortes (fecha_corte, total_pedidos, suma_pedidos, total_ticket, cupon)
VALUES (:fecha_actual, :total_pedidos, :suma_pedidos, :total_ticket,
        :suma_pedidos - :total_ticket);

-- 4. Vincular al corte los pedidos con al menos un artículo confirmado
UPDATE shein_pedidos
SET id_shein_corte = :id_shein_corte_nuevo,
    estatus_pago   = 'pago_pendiente'
WHERE id_shein_pedido IN (:ids_pedidos_con_articulo_confirmado);

-- 5. Cargar saldo al shein_cliente por cada pedido incluido
UPDATE shein_clientes
SET saldo   = saldo + :monto_pedido,
    estatus = 'activo'
WHERE id_shein_cliente = :id_shein_cliente;
-- (Una operación por cada shein_cliente afectado, calculando monto_pedido
--  como SUM(COALESCE(monto_vigente, monto)) de sus artículos confirmados)
```

- En éxito: `"Corte registrado. Cupón: $X.XX"` y cierra la ventana.
- En error: `"No se pudo registrar el corte. Intenta de nuevo."`

#### Opción 6 — Consulta de Cortes

> Responde: **¿dónde está el dinero del negocio en Shein?** — separado de la Consulta
> Finanzas, que es transversal a todo el sistema.

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

---

### Formulario Registrar Pedido Shein

Se abre tras validar `id_shein_cliente`. Muestra el nombre del cliente en el encabezado.

Contiene entre 1 y 4 artículos. Solo el Artículo 1 es obligatorio. Los artículos 2, 3 y
4 están colapsados hasta que el ejecutivo los activa (botón **"+ Agregar artículo"**).
Sin concepto de alternativa — cada artículo es un renglón independiente.

**Campos por renglón de artículo:**

| Etiqueta          | Modelo          | Tipo           | Requerido | Nota                                                         |
| ----------------- | --------------- | -------------- | --------- | ------------------------------------------------------------ |
| SKU               | `sku`           | String(25)     | ✅         | Identificador del artículo en el catálogo Shein.             |
| Producto          | `producto`      | String(60)     | ✅         | Descripción del artículo.                                    |
| Tipo Producto     | `tipo_producto` | Enum (select)  | ✅         | `Nacional` \| `Importado`. Informativo en MVP.               |
| Monto             | `monto`         | Float          | ✅         | Precio en la app al momento de la solicitud.                 |
| Monto actualizado | `monto_vigente` | Float          | —         | Deshabilitado en este formulario. Solo se habilita en Registrar Corte. |
| Cancelar          | —               | Acción (botón) | —         | Antes de guardar: remueve el renglón opcional. Después de guardado: cancela el artículo (`estatus_articulo = 'cancelado'`). |

---

### Flujo de variación de precios y cancelación en cascada

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
      → el saldo del shein_cliente no se afecta (no hay monto que cargar).
4. Si el pedido conserva AL MENOS UN artículo 'confirmado':
      → el pedido continúa vivo.
      → se le asigna id_shein_corte y estatus_pago = 'pago_pendiente'.
      → monto_pedido se calcula usando únicamente los artículos 'confirmado'.
      → ese monto_pedido se carga al saldo del shein_cliente.
```

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
        { "id": 2, "etiqueta": "Registrar Pedido Shein",  "accion": { "tipo": "abrir_modal",   "modal":   "modal_busqueda_cliente_shein"    } },
        { "id": 3, "etiqueta": "Registrar Abono Shein",   "accion": { "tipo": "abrir_modal",   "modal":   "modal_abono_shein"               } },
        { "id": 4, "etiqueta": "Lista de Pedidos",        "accion": { "tipo": "abrir_ventana", "ventana": "ventana_lista_pedidos_shein"     } },
        { "id": 5, "etiqueta": "Registrar Corte",         "accion": { "tipo": "abrir_ventana", "ventana": "ventana_registrar_corte_shein"   } },
        { "id": 6, "etiqueta": "Consulta de Cortes",      "accion": { "tipo": "abrir_ventana", "ventana": "ventana_consulta_cortes_shein"   } }
      ]
    },
    {
      "id": "modal_busqueda_cliente_shein",
      "titulo": "Registrar Pedido Shein",
      "tipo": "busqueda_previa",
      "campo_busqueda": { "etiqueta": "Cliente Shein", "modelo": "id_shein_cliente_o_nombre", "tipo": "String", "requerido": true },
      "validacion": { "tabla": "shein_clientes", "en_error": "Cliente no encontrado. Regístralo primero." },
      "boton": { "etiqueta": "Continuar", "accion": { "tipo": "abrir_ventana", "ventana": "ventana_registrar_pedido_shein" } }
    },
    {
      "id": "modal_abono_shein",
      "titulo": "Registrar Abono Shein",
      "tipo": "busqueda_previa",
      "campo_busqueda": { "etiqueta": "Cliente Shein", "modelo": "id_shein_cliente_o_nombre", "tipo": "String", "requerido": true },
      "validacion": { "tabla": "shein_clientes", "en_error": "Cliente no encontrado." },
      "boton": { "etiqueta": "Continuar", "accion": { "tipo": "abrir_ventana", "ventana": "ventana_abono_shein" } }
    }
  ],
  "ventanas": [
    {
      "id": "ventana_registrar_cliente_shein",
      "titulo": "Registrar Cliente Shein",
      "campos": [
        { "etiqueta": "Nombre",   "modelo": "nombre",   "tipo": "String",  "longitud": 20, "requerido": true },
        { "etiqueta": "Colonia",  "modelo": "colonia",  "tipo": "String",  "longitud": 12, "requerido": true },
        { "etiqueta": "Teléfono", "modelo": "telefono", "tipo": "Integer", "longitud": 10, "requerido": true },
        {
          "etiqueta": "Frecuencia de Pago", "modelo": "frecuencia_pago", "tipo": "Enum", "control": "select", "requerido": true,
          "opciones": [
            { "valor": "semanal",            "etiqueta": "Semanal"               },
            { "valor": "quincenal",          "etiqueta": "Quincenal"             },
            { "valor": "dia_especifico_mes", "etiqueta": "Día específico del mes"},
            { "valor": "otro",               "etiqueta": "Otro"                  }
          ]
        },
        {
          "etiqueta": "Día de pago específico", "modelo": "dia_pago_especifico",
          "tipo": "Integer", "control": "select_numero", "min": 1, "max": 31, "requerido": true,
          "visible_si": { "campo": "frecuencia_pago", "valor": "dia_especifico_mes" }
        },
        {
          "etiqueta": "Detalle de frecuencia", "modelo": "frecuencia_pago_detalle",
          "tipo": "String", "longitud": 60, "requerido": true,
          "visible_si": { "campo": "frecuencia_pago", "valor": "otro" }
        }
      ],
      "acciones": [
        {
          "id": "btn_guardar", "etiqueta": "Guardar", "tipo": "button", "variante": "primary",
          "accion": {
            "tipo": "db_insert", "tabla": "shein_clientes",
            "valores_default": [
              { "columna": "saldo",                 "valor": 0         },
              { "columna": "estatus",               "valor": "inactivo"},
              { "columna": "fecha_pago_programada", "valor": null      }
            ],
            "en_exito": { "mensaje": "Cliente Shein registrado correctamente.", "limpiar_formulario": true },
            "en_error": { "mensaje": "No se pudo guardar. Intenta de nuevo." }
          }
        }
      ]
    },
    {
      "id": "ventana_abono_shein",
      "titulo": "Registrar Abono Shein",
      "encabezado": { "campos": ["nombre", "saldo", "fecha_pago_programada"], "fuente": "shein_clientes" },
      "campos": [
        { "etiqueta": "Monto", "modelo": "monto", "tipo": "Real", "requerido": true },
        {
          "etiqueta": "Forma de pago", "modelo": "forma_pago", "tipo": "Enum", "control": "select", "requerido": true,
          "opciones": ["efectivo", "transferencia", "tarjeta"]
        }
      ],
      "acciones": [
        {
          "id": "btn_guardar", "etiqueta": "Registrar Abono", "tipo": "button", "variante": "primary",
          "accion": {
            "tipo": "transaccion",
            "pasos": [
              { "operacion": "INSERT", "tabla": "shein_movimientos", "descripcion": "Registra el abono." },
              { "operacion": "UPDATE", "tabla": "shein_clientes",    "descripcion": "Reduce saldo, recalcula estatus y fecha_pago_programada." }
            ],
            "validacion": { "condicion": "monto <= saldo", "en_error": "El abono excede el saldo del cliente." },
            "en_exito": { "mensaje": "Abono registrado correctamente.", "limpiar_formulario": true },
            "en_error": { "mensaje": "No se pudo registrar. Intenta de nuevo." }
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
            { "etiqueta": "SKU",               "modelo": "sku",           "tipo": "String", "longitud": 25, "requerido": true  },
            { "etiqueta": "Producto",          "modelo": "producto",      "tipo": "String", "longitud": 60, "requerido": true  },
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
                  { "modelo": "sku",           "columna": "sku"           },
                  { "modelo": "producto",      "columna": "producto"      },
                  { "modelo": "tipo_producto", "columna": "tipo_producto" },
                  { "modelo": "monto",         "columna": "monto"         }
                ],
                "valores_default": [
                  { "columna": "estatus_articulo", "valor": "vigente" },
                  { "columna": "monto_vigente",    "valor": null      }
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
        "expandible": { "descripcion": "Muestra sku, producto, tipo_producto, monto por renglón." }
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
          "columnas": ["sku", "producto", "tipo_producto", "monto", "monto_vigente"],
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
              { "operacion": "UPDATE_MASIVO", "tabla": "shein_pedidos_articulos", "descripcion": "Aplica estatus_articulo y monto_vigente resueltos." },
              { "operacion": "UPDATE",        "tabla": "shein_pedidos_articulos", "set": { "estatus_articulo": "confirmado" }, "where": "id_shein_pedido IN (:ids_seleccionados) AND estatus_articulo = 'vigente'" },
              { "operacion": "INSERT",        "tabla": "shein_cortes",            "campos": ["fecha_corte", "total_pedidos", "suma_pedidos", "total_ticket", "cupon"] },
              { "operacion": "UPDATE",        "tabla": "shein_pedidos",           "set": { "id_shein_corte": ":id_shein_corte_nuevo", "estatus_pago": "pago_pendiente" }, "where": "id_shein_pedido IN (:ids_pedidos_con_articulo_confirmado)" },
              { "operacion": "UPDATE_MASIVO", "tabla": "shein_clientes",          "descripcion": "saldo += monto_pedido por cada shein_cliente afectado; estatus -> activo." }
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
