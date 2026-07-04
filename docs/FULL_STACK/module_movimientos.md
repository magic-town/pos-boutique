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

| Operación | No. Cliente   | Producto / Origen         | Monto                  | Forma Pago | `saldo_resultante` | Descripción   |
| --------- | ------------- | ------------------------- | ---------------------- | ---------- | ------------------ | ------------- |
| Contado   | Opcional      | ✅ (Catálogo o Inventario) | ✅                      | ✅          | NULL               | —             |
| Apartado  | Obligatorio   | ✅ (solo Inventario)       | ✅ (1er pago, mín $100) | ✅          | ✅ precio − pago    | —             |
| Abono     | Obligatorio   | ❌                         | ✅                      | ✅          | ✅ saldo − monto    | —             |
| Gasto     | Deshabilitado | ❌                         | ✅                      | ✅          | NULL               | ✅ obligatorio |

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

