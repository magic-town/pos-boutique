## Panel Principal — Main Panel

> El Panel Principal es la pantalla de operación cotidiana: siempre visible, siempre
> disponible. Funciona como caja registradora. No requiere navegar a ningún módulo.
>
> Escribe en: `movimientos`, `apartados`, `apartados_articulos`. Dispara actualizaciones
> en `clientes.saldo` e `inventario.estatus` según la operación.

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
                     -- Solo aplica a 'contado' con coincidencia en inventario. NULL en los demás casos.
    id_apartado      INTEGER REFERENCES apartados(id_apartado),
                     -- Solo aplica a 'apartado' (evento de primer pago). NULL en los demás casos.
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
> Un apartado agrupa de 1 a N artículos bajo una sola fecha y un solo primer pago.

#### Tablas `apartados` y `apartados_articulos`

```sql
CREATE TABLE apartados (
    id_apartado        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente         INTEGER NOT NULL REFERENCES clientes(id_cliente),
    fecha_apartado     TEXT    NOT NULL,   -- ISO 8601. Semilla de la bandera naranja.
    monto_primer_pago  REAL    NOT NULL,   -- mínimo $100.00. Cubre todo el lote, no por artículo.
    saldo_pendiente    REAL    NOT NULL,   -- Σ(precio_producto del lote) − monto_primer_pago.
                       -- Se reduce únicamente con abonos. No se ajusta por cancelaciones.
    estatus            TEXT    NOT NULL DEFAULT 'abierto'
                           CHECK (estatus IN ('abierto', 'liquidado'))
);

CREATE TABLE apartados_articulos (
    id_apartado_articulo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_apartado          INTEGER NOT NULL REFERENCES apartados(id_apartado),
    id_producto          INTEGER REFERENCES inventario(id_producto),
                         -- Opcional. NULL si no hubo coincidencia en inventario o no se capturó.
    precio_producto      REAL    NOT NULL,
                         -- Autollenado desde inventario.precio_venta si hay coincidencia;
                         -- capturado a mano si no. Se persiste siempre, en ambos casos.
    estatus_articulo     TEXT    NOT NULL DEFAULT 'vigente'
                             CHECK (estatus_articulo IN ('vigente', 'vendido', 'cancelado'))
);
```

#### Reglas del Apartado

1. El cliente debe estar registrado en `clientes`. Obligatorio.
2. Un cliente solo puede tener un apartado abierto (`estatus = 'abierto'`) a la vez. Ese
   apartado puede contener varios artículos, todos bajo la misma `fecha_apartado`.
3. Por cada artículo, `id_producto` es opcional. Si se captura, el sistema lo busca en
   `inventario`; si hay coincidencia, autollena `precio_producto` (solo lectura). Si no
   hay coincidencia, o no se capturó `id_producto`, `precio_producto` se captura a mano.
4. Solo los artículos con `id_producto` que exista en `inventario` con
   `estatus IN ('disponible', 'disponible_c/descuento')` cambian su estatus a
   `'apartado'` al registrar. Un artículo sin coincidencia en `inventario` forma parte
   del saldo del apartado, pero no genera ningún movimiento de inventario.
5. El primer pago (`monto_primer_pago`) es único para todo el lote — no por artículo.
   Mínimo $100.00. El backend rechaza si `monto_primer_pago < 100`.
6. `saldo_pendiente = Σ(precio_producto de todos los artículos del lote) − monto_primer_pago`.
   Este saldo se suma al `clientes.saldo` general en la misma transacción.
7. El plazo de liquidación es un mes contado desde `fecha_apartado`. El sistema no
   bloquea la operación automáticamente al vencer — es criterio operativo, señalado por
   la bandera naranja.
8. Liquidación: cuando `saldo_pendiente` llega a 0 (vía abonos), `apartados.estatus`
   pasa a `'liquidado'`. Todos los artículos con `estatus_articulo = 'vigente'` y
   `id_producto` existente en `inventario` cambian a `inventario.estatus = 'vendido'`.
   La bandera naranja desaparece.
9. Cancelación por artículo: cualquier artículo `vigente` del lote puede cancelarse
   individualmente. Si tiene `id_producto` existente en `inventario`, su estatus regresa
   a `'disponible'`. La cancelación **no ajusta** `saldo_pendiente` ni `clientes.saldo`
   — la deuda generada por ese artículo permanece y se cobra como cualquier otro saldo
   pendiente del cliente.
10. Correcciones de registros históricos se hacen con un abono compensatorio — no se
    editan movimientos pasados directamente.

#### Bandera naranja — alerta de apartado por vencer

Independiente de las banderas amarilla y roja del ciclo normal de pagos
(`clientes.fecha_pago_programada`, ver Módulo Clientes). Se calcula al vuelo, no se
persiste como columna:

- **Semilla:** `apartados.fecha_apartado` del apartado abierto del cliente.
- **Vencimiento:** `fecha_apartado + 1 mes`.
- **Activa cuando:** `apartados.estatus = 'abierto'` y
  `fecha_actual >= (fecha_apartado + 1 mes) − 5 días`.
- **Se apaga cuando:** `apartados.estatus = 'liquidado'`.

#### Ciclo de vida de un Apartado

```
inventario.estatus     disponible ──▶ apartado ──────────────────▶ vendido
(por artículo):                            │ (artículo cancelado)
                                            └──▶ disponible

apartados.saldo_pendiente:  Σ precio_producto − monto_primer_pago  ──▶ ... ──▶ 0 (liquidado)

movimientos:            [apartado: 1er pago]  [abono]  [abono]  [abono: saldo_pendiente en 0]
```

#### Comportamiento — Registrar Apartado

1. Operadora ingresa `no_cliente` — el sistema muestra nombre y saldo actual.
2. Operadora agrega de 1 a N artículos. Por cada uno captura `id_producto` (opcional);
   si hay coincidencia en inventario, el sistema autollena `precio_producto`; si no, lo
   captura a mano.
3. El sistema muestra `saldo_pendiente` en vivo conforme se agregan artículos y se
   ingresa el primer pago.
4. Operadora ingresa `monto_primer_pago`. Backend valida `>= 100`.
5. Operadora selecciona forma de pago y confirma.

**Transacción al confirmar:**

```sql
-- 1. Cabecera del apartado
INSERT INTO apartados (id_cliente, fecha_apartado, monto_primer_pago, saldo_pendiente, estatus)
VALUES (:id_cliente, :fecha_actual, :monto_primer_pago, :saldo_pendiente, 'abierto');

-- 2. Detalle: un renglón por artículo del lote
INSERT INTO apartados_articulos (id_apartado, id_producto, precio_producto, estatus_articulo)
VALUES (:id_apartado, :id_producto, :precio_producto, 'vigente');

-- 3. Registrar el evento de caja
INSERT INTO movimientos (operacion, id_cliente, id_apartado, monto, forma_pago, saldo_resultante, fecha)
VALUES ('apartado', :id_cliente, :id_apartado, :monto_primer_pago, :forma_pago, :saldo_pendiente, :fecha_actual);

-- 4. Actualizar saldo del cliente
UPDATE clientes SET saldo = saldo + :saldo_pendiente WHERE id_cliente = :id_cliente;

-- 5. Marcar como apartado solo los artículos con coincidencia en inventario
UPDATE inventario SET estatus = 'apartado', changed_status = :fecha_actual
WHERE id_producto IN (:ids_producto_encontrados);
```

#### Comportamiento — Abonar / Liquidar

1. Operadora ingresa `no_cliente`. El sistema muestra `saldo_actual` y, si el cliente
   tiene un apartado abierto, su `saldo_pendiente`.
2. Operadora ingresa monto del abono. El sistema muestra `saldo_resultante = saldo_actual − monto`.
3. Backend valida `monto <= saldo_actual`. Si no: `"El abono supera el saldo del cliente."`.
4. Operadora selecciona forma de pago y confirma.

**Transacción al confirmar:**

```sql
-- 1. Registrar movimiento
INSERT INTO movimientos (operacion, id_cliente, monto, forma_pago, saldo_resultante, fecha)
VALUES ('abono', :id_cliente, :monto, :forma_pago, :saldo_resultante, :fecha_actual);

-- 2. Actualizar saldo del cliente
UPDATE clientes SET saldo = saldo - :monto WHERE id_cliente = :id_cliente;

-- 3. Si el cliente tiene un apartado abierto, reducir su saldo pendiente
UPDATE apartados SET saldo_pendiente = saldo_pendiente - :monto
WHERE id_cliente = :id_cliente AND estatus = 'abierto';

-- 4. Liquidar si el saldo pendiente llega a 0
UPDATE apartados SET estatus = 'liquidado'
WHERE id_cliente = :id_cliente AND estatus = 'abierto' AND saldo_pendiente <= 0;

UPDATE apartados_articulos SET estatus_articulo = 'vendido'
WHERE id_apartado = :id_apartado_liquidado AND estatus_articulo = 'vigente' AND id_producto IS NOT NULL;

UPDATE inventario SET estatus = 'vendido', changed_status = :fecha_actual
WHERE id_producto IN (
    SELECT id_producto FROM apartados_articulos
    WHERE id_apartado = :id_apartado_liquidado AND estatus_articulo = 'vendido'
);
```

Si `saldo_resultante = 0`: el sistema muestra `"¡Cuenta liquidada!"` en el mismo toast de
éxito. Si ese abono liquidó además un apartado abierto, el toast indica que los
artículos vigentes pasaron a `vendido`. El `estatus` de `clientes` no cambia
automáticamente — el cliente permanece `activo`. La operadora puede cambiarlo
manualmente desde **Editar Cliente** si lo considera.

#### Comportamiento — Cancelar artículo de un Apartado

1. Operadora selecciona el apartado abierto del cliente y el artículo específico a
   cancelar.
2. Confirma.

```sql
UPDATE apartados_articulos SET estatus_articulo = 'cancelado'
WHERE id_apartado_articulo = :id_apartado_articulo;

UPDATE inventario SET estatus = 'disponible', changed_status = :fecha_actual
WHERE id_producto = (
    SELECT id_producto FROM apartados_articulos WHERE id_apartado_articulo = :id_apartado_articulo
) AND id_producto IS NOT NULL;
```

No afecta `apartados.saldo_pendiente` ni `clientes.saldo`.

---

### Campos activos por operación

| Operación | No. Cliente   | Producto(s)                                        | Monto                         | Forma Pago | `saldo_resultante`               | Descripción   |
| --------- | ------------- | --------------------------------------------------- | ------------------------------ | ---------- | --------------------------------- | ------------- |
| Contado   | Opcional      | 0 o 1, `id_producto` opcional                        | ✅                              | ✅          | NULL                               | —             |
| Apartado  | Obligatorio   | 1 a N artículos, `id_producto` opcional c/u          | ✅ primer pago del lote, mín $100 | ✅       | ✅ Σ precio_producto − primer pago | —             |
| Abono     | Obligatorio   | ❌                                                    | ✅                              | ✅          | ✅ saldo − monto                   | —             |
| Gasto     | Deshabilitado | ❌                                                    | ✅                              | ✅          | NULL                               | ✅ obligatorio |

---

### Comportamiento — Contado

1. Operadora ingresa `id_producto` (opcional) y/o descripción libre.
2. Si `id_producto` tiene coincidencia en `inventario` con
   `estatus IN ('disponible', 'disponible_c/descuento')`, el sistema autollena
   descripción y precio (solo lectura).
3. Si no hay coincidencia — artículo no registrado en el sistema, o no se capturó
   `id_producto` — la operadora captura descripción y precio a mano. No hay efecto en
   inventario.
4. Operadora ingresa monto, forma de pago y confirma.
5. El sistema inserta en `movimientos` con `operacion = 'contado'`, `id_producto`
   vinculado solo si hubo coincidencia.
6. Si hubo coincidencia: descuenta `inventario.stock -= 1`. Si `stock` llega a 0,
   actualiza `estatus = 'vendido'`.

### Comportamiento — Gasto

1. El campo `no_cliente` se deshabilita visualmente.
2. El campo `descripcion` se activa y es obligatorio.
3. Operadora ingresa monto, forma de pago y descripción.
4. El sistema inserta en `movimientos` con `operacion = 'gasto'`, `id_cliente = NULL`,
   `id_producto = NULL`.
5. `saldo_resultante = NULL`. El monto es salida de caja (negativo para el negocio).

> El saldo del negocio no existe como campo en la DB — se deriva mediante consultas
> agregadas sobre `movimientos`. Ver [Módulo Consulta Global](#módulo-consulta-global).

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
    nota: "En Apartado representa el primer pago del lote (monto_primer_pago), no el saldo."
  - etiqueta: Forma de Pago
    modelo: forma_pago
    tipo: Enum
    control: radio_buttons
    opciones: [Efectivo, Transferencia, Tarjeta]
    requerido: true
campos_condicionales_por_operacion:
  Contado:
    - id_producto: opcional. Autollena descripción y precio si hay coincidencia en inventario.
    - descripcion_producto: texto libre si no hay coincidencia.
  Apartado:
    - articulos: lista de 1 a N, cada uno con:
        - id_producto: opcional
        - precio_producto: autollenado si hay coincidencia en inventario, editable si no
    - saldo_pendiente: calculado (Σ precio_producto − monto_primer_pago). Solo lectura.
  Abono:
    - saldo_actual: mostrado al buscar cliente (solo lectura)
    - saldo_resultante: calculado (saldo_actual − monto). Solo lectura.
  Gasto:
    - descripcion: texto libre. Obligatorio. Reemplaza id_cliente y producto.
```

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
          { "etiqueta": "ID Producto", "modelo": "id_producto", "tipo": "Integer",
            "requerido": false },
          { "etiqueta": "Producto", "modelo": "descripcion_producto", "tipo": "String",
            "visible_si": {"id_producto": "sin_coincidencia"}, "requerido": false }
        ]
      },
      {
        "visible_si": {"operacion": "Apartado"},
        "campos": [
          { "etiqueta": "Artículos", "modelo": "articulos", "tipo": "Lista",
            "minimo": 1,
            "campos_por_articulo": [
              { "etiqueta": "ID Producto", "modelo": "id_producto", "tipo": "Integer", "requerido": false },
              { "etiqueta": "Precio", "modelo": "precio_producto", "tipo": "Float",
                "autollenado": "inventario.precio_venta", "editable_si": "sin_coincidencia" }
            ]
          },
          { "etiqueta": "Saldo pendiente", "modelo": "saldo_pendiente", "tipo": "Float",
            "solo_lectura": true, "calculado": "suma(articulos.precio_producto) - monto" }
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
