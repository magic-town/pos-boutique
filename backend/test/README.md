# Tests automatizados — convención

Reemplaza el propósito de verificación (no el de aprendizaje) de las guías
`aux_*.md`: en vez de descifrar tokens y pegar `curl` a mano cada vez que se
toca un módulo, esta suite reconstruye el escenario completo en segundos.

Las guías `aux_*.md` **no desaparecen** — le siguen sirviendo a una persona
nueva para *entender* el flujo paso a paso. Esta carpeta es para *verificar*
que el flujo sigue funcionando, sin explicar nada.

## Cómo correr

Correr desde `backend/`, requiere `pytest.ini`

```bash
cd backend
python3 -m venv venv          # si no existe ya
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest test/ -v
```

Requiere `pos.db` ya migrado (`alembic upgrade head`) y, para los tests de
Pedidos que dependen de catálogo, `precios_catalogo` ya importado
(`python -m app.scripts.importar_precios ...`). No requiere `uvicorn`
corriendo — usa `TestClient`, que invoca la app directamente en proceso.

## Estructura

- `conftest.py` — fixtures compartidas por todos los módulos: `client`
  (TestClient), `admin_token`/`auth_headers` (login real), `cliente_prueba`
  (cliente desechable, `no_cliente` único por corrida vía `uuid`, creado
  directo en SQLAlchemy para no depender de módulos con bugs conocidos).
- `test_<modulo>.py` — un archivo por módulo, mapeado 1:1 a
  `FULLSTACK/module_<modulo>.md`. Si el spec de un módulo no tiene un
  `module_<modulo>.md` propio todavía, ese es el primer paso, no escribir el
  test a ciegas contra el `.md` monolítico.

## Módulos y su estado (actualizar conforme se agreguen)

| Módulo | `FULLSTACK/module_*.md` | `test_*.py` | `casos_uso` |
|---|---|---|---|
| Pedidos | ✅ existe | ✅ `test_pedidos.py` (corrido, verde) | ✅ `casos_pedidos.md` |
| Inventario | ✅ existe | ✅ `test_inventario.py` (corrido, verde) | ✅ `casos_inventario.md` |
| Shein | ✅ existe | ❌ pendiente (código existente, sin test) | ❌ en diseño |
| Clientes | ✅ existe | ❌ pendiente (bloqueado por INC-02) | ❌ en diseño |
| Movimientos | ✅ existe | ❌ pendiente (bloqueado por INC-05/06) | ❌ en diseño |
| Recargas | ✅ existe | ❌ pendiente (sin código todavía) | ❌ en diseño |
| Consulta | ✅ existe | ❌ pendiente (sin código todavía) | ❌ en diseño |
| Setting | ✅ existe | ❌ pendiente (Auth existente; Setting sin código) | ❌ en diseño |

Ver `docs/FULLSTACK/README.md` para el detalle de cada uno (es la fuente de
verdad de esta tabla — actualízala ahí primero, luego refleja aquí).

Detalle en lenguaje llano de cada caso, mapeado 1:1 a los tests de abajo: `casos_inventario.md`, `casos_pedidos.md`.

## Cobertura conocida (revisado contra el spec, no solo "ya quedó")

### `test_pedidos.py`

Cubre: lookup automático de precio, `informal` con monto libre, cliente
inexistente (404), límite de alternativas (3 para Price_Shoes / 1 para el resto, ambos límites superiores), saldo del cliente sin cambios mientras el artículo está `vigente` (aunque ya tenga monto resuelto) y solo sube (`+=`) al pasar a `en_almacen`, devolución (`-=` + precarga), cancelar `vigente` (sin impacto) y `en_almacen` (revierte), escenario integral de 3 artículos mixto.

**Huecos que NO están cubiertos todavía** (encontrados al revisar, no
inventados para parecer exhaustivo):
- `proveedor = otro` con `monto` faltante — el schema lo valida
  (`ArticuloCreate`), pero ningún test dispara ese `422`.
- Alternativa con proveedor distinto al principal (ej. principal `Pakar`,
  alternativa `Price_Shoes`) — la regla dice que el límite lo da el
  principal; no hay test que confirme que una alternativa "distinta" no
  rompe nada.
- Devolver un artículo que no está `en_almacen` (ej. todavía `vigente`) —
  debería dar `400`, no probado.
- Cancelar un artículo ya `cancelado` o `devuelto` — comportamiento en
  reintento, no probado.
- 404 de cliente inexistente en `/devolucion` y `/cancelacion` (solo se
  probó en `POST /pedidos`).

### `test_inventario.py`

Cubre: alta básica, transición a `en_ruta` (requiere `descripcion_ruta`),
transición inválida (`vendido → disponible`), `precio_descuento >=
precio_venta` rechazado, descuento masivo por `marca` (aplicar + retirar),
`precio_fijo` mayor al de venta (omitido, no aborta), segmento vacío
rechazado, productos `vendido` no afectados por descuento masivo.

**Huecos:**
- Selección manual por `ids_producto` — el schema lo soporta
  (`SegmentoDescuento.ids_producto`), pero solo se probó filtro por `marca`.
- Combinar filtro + `ids_producto` a la vez (AND) — no probado.
- Consulta con múltiples filtros combinados a la vez (`categoria` +
  `tipo_producto` + `marca` juntos) — solo se probó un filtro por vez.

Quedan pendientes de cerrar en una sesión aparte — son casos nuevos, no
arreglos de lo ya escrito, y no bloquean nada de lo que ya está en verde.

## Al agregar un módulo nuevo

1. Extraer `FULLSTACK/module_<nombre>.md` del monolito (o pedir que se
   extraiga), del mismo tamaño/nivel de detalle que `module_pedidos.md`.
2. Escribir `test_<nombre>.py` usando las fixtures de `conftest.py` — no
   crear un cliente de prueba ni un login propio dentro del archivo.
3. Un archivo de test por módulo, nunca un mega-archivo — la razón de ser de
   esta carpeta es exactamente evitar el problema del `.md` monolítico, no
   reproducirlo en Python.
4. Actualizar la tabla de arriba.

## Por qué `cliente_prueba` no usa `POST /api/v1/clientes`

INC-02 (ver `REPORT.md §4.3`) hace que ese endpoint falle con
`IntegrityError`. El fixture crea el cliente directo en SQLAlchemy como
workaround documentado, en un solo lugar. Cuando se corrija el módulo
Clientes (paso 3 de la ruta de trabajo), el fixture cambia una vez en
`conftest.py` y todos los tests que dependen de él quedan corregidos sin
tocarlos.
