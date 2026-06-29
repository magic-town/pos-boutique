# AVANCE_VALIDACION.md
## pos-boutique — Validación de avance por fase

> Este documento es para un ingeniero de software que necesita entender
> el estado actual del proyecto y verificar que lo construido funciona.
> Cada sección incluye qué se construyó, cómo verificarlo y qué falta.

**Última actualización:** 28 de junio de 2026
**Máquina de desarrollo:** `gabriel@actuary`

---

## Prerequisitos

```bash
cd ~/pos-boutique/backend
source venv/bin/activate
```

---

## Fase 0 — Homologación ✅ Completa

### Qué se construyó

- Modelo de datos: 11 tablas SQLite (6 originales + 5 nuevas definidas en FULL_STACK_DEVELOPMENT.md) con tipos, restricciones y relaciones definidas
- Control de versiones de base de datos con Alembic (2 migraciones aplicadas)
- Backend FastAPI modernizado: patrón `lifespan`, CORS, configuración centralizada
- Documentación homologada: reglas de negocio, enums, ciclo de vida del cliente

### Cómo verificarlo

```bash
# 1. Arrancar backend
uvicorn app.main:app --reload --port 8000

# En otra terminal:

# 2. Endpoints de salud
curl -s http://localhost:8000/ | python3 -m json.tool
# Esperado: {"status": "ok", "sistema": "pos-boutique", "version": "0.1.0"}

curl -s http://localhost:8000/ping | python3 -m json.tool
# Esperado: {"mensaje": "pong desde pos-boutique"}

# 3. Tablas en pos.db
sqlite3 ~/pos-boutique/backend/pos.db ".tables"
# Esperado (implementadas): alembic_version clientes inventario movimientos
#           pedidos pedidos_shein usuarios
# Pendientes según FULL_STACK_DEVELOPMENT.md: pedidos_articulos shein_clientes
#           shein_pedidos shein_cortes recargas configuracion

# 4. Migraciones aplicadas
alembic history
alembic current
# Esperado: 2 migraciones — esquema inicial + tabla usuarios

# 5. Enums del modelo
python3 -c "
from app.models.models import Operacion, FormaPago, EstatusInventario
print('Operacion:', [o.value for o in Operacion])
print('FormaPago:', [f.value for f in FormaPago])
print('EstatusInventario:', [e.value for e in EstatusInventario])
"
# Esperado:
# Operacion: ['contado', 'apartado', 'abono', 'gasto']
# FormaPago: ['efectivo', 'transferencia', 'tarjeta']
# EstatusInventario: ['disponible', 'vendido', 'disponible_c/descuento', 'en_ruta', 'apartado']
```

---

## Fase 1 — Backend funcional 🔄 En curso

### Qué se construyó

- **Schemas Pydantic** — validación de entrada y salida para todos los módulos:
  `ClienteCreate/Read`, `MovimientoCreate/Read`, `PedidoCreate/Read`,
  `PedidoSheinCreate/Read`, `UsuarioCreate/Read`, `Token/TokenData`
- **Servicios de lógica de negocio:**
  - `cliente_service` — crear cliente, generar `no_cliente`, buscar, rehabilitar
  - `movimiento_service` — registrar operación, calcular saldo, cancelar último movimiento
  - `pedido_service` — crear y consultar pedidos de catálogo
  - `pedido_shein_service` — crear y consultar pedidos Shein
  - `auth_service` — JWT, hash de passwords, verificación, `get_current_user`

### Qué falta

- Endpoints API REST (`api/v1/endpoints/`) — vacío
- Registro de routers en `main.py`
- Seed de usuarios iniciales (`sonia`, `operador2`)
- Tests unitarios (`tests/`)
- Migración de tabla `pedidos` al modelo cabecera + `pedidos_articulos`
- Tablas nuevas: `shein_clientes`, `shein_pedidos`, `shein_cortes`, `recargas`, `configuracion`
- Schemas Pydantic para módulos nuevos (Inventario extendido, Shein con cortes, Recargas, Consulta Global, Setting)
- Servicios para módulos nuevos (`inventario_service`, `shein_service`, `recarga_service`, `consulta_service`, `configuracion_service`)
- Campo `frecuencia_pago` y `fecha_pago_programada` en tabla `clientes`
- Sistema de banderas (🟡/🔴) para vencimiento de pagos
- `estatus` de clientes simplificado a `activo | inactivo`

### Cómo verificar lo construido

```bash
# 1. Verificar que schemas y servicios importan sin errores
python3 -c "
from app.schemas import (ClienteCreate, ClienteRead, ClienteResumen,
    MovimientoCreate, MovimientoRead, PedidoCreate, PedidoRead,
    PedidoSheinCreate, PedidoSheinRead, UsuarioCreate, UsuarioRead, Token)
from app.services.cliente_service import crear_cliente, buscar_clientes, rehabilitar_cliente
from app.services.movimiento_service import registrar_movimiento, cancelar_movimiento
from app.services.pedido_service import crear_pedido, obtener_pedidos_cliente
from app.services.pedido_shein_service import crear_pedido_shein, obtener_pedidos_shein_cliente
from app.services.auth_service import hash_password, verificar_password, crear_token, get_current_user
print('OK — todos los schemas y servicios importan correctamente')
"

# 2. Verificar validaciones de reglas de negocio en schemas
python3 -c "
from app.schemas import ClienteCreate, MovimientoCreate
from app.models.models import Operacion, FormaPago

try:
    ClienteCreate(nombre='', colonia='Centro', telefono='443', ref_nombre='Juan', ref_colonia='Centro')
except Exception:
    print('OK — nombre vacío rechazado')

try:
    MovimientoCreate(operacion=Operacion.contado, monto=-100, forma_pago=FormaPago.efectivo)
except Exception:
    print('OK — monto negativo rechazado')

try:
    MovimientoCreate(operacion=Operacion.abono, monto=100, forma_pago=FormaPago.efectivo)
except Exception:
    print('OK — abono sin cliente rechazado')

m = MovimientoCreate(operacion=Operacion.gasto, monto=50, forma_pago=FormaPago.tarjeta)
print(f'OK — gasto válido: {m.operacion.value}, \${m.monto}, {m.forma_pago.value}')
"

# 3. Verificar auth: hash, verificación y JWT
python3 -c "
from app.services.auth_service import hash_password, verificar_password, crear_token
from jose import jwt

h = hash_password('mipassword123')
print(f'OK — password hasheado: {h[:30]}...')

assert verificar_password('mipassword123', h) == True
print('OK — password correcto verificado')

assert verificar_password('passwordincorrecto', h) == False
print('OK — password incorrecto rechazado')

token = crear_token({'sub': 'operador_1', 'rol': 'estandar'})
payload = jwt.decode(token, 'pos-boutique-secret-key-cambiar-en-produccion', algorithms=['HS256'])
assert payload['sub'] == 'operador_1' and payload['rol'] == 'estandar'
print(f'OK — token válido: sub={payload[\"sub\"]}, rol={payload[\"rol\"]}')
"
```

### Criterio de Fase 1 completa

Desde `http://localhost:8000/docs` debe ser posible ejecutar todas las
operaciones del MVP sin tocar el frontend. El flujo completo de un ciclo
de cliente debe funcionar vía API:
`registro → apartado → abono → liquidado → rehabilitado`

---

## Módulos definidos en FULL_STACK_DEVELOPMENT.md — Pendientes de implementación

> Estos módulos están completamente especificados en `FULL_STACK_DEVELOPMENT.md`
> pero aún no tienen implementación en código.

> Corregido: se agrega tabla de módulos pendientes según la especificación completa.

| Módulo | Tablas | Operaciones | Estado |
|--------|--------|-------------|--------|
| Clientes (extendido) | `clientes` (campos nuevos) | Registrar, Editar, Consulta, Historial con banderas | ⏳ Pendiente |
| Pedidos (rediseñado) | `pedidos` + `pedidos_articulos` | Registrar Pedido (1–4 artículos), Devolución, Cancelación, Lista de Surtido | ⏳ Pendiente |
| Inventario (extendido) | `inventario` (campos nuevos) | Agregar Producto, Cambiar Estatus, Consulta con filtros | ⏳ Pendiente |
| Panel Principal | `movimientos` | Contado (Catálogo/Inventario), Apartado (mín $100), Abono, Gasto | 🔄 Parcial (servicios existen, endpoints no) |
| Shein (rediseñado) | `shein_clientes`, `shein_pedidos`, `shein_cortes` | Reg. Cliente, Reg. Pedido, Lista, Corte con bono | ⏳ Pendiente |
| Recargas Telefónicas | `recargas` | Registro de recarga, resumen diario | ⏳ Pendiente |
| Consulta Global | (solo lectura) | Ventas totales, por segmento, cartera | ⏳ Pendiente |
| Setting | `configuracion`, `usuarios` | Usuarios, métodos de pago, info sistema | ⏳ Pendiente |

---

## Infraestructura y máquinas

| Máquina | Rol | Estado |
|---------|-----|--------|
| `gabriel@actuary` | Desarrollo activo | ✅ Todo el desarrollo ocurre aquí |
| `sonia@envy` | Producción (tienda) | ⏳ Repo clonado, migraciones aplicadas, sin infraestructura activa |
| `gabriel@envy` | Espejo / respaldo | ⏳ Sincronizado vía `git pull` |

### Sobre `sonia@envy`

El sistema no está montado como servicio en `sonia@envy` todavía — y no debe estarlo.
El detonador para convertirla en servidor de producción es completar
el ✋ de Fase 3 en `gabriel@actuary` (sistema funcionando de extremo a extremo).

Cuando ese momento llegue, los pasos están documentados en:
- `docs/DEBUGGING.md` — sección **Servicio systemd en producción**
- `docs/CHECKLIST.md` — **Fase 4**

Para sincronizar `sonia@envy` con el estado actual de desarrollo:

```bash
# En sonia@envy vía SSH desde gabriel@actuary:
ssh sonia@<ip-tailscale>
cd ~/pos-boutique
git pull
cd backend
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```
