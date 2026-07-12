# FULLSTACK/ — spec segmentada por módulo

**Para trabajar en un módulo específico, basta con su `module_<nombre>.md`** — no hace falta cargar los demás.

## Regla de una sola vía

`REPORT.md` puede referenciar estos archivos. Estos archivos **no**
referencian a `REPORT.md` ni entre sí — cada uno debe bastarse solo para
implementar su módulo. Si un módulo necesita algo de otro (ej. Pedidos lee
`inventario` en el futuro), esa dependencia se documenta en
`resumen_tablas.md`, no se resuelve cargando el otro `module_*.md` completo.

## Mapa de módulos

| Archivo | Módulo | Extraído | Código | Test |
|---|---|---|---|---|
| `module_clientes.md` | Clientes | ✅ | ✅ | ✅ |
| `module_pedidos.md` | Pedidos | ✅ | ✅ | ✅ |
| `module_inventario.md` | Inventario | ✅ | ✅ | ✅ |
| `module_movimientos.md` | Movimientos (Panel Principal) | ✅ | ✅ | ✅ |
| `module_shein.md` | Shein | ✅ | ✅ | ✅ |
| `module_recargas.md` | Recargas Telefónicas | ✅ | ✅ | ✅ |
| `module_consulta.md` | Consulta Global | ❌ | ❌ | ❌ |
| `module_setting.md` | Autenticación y Configuración | ✅ | ✅ | ✅ |
| `resumen_tablas.md` | — (transversal) | ✅ | — | — |

`⚠️` = tiene código pero con incidencias conocidas (ver `REPORT.md §4.3`) o
incompleto. 

`❌` = no empezado. Actualizar esta tabla cada vez que un módulo
cambie de columna — es el mismo principio que ya rige `REPORT.md §5`.

## `resumen_tablas.md`

Índice de las 15 tablas del sistema y a qué módulo pertenece cada una — útil
para saber si tocar una tabla en un módulo tiene efecto lateral en otro
(ej. `inventario` la lee `movimientos`). No es spec de ningún módulo
individual, por eso vive aparte y no dentro de ninguno de los `module_*.md`.
