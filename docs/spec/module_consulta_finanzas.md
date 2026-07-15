## Módulo Consulta Finanzas

> **Naturaleza del módulo:** panel de consulta de solo lectura. No realiza escrituras
> en ninguna tabla — consume datos agregados de `movimientos`, `shein_movimientos`,
> `recargas` y `clientes`/`shein_clientes`. Es transversal al sistema: resume la
> operación financiera del negocio en su conjunto, separado de la vista individual
> de cada cliente (que vive en **Consulta Historial** del Módulo Clientes y en
> **Consulta de Cortes** del Módulo Shein).

---

### Menú Consulta Finanzas

El botón `Consulta Finanzas` en el `main_menu` abre una ventana emergente con tres opciones.

```yaml
titulo_ventana: Consulta Finanzas
opciones:
  1: Cortes por periodo
  2: Ventas por segmento
  3: Detalle tienda
```

---

### Opción 1 — Cortes por periodo

Responde: **¿cuánto se movió en caja en un período dado, y cómo se desglosa?**

**Filtro de entrada:**

| Campo       | Tipo   | Requerido | Nota                                      |
| ----------- | ------ | --------- | ----------------------------------------- |
| Fecha desde | String | ✅         | Formato `DD-MM-YYYY`. ISO internamente.   |
| Fecha hasta | String | ✅         | Inclusivo. Formato `DD-MM-YYYY`.          |

**Resultados:**

Tabla resumen de `movimientos` del período, segmentada por `operacion`:

| Operación  | Total registros | Monto total |
| ---------- | --------------- | ----------- |
| `abono`    | N               | $X          |
| `contado`  | N               | $X          |
| `apartado` | N               | $X          |
| `gasto`    | N               | $X          |
| **Total**  | **N**           | **$X**      |

> `apartado` representa el primer pago registrado al crear el lote (`monto_primer_pago`).
> Los abonos subsiguientes al apartado se reflejan en `abono`.

**Consulta base:**

```sql
SELECT
    operacion,
    COUNT(*) AS total_registros,
    SUM(monto) AS monto_total
FROM movimientos
WHERE fecha >= :fecha_desde
  AND fecha <= :fecha_hasta
GROUP BY operacion;
```

**Drill-down disponibles:**

- **Por colonia** — agrupa los `movimientos` con `id_cliente` no nulo por `clientes.colonia`.
- **Por tipo de producto** — aplica sobre `movimientos WHERE operacion = 'contado'` con `id_producto`, join `inventario.tipo_producto`.

```sql
-- Drill-down por colonia (abono/apartado)
SELECT
    c.colonia,
    m.operacion,
    COUNT(*) AS total,
    SUM(m.monto) AS monto_total
FROM movimientos m
JOIN clientes c ON c.id_cliente = m.id_cliente
WHERE m.fecha >= :fecha_desde
  AND m.fecha <= :fecha_hasta
  AND m.operacion IN ('abono', 'apartado')
GROUP BY c.colonia, m.operacion
ORDER BY c.colonia;

-- Drill-down por tipo_producto (contado con producto registrado)
SELECT
    i.tipo_producto,
    COUNT(*) AS total,
    SUM(m.monto) AS monto_total
FROM movimientos m
JOIN inventario i ON i.id_producto = m.id_producto
WHERE m.fecha >= :fecha_desde
  AND m.fecha <= :fecha_hasta
  AND m.operacion = 'contado'
GROUP BY i.tipo_producto;
```

**UI:**

- Slider de rango de fechas o campos `desde` / `hasta`.
- Tabla con totales por operación en la vista principal.
- Botones de drill-down que expanden la tabla con el desglose seleccionado.
- La vista vuelve al resumen principal al cerrar el desglose.

---

### Opción 2 — Ventas por segmento

Responde: **¿cómo se distribuye el flujo del negocio entre Tienda, Shein y Recargas en un período dado? ¿Cuánto se debe al negocio?**

**Filtro de entrada:** mismo rango de fechas que la Opción 1.

#### Variables del segmento Tienda

```
ingresos_tienda  = Σ movimientos WHERE operacion IN ('contado', 'abono', 'apartado')
egresos_tienda   = Σ movimientos WHERE operacion = 'gasto'
saldo_tienda     = ingresos_tienda − egresos_tienda
```

> `saldo_tienda` representa el resultado neto de caja en el período.
> Contablemente: `saldo = ingresos − egresos`.

#### Variables del segmento Shein

```
ingresos_shein = Σ shein_movimientos.monto  (abonos de cartera Shein en el período)
```

#### Variables del segmento Recargas

```
ingresos_recargas = Σ recargas.monto  (en el período)
```

#### Total Caja

```
total_caja = saldo_tienda + ingresos_shein + ingresos_recargas
```

#### Deuda vigente (acreedores)

> Snapshot del momento de consulta — no depende del rango de fechas.

```
deuda_clientes = Σ clientes.saldo  WHERE saldo > 0
deuda_shein    = Σ shein_clientes.saldo  WHERE saldo > 0
total_acreedores = deuda_clientes + deuda_shein
```

**Consultas base:**

```sql
-- Segmento Tienda
SELECT
    SUM(CASE WHEN operacion IN ('contado','abono','apartado') THEN monto ELSE 0 END) AS ingresos_tienda,
    SUM(CASE WHEN operacion = 'gasto'                         THEN monto ELSE 0 END) AS egresos_tienda
FROM movimientos
WHERE fecha >= :fecha_desde AND fecha <= :fecha_hasta;

-- Segmento Shein
SELECT COALESCE(SUM(monto), 0) AS ingresos_shein
FROM shein_movimientos
WHERE fecha >= :fecha_desde AND fecha <= :fecha_hasta;

-- Segmento Recargas
SELECT COALESCE(SUM(monto), 0) AS ingresos_recargas
FROM recargas
WHERE fecha >= :fecha_desde AND fecha <= :fecha_hasta;

-- Deuda vigente (snapshot)
SELECT COALESCE(SUM(saldo), 0) AS deuda_clientes FROM clientes WHERE saldo > 0;
SELECT COALESCE(SUM(saldo), 0) AS deuda_shein    FROM shein_clientes WHERE saldo > 0;
```

**UI:**

- Tres cajas (boxes) en la parte superior: **Tienda**, **Shein**, **Recargas** — cada una con su monto de ingresos.
- Caja destacada: **Total Caja** (`total_caja`).
- Sección separada: **Acreedores** con `deuda_clientes`, `deuda_shein` y `total_acreedores`.
- Indicador visual diferenciado para saldo positivo / negativo en `saldo_tienda`.
- El rango de fechas aplica sobre los ingresos/egresos del período; la deuda vigente siempre es al momento de la consulta.

---

### Opción 3 — Detalle tienda

Responde: **¿cómo se pagó lo que entró a caja en Tienda en un período dado?**

Desglosa los `movimientos` de ingresos del período por `forma_pago`.

**Filtro de entrada:** mismo rango de fechas.

**Resultado:**

| Forma de pago   | Total registros | Monto total |
| --------------- | --------------- | ----------- |
| `efectivo`      | N               | $X          |
| `transferencia` | N               | $X          |
| `tarjeta`       | N               | $X          |
| **Total**       | **N**           | **$X**      |

> Solo se incluyen operaciones de ingreso: `contado`, `abono`, `apartado`.
> `gasto` no tiene `forma_pago` diferenciada a nivel de este reporte — se visualiza
> en Opción 1 como egreso.

**Consulta base:**

```sql
SELECT
    forma_pago,
    COUNT(*) AS total_registros,
    SUM(monto) AS monto_total
FROM movimientos
WHERE fecha >= :fecha_desde
  AND fecha <= :fecha_hasta
  AND operacion IN ('contado', 'abono', 'apartado')
GROUP BY forma_pago
ORDER BY monto_total DESC;
```

**UI:**

- Tabla simple con tres renglones (uno por `forma_pago` activa).
- Total en el pie de tabla.
- Mismos controles de fecha que las otras opciones.

---

### Schema JSON completo — Consulta Finanzas

```json
{
  "main_menu": {
    "botones": [
      {
        "id": "btn_consulta_finanzas",
        "etiqueta": "Consulta Finanzas",
        "accion": { "tipo": "abrir_modal", "modal": "modal_consulta_finanzas" }
      }
    ]
  },
  "modales": [
    {
      "id": "modal_consulta_finanzas",
      "titulo": "Consulta Finanzas",
      "tipo": "menu_opciones",
      "opciones": [
        { "id": 1, "etiqueta": "Cortes por periodo",  "accion": { "tipo": "abrir_ventana", "ventana": "ventana_cortes_periodo"    } },
        { "id": 2, "etiqueta": "Ventas por segmento", "accion": { "tipo": "abrir_ventana", "ventana": "ventana_ventas_segmento"   } },
        { "id": 3, "etiqueta": "Detalle tienda",      "accion": { "tipo": "abrir_ventana", "ventana": "ventana_detalle_tienda"    } }
      ]
    }
  ],
  "ventanas": [
    {
      "id": "ventana_cortes_periodo",
      "titulo": "Cortes por periodo",
      "filtros": [
        { "etiqueta": "Fecha desde", "modelo": "fecha_desde", "tipo": "Date", "requerido": true },
        { "etiqueta": "Fecha hasta", "modelo": "fecha_hasta", "tipo": "Date", "requerido": true }
      ],
      "tabla_resultado": {
        "columnas": ["operacion", "total_registros", "monto_total"],
        "total_row": true
      },
      "drill_down_opciones": [
        { "id": "drill_colonia",      "etiqueta": "Por colonia",       "columnas_extra": ["colonia"] },
        { "id": "drill_tipo_producto","etiqueta": "Por tipo producto", "columnas_extra": ["tipo_producto"], "nota": "Solo aplica sobre contado con producto registrado en inventario." }
      ]
    },
    {
      "id": "ventana_ventas_segmento",
      "titulo": "Ventas por segmento",
      "filtros": [
        { "etiqueta": "Fecha desde", "modelo": "fecha_desde", "tipo": "Date", "requerido": true },
        { "etiqueta": "Fecha hasta", "modelo": "fecha_hasta", "tipo": "Date", "requerido": true }
      ],
      "cajas_kpi": [
        { "id": "box_tienda",    "etiqueta": "Tienda",          "campos": ["ingresos_tienda", "egresos_tienda", "saldo_tienda"] },
        { "id": "box_shein",     "etiqueta": "Shein",           "campos": ["ingresos_shein"]  },
        { "id": "box_recargas",  "etiqueta": "Recargas",        "campos": ["ingresos_recargas"] },
        { "id": "box_total",     "etiqueta": "Total Caja",      "campos": ["total_caja"], "destacado": true }
      ],
      "seccion_acreedores": {
        "titulo": "Deuda vigente",
        "nota": "Snapshot al momento de la consulta, independiente del rango de fechas.",
        "campos": ["deuda_clientes", "deuda_shein", "total_acreedores"]
      }
    },
    {
      "id": "ventana_detalle_tienda",
      "titulo": "Detalle tienda",
      "filtros": [
        { "etiqueta": "Fecha desde", "modelo": "fecha_desde", "tipo": "Date", "requerido": true },
        { "etiqueta": "Fecha hasta", "modelo": "fecha_hasta", "tipo": "Date", "requerido": true }
      ],
      "tabla_resultado": {
        "columnas": ["forma_pago", "total_registros", "monto_total"],
        "filtro_operacion": ["contado", "abono", "apartado"],
        "total_row": true,
        "ordenado_por": ["monto_total DESC"]
      }
    }
  ]
}
```

---
