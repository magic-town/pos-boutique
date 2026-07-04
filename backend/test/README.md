# Tests automatizados — convención

Reemplaza el propósito de verificación (no el de aprendizaje) de las guías
`aux_*.md`: en vez de descifrar tokens y pegar `curl` a mano cada vez que se
toca un módulo, esta suite reconstruye el escenario completo en segundos.

Las guías `aux_*.md` **no desaparecen** — le siguen sirviendo a una persona
nueva para *entender* el flujo paso a paso. Esta carpeta es para *verificar*
que el flujo sigue funcionando, sin explicar nada.

## Cómo correr

```bash
cd backend
pip install pytest httpx --break-system-packages
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

| Módulo | `FULLSTACK/module_*.md` | `test_*.py` |
|---|---|---|
| Pedidos | ✅ existe | ✅ `test_pedidos.py` (no corrido aún) |
| Inventario | ✅ existe | ✅ `test_inventario.py` (no corrido aún) |
| Shein | ✅ existe | ❌ pendiente (código existente, sin test) |
| Clientes | ✅ existe | ❌ pendiente (bloqueado por INC-02) |
| Movimientos | ✅ existe | ❌ pendiente (bloqueado por INC-05/06) |
| Recargas | ✅ existe | ❌ pendiente (sin código todavía) |
| Consulta | ✅ existe | ❌ pendiente (sin código todavía) |
| Setting | ✅ existe | ❌ pendiente (Auth existente; Setting sin código) |

Ver `docs/FULLSTACK/README.md` para el detalle de cada uno (es la fuente de
verdad de esta tabla — actualízala ahí primero, luego refleja aquí).

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
