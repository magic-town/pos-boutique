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

| Campo      | Nota                                                                       |
| ---------- | -------------------------------------------------------------------------- |
| `compania` | Enum fijo. Ortografía correcta: `Unefon` (no `Unifon`).                    |
| `monto`    | Float. Sin validación de tope — la operadora captura el monto real.        |
| `fecha`    | Timestamp completo. El backend lo autogenera — la operadora no lo captura. |

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

