# Casos de uso — Módulo Clientes

> Espejo en lenguaje llano de `test_clientes.py`, mapeado 1:1 a
> `FULLSTACK/module_clientes.md`. No reemplaza ese archivo — aquí solo se
> listan los casos que el test ejercita y su resultado esperado.

**⚠️ Supuesto de rutas, pendiente de confirmar contra el archivo real:**
este documento y `test_clientes.py` asumen las siguientes rutas, inferidas
de la convención del resto del proyecto y de la única ruta que el propio
usuario confirmó por escrito (`docs/REPORT.md`, paso 3.3: *"correr los curl
contra /api/v1/auth/login y /api/v1/clientes"*):

| Acción | Método + ruta asumida | Confirmado por el usuario |
|---|---|---|
| Registrar cliente | `POST /api/v1/clientes` | ✅ Sí |
| Obtener cliente por id | `GET /api/v1/clientes/{id_cliente}` | ❌ Inferido |
| Buscar clientes | `GET /api/v1/clientes?q=` | ❌ Inferido |
| Rehabilitar cliente | `PATCH /api/v1/clientes/{id_cliente}/rehabilitar` | ❌ Inferido |

No se tuvo a la vista `app/api/v1/endpoints/clientes.py`. Si alguna ruta
real difiere, es un ajuste de una línea en `test_clientes.py` — no invalida
el resto del archivo. **Fuera de alcance de este documento:** "Editar
Cliente" (Opción 2 de `module_clientes.md`) — no tiene `service` ni
`endpoint` todavía (`cliente_service.py` no define `editar_cliente`), así
que no se inventa un caso para algo que no existe en código.

---

## 1. Registrar Cliente (`POST /api/v1/clientes`)

| # | Caso | Entrada relevante | Resultado esperado |
|---|---|---|---|
| 1.1 | Alta válida, `frecuencia_pago = semanal` | Sin campos condicionales | `201`, `no_cliente` autogenerado, `saldo = 0`, `estatus = "inactivo"` (nace inactivo, se activa en automático al recibir el primer producto -- ver `test_pedidos.py`), `fecha_pago_programada = null` |
| 1.2 | Alta válida, `frecuencia_pago = quincenal` | Sin campos condicionales | `201`, mismos defaults que 1.1 |
| 1.3 | Alta válida, `frecuencia_pago = dia_especifico_mes` con `dia_pago_especifico = 15` | — | `201`, `dia_pago_especifico` persistido y visible en la respuesta |
| 1.4 | Alta inválida, `dia_especifico_mes` **sin** `dia_pago_especifico` | — | `422` (INC-02, validación condicional de `cliente.py`) |
| 1.5 | Alta inválida, `dia_pago_especifico` fuera de rango (`0` y `32`) | — | `422` en ambos bordes |
| 1.6 | Alta válida, `frecuencia_pago = otro` con `frecuencia_pago_detalle` no vacío | — | `201`, `frecuencia_pago_detalle` persistido |
| 1.7 | Alta inválida, `otro` **sin** `frecuencia_pago_detalle` (ausente y como cadena vacía `""`/solo espacios) | — | `422` en los tres casos |
| 1.8 | Alta inválida, `telefono` con 9 y con 11 dígitos | — | `422` en ambos (regresión de INC-01, ya resuelto — no se debe romper de nuevo) |
| 1.9 | Alta inválida, `nombre`/`colonia`/`ref_nombre`/`ref_colonia` vacíos o solo espacios | — | `422` |
| 1.10 | Alta inválida, `nombre` (41), `colonia` (21), `ref_nombre`/`ref_colonia` (41), `frecuencia_pago_detalle` (61) — cada uno 1 carácter sobre su límite | — | `422` en cada uno (INC-18, ver nota de `cliente.py`) |
| 1.11 | `ref_telefono` ausente (`None`) | — | `201` — es opcional |
| 1.12 | `no_cliente` — consecutivo correcto por colonia | Dos altas seguidas con la misma `colonia` | El segundo `no_cliente` continúa el consecutivo del primero (`Colonia-001`, `Colonia-002`) |
| 1.13 | `no_cliente` — normalización de mayúsculas | `colonia = "carrillos"` | `no_cliente` se genera como `Carrillos-00N` (`.title()`), consistente con el ejemplo de `module_clientes.md` |

---

## 2. Consulta Cliente

| # | Caso | Resultado esperado |
|---|---|---|
| 2.1 | `GET` por `id_cliente` existente | `200`, incluye `frecuencia_pago`, `dia_pago_especifico`, `frecuencia_pago_detalle`, `fecha_pago_programada = null`, `fecha_registro` como `date` |
| 2.2 | `GET` por `id_cliente` inexistente | `404` (a confirmar contra el endpoint real — `cliente_service.obtener_cliente` devuelve `None`, el manejo del `404` vive en el endpoint, no revisado) |
| 2.3 | Búsqueda por `nombre` parcial | Devuelve solo los clientes que hacen match (`ilike`) |
| 2.4 | Búsqueda por `no_cliente` parcial | Igual que 2.3, por el otro campo indexado en el `or_` |
| 2.5 | Búsqueda con `q` vacío | Devuelve todos los clientes, ordenados por `nombre` |

---

## 3. `estatus` — campo derivado, sin endpoint propio

No existe "Rehabilitar Cliente" ni ningún otro mecanismo para editar
`estatus` a mano — nace `inactivo` (caso 1.1/1.2) y se sincroniza en
automático (`cliente_service.sincronizar_estatus`) en cada punto de
Pedidos o Movimientos que modifique `saldo`. El ciclo completo
(`inactivo -> activo` al surtir, `activo -> inactivo` al devolver/cancelar/
abonar hasta `saldo = 0`) se prueba en `test_pedidos.py` y, cuando exista,
`test_movimientos.py` — no en este archivo, que solo cubre alta y consulta.

Regresión de INC-07: ningún cliente puede llegar a `estatus = "liquidado"`
— el enum real (`EstatusCliente`) solo admite `activo`/`inactivo`, y
`sincronizar_estatus()` es la única función que escribe en esta columna.

---

## 4. Nota explícita — `fecha_pago_programada`

**Pendiente de Movimientos, no se prueba aquí.** La fórmula diferenciada
por `frecuencia_pago` (semanal rodante, quincenal a fechas fijas de
calendario, `dia_especifico_mes` con clamp de fin de mes, `otro` siempre
`NULL`) vive en `movimiento_service.py`, no en `cliente_service.py`. Este
módulo solo garantiza que el campo nace en `NULL` y que los datos de origen
(`dia_pago_especifico`, `frecuencia_pago_detalle`) se capturan y validan
correctamente al registrar. La prueba de la fórmula en sí corresponde a
`test_movimientos.py`.

---

## 5. Casos deliberadamente no cubiertos (decisión, no descuido)

- **`dia_pago_especifico` o `frecuencia_pago_detalle` enviados cuando la
  `frecuencia_pago` no los requiere** (ej. `frecuencia_pago = semanal` con
  `dia_pago_especifico = 15`). El validador actual no lo rechaza — solo
  exige el campo cuando aplica, no prohíbe que llegue cuando no aplica. Es
  una decisión de diseño abierta, no un bug: el formulario (`module_clientes.md`,
  `visible_si`) ya oculta el campo irrelevante en la UI, así que hoy es
  inofensivo. **Pendiente de que el usuario confirme** si prefiere que el
  backend también lo rechace explícitamente (defensa en profundidad) o si
  la UI es control suficiente.
- **Editar Cliente** — sin `service`/`endpoint` todavía, no aplica.
- **Concurrencia en `generar_no_cliente`** — dos altas simultáneas en la
  misma `colonia` podrían competir por el mismo consecutivo (`COUNT` +
  `+1`, sin lock). Riesgo de arquitectura de un solo usuario concurrente
  real hoy (negocio de una sola operadora, confirmado en `REPORT.md §3`);
  se deja anotado, no bloqueante.
