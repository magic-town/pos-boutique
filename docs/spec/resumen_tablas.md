## Resumen de tablas del sistema

| Tabla                     | Módulo               | Relaciones principales                                |
| ------------------------- | -------------------- | ----------------------------------------------------- |
| `clientes`                | Clientes             | Referenciada por `pedidos`, `movimientos`, `familiares`|
| `cartera_vencida`         | Clientes             | Independiente — sin FKs (tabla de archivo)             |
| `familiares`              | Clientes             | FK doble → `clientes` (id_cliente_a, id_cliente_b)    |
| `pedidos`                 | Pedidos              | FK → `clientes`                                       |
| `pedidos_articulos`       | Pedidos              | FK → `pedidos`, autorreferencia para `rol`            |
| `precios_catalogo`        | Pedidos              | Sin FK — lookup por `proveedor` + `id_producto`       |
| `inventario`              | Inventario           | Referenciada por `movimientos`, `apartados_articulos` |
| `movimientos`             | Panel Principal      | FK → `clientes`, FK → `inventario`, FK → `apartados`  |
| `apartados`               | Panel Principal      | FK → `clientes`, referenciada por `apartados_articulos`, `movimientos` |
| `apartados_articulos`     | Panel Principal      | FK → `apartados`, FK → `inventario` (nullable)        |
| `shein_clientes`          | Shein                | Independiente de `clientes`. Referenciada por `shein_pedidos`, `shein_movimientos` |
| `shein_movimientos`       | Shein                | FK → `shein_clientes`                                 |
| `shein_pedidos`           | Shein                | FK → `shein_clientes`, FK → `shein_cortes` (nullable) |
| `shein_pedidos_articulos` | Shein                | FK → `shein_pedidos`                                  |
| `shein_cortes`            | Shein                | Referenciada por `shein_pedidos`                      |
| `recargas`                | Recargas Telefónicas | Independiente                                         |
| `usuarios`                | Autenticación        | Independiente                                         |
| `configuracion`           | Setting              | Independiente                                         |

> **18 tablas.** Las 3 tablas nuevas del rediseño (`cartera_vencida`, `familiares`,
> `shein_movimientos`) se agregaron en la migración `e5f6a7b8c9d0`.
> `shein_clientes` incorpora columnas de cartera de crédito (`saldo`, `estatus`,
> `frecuencia_pago`, `dia_pago_especifico`, `frecuencia_pago_detalle`,
> `fecha_pago_programada`).
