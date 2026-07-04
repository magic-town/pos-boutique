## Resumen de tablas del sistema

| Tabla                     | Módulo               | Relaciones principales                                |
| ------------------------- | -------------------- | ----------------------------------------------------- |
| `clientes`                | Clientes             | Referenciada por `pedidos`, `movimientos`             |
| `pedidos`                 | Pedidos              | FK → `clientes`                                       |
| `pedidos_articulos`       | Pedidos              | FK → `pedidos`, autorreferencia para `rol`            |
| `precios_catalogo`        | Pedidos              | Sin FK — lookup por `proveedor` + `id_producto`       |
| `inventario`              | Inventario           | Referenciada por `movimientos`                        |
| `movimientos`             | Panel Principal      | FK → `clientes`, FK → `inventario`                    |
| `shein_clientes`          | Shein                | Independiente de `clientes`                           |
| `shein_pedidos`           | Shein                | FK → `shein_clientes`, FK → `shein_cortes` (nullable) |
| `shein_pedidos_articulos` | Shein                | FK → `shein_pedidos`                                  |
| `shein_cortes`            | Shein                | Referenciada por `shein_pedidos`                      |
| `recargas`                | Recargas Telefónicas | Independiente                                         |
| `usuarios`                | Autenticación        | Independiente                                         |
| `configuracion`           | Setting              | Independiente                                         |

> **Siguiente paso:** con este documento el mapa del sistema está completo.
> El siguiente documento de la secuencia es la especificación de la API REST
> (`docs/API.md`): endpoints, schemas Pydantic, respuestas de error y orden de
> implementación recomendado.
