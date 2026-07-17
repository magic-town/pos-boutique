import calendar
from datetime import date, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.models import Cliente, Apartado, CarteraVencida, Familiar, FrecuenciaPago
from app.schemas.cliente import ClienteCreate

MAX_VINCULOS_FAMILIARES = 4  # REPORT.md §3: hasta 4 vínculos por cliente, validado en servicio


def generar_no_cliente(db: Session, colonia: str) -> str:
    """
    Genera el identificador único del cliente.
    Formato: {Colonia}-{consecutivo con ceros}
    Ejemplo: Carrillos-001, Carrillos-002, Centro-001
    El consecutivo es independiente por colonia.
    """
    prefijo = colonia.strip().title()
    total = (
        db.query(Cliente)
        .filter(Cliente.no_cliente.like(f"{prefijo}-%"))
        .count()
    )
    consecutivo = total + 1
    return f"{prefijo}-{consecutivo:03d}"


def sincronizar_estatus(cliente: Cliente) -> None:
    """
    Deriva `estatus` a partir de `saldo` (REGLAS_NEGOCIO.md regla 1;
    module_clientes.md, enum `estatus`). NO es una decisión operativa: nunca
    se asigna a mano. `activo` si `saldo > 0`, `inactivo` si `saldo == 0`.
    Debe llamarse, en la misma transacción, en cualquier punto del sistema
    que modifique `cliente.saldo` -- Clientes, Pedidos o Movimientos.
    """
    cliente.estatus = "activo" if cliente.saldo > 0 else "inactivo"


def _sumar_un_mes(f: date) -> date:
    """
    Suma un mes calendario a `f`, ajustando al último día del mes destino si
    este tiene menos días (p. ej. 31-ene -> 28/29-feb). Se evita
    `timedelta(days=30)` porque desalinearía la fecha de vencimiento en
    meses de 28, 29 o 31 días.
    """
    year = f.year + (1 if f.month == 12 else 0)
    month = 1 if f.month == 12 else f.month + 1
    ultimo_dia_mes = calendar.monthrange(year, month)[1]
    return date(year, month, min(f.day, ultimo_dia_mes))


def calcular_bandera_naranja(db: Session, cliente: Cliente) -> bool:
    """
    Bandera naranja — alerta de apartado por vencer (module_movimientos.md
    §"Bandera naranja"; REPORT.md §5 Nivel 3, punto 7).

    Independiente de las banderas amarilla/roja del ciclo normal de pagos
    (`clientes.fecha_pago_programada`). Se calcula al vuelo, en lectura;
    no se persiste como columna.

    Semilla: `apartados.fecha_apartado` del apartado abierto del cliente
    (a lo más uno, por regla de negocio — module_movimientos.md regla 2).
    Activa cuando el apartado sigue `abierto` y faltan <=5 días para
    cumplirse 1 mes desde `fecha_apartado`. Se apaga al liquidarse.
    """
    apartado = (
        db.query(Apartado)
        .filter(Apartado.id_cliente == cliente.id_cliente, Apartado.estatus == "abierto")
        .order_by(Apartado.fecha_apartado.desc())
        .first()
    )
    if apartado is None:
        return False

    fecha_apartado = apartado.fecha_apartado
    if isinstance(fecha_apartado, datetime):
        fecha_apartado = fecha_apartado.date()

    vencimiento = _sumar_un_mes(fecha_apartado)
    umbral_activacion = vencimiento - timedelta(days=5)
    return date.today() >= umbral_activacion


def crear_cliente(db: Session, data: ClienteCreate) -> Cliente:
    no_cliente = generar_no_cliente(db, data.colonia)

    cliente = Cliente(
        no_cliente=no_cliente,
        nombre=data.nombre,
        colonia=data.colonia,
        telefono=data.telefono,
        ref_nombre=data.ref_nombre,
        ref_colonia=data.ref_colonia,
        ref_telefono=data.ref_telefono,
        frecuencia_pago=data.frecuencia_pago,  # INC-02: antes ausente, causaba IntegrityError
        dia_pago_especifico=data.dia_pago_especifico,
        frecuencia_pago_detalle=data.frecuencia_pago_detalle,
        saldo=0.0,
    )
    sincronizar_estatus(cliente)  # nace inactivo (saldo = 0)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def obtener_cliente(db: Session, id_cliente: int) -> Cliente | None:
    return db.query(Cliente).filter(Cliente.id_cliente == id_cliente).first()


def buscar_clientes(db: Session, q: str = "") -> list[Cliente]:
    """
    Búsqueda por nombre o no_cliente.
    Si q está vacío devuelve todos los clientes.
    """
    if not q:
        return db.query(Cliente).order_by(Cliente.nombre).all()
    termino = f"%{q.strip()}%"
    return (
        db.query(Cliente)
        .filter(
            Cliente.nombre.ilike(termino) | Cliente.no_cliente.ilike(termino)
        )
        .order_by(Cliente.nombre)
        .all()
    )


def cancelar_cliente(db: Session, id_cliente: int) -> CarteraVencida:
    """
    Cancela un cliente moroso (module_clientes.md §Operación "Cancelar
    Cliente"; REGLAS_NEGOCIO.md #3).

    Precondición: `bandera_roja` activa (`hoy > fecha_pago_programada` y
    `saldo > 0`). Si no se cumple, la operación se rechaza.

    Transacción:
    1. Snapshot de los datos actuales del cliente a `cartera_vencida`.
    2. Limpieza del slot en `clientes` — a diferencia de una versión previa
       de esta función, el `no_cliente` NO se renombra: permanece igual y
       queda disponible tal cual para que la operadora lo reasigne desde
       "Registrar Cliente" (modo `slot_disponible`). Solo se reescriben
       nombre/teléfono/frecuencia/referencia/fecha_pago_programada y se
       pone `saldo = 0` (con `estatus` resincronizado a `inactivo`).
       `id_cliente` y `no_cliente` no cambian; el historial de
       movimientos/pedidos/apartados sigue vinculado al mismo `id_cliente`.
    """
    cliente = obtener_cliente(db, id_cliente)
    if cliente is None:
        raise ValueError(f"Cliente {id_cliente} no encontrado")

    if not calcular_bandera_roja(cliente):
        raise ValueError("Este cliente no está en morosidad (bandera_roja). No se puede cancelar.")

    snapshot = CarteraVencida(
        no_cliente_original=cliente.no_cliente,
        nombre=cliente.nombre,
        colonia=cliente.colonia,
        telefono=cliente.telefono,
        ref_nombre=cliente.ref_nombre,
        ref_colonia=cliente.ref_colonia,
        ref_telefono=cliente.ref_telefono,
        saldo_cancelado=cliente.saldo,
        fecha_registro_original=cliente.fecha_registro.isoformat(),
        fecha_cancelacion=date.today().isoformat(),
    )
    db.add(snapshot)

    # Limpieza del slot — no_cliente y colonia se conservan tal cual.
    cliente.saldo = 0.0
    cliente.nombre = ""
    cliente.telefono = 0
    cliente.frecuencia_pago = FrecuenciaPago.otro
    cliente.dia_pago_especifico = None
    cliente.frecuencia_pago_detalle = "slot disponible"
    cliente.ref_nombre = ""
    cliente.ref_colonia = ""
    cliente.ref_telefono = None
    cliente.fecha_pago_programada = None
    sincronizar_estatus(cliente)  # saldo = 0 -> inactivo

    db.commit()
    db.refresh(snapshot)
    return snapshot


def calcular_bandera_amarilla(cliente: Cliente) -> bool:
    """
    Bandera amarilla — próximo a vencer (module_clientes.md §Sistema de
    banderas: `fecha_pago_programada - hoy <= 2 días`).

    Requiere `saldo > 0` y `fecha_pago_programada` no nulo (clientes con
    `frecuencia_pago = otro` nunca tienen `fecha_pago_programada`, y
    clientes con `saldo = 0` no generan amarilla ni roja aunque tengan
    fecha programada — ambos casos explícitos en la spec).

    Se acota a `0 <= dias_restantes <= 2` (no negativo) para no traslaparse
    con roja, que cubre el caso ya vencido (`hoy > fecha_pago_programada`).
    """
    if cliente.saldo <= 0 or cliente.fecha_pago_programada is None:
        return False
    dias_restantes = (cliente.fecha_pago_programada - date.today()).days
    return 0 <= dias_restantes <= 2


def calcular_bandera_roja(cliente: Cliente) -> bool:
    """
    Bandera roja — vencido (module_clientes.md §Sistema de banderas:
    `hoy > fecha_pago_programada`, con `saldo > 0` implícito: clientes con
    `saldo = 0` no generan roja aunque tengan fecha programada).

    También es la precondición de `cancelar_cliente()` (module_clientes.md
    §Operación "Cancelar Cliente").
    """
    if cliente.saldo <= 0 or cliente.fecha_pago_programada is None:
        return False
    return date.today() > cliente.fecha_pago_programada


def calcular_bandera_negra(db: Session, cliente: Cliente) -> bool:
    """
    Bandera negra — morosidad familiar (module_clientes.md §Sistema de
    banderas: "El cliente tiene bandera_roja Y al menos un familiar
    también tiene bandera_roja"). Se calcula al vuelo, no se persiste.
    """
    if not calcular_bandera_roja(cliente):
        return False

    vinculos = listar_familiares(db, cliente.id_cliente)
    for v in vinculos:
        familiar = obtener_cliente(db, v["id_cliente_relacionado"])
        if familiar is not None and calcular_bandera_roja(familiar):
            return True
    return False


def _contar_vinculos(db: Session, id_cliente: int) -> int:
    return (
        db.query(Familiar)
        .filter(
            or_(Familiar.id_cliente_a == id_cliente, Familiar.id_cliente_b == id_cliente)
        )
        .count()
    )


def listar_familiares(db: Session, id_cliente: int) -> list[dict]:
    """
    Devuelve los vínculos del cliente, ya normalizados desde la perspectiva
    de `id_cliente` (independientemente de si quedó guardado como
    `id_cliente_a` o `id_cliente_b` — ver Familiar en models.py). Cada item
    es un dict listo para construir FamiliarRead.
    """
    vinculos = (
        db.query(Familiar)
        .filter(
            or_(Familiar.id_cliente_a == id_cliente, Familiar.id_cliente_b == id_cliente)
        )
        .all()
    )
    resultado = []
    for v in vinculos:
        otro = v.cliente_b if v.id_cliente_a == id_cliente else v.cliente_a
        resultado.append(
            {
                "id_vinculo": v.id_vinculo,
                "id_cliente": id_cliente,
                "id_cliente_relacionado": otro.id_cliente,
                "nombre_relacionado": otro.nombre,
                "no_cliente_relacionado": otro.no_cliente,
            }
        )
    return resultado


def vincular_familiar(db: Session, id_cliente: int, id_cliente_relacionado: int) -> Familiar:
    """
    Declara un vínculo familiar entre dos clientes (REPORT.md §5, tarea 22;
    §3.3/§3.4 diseño de `familiares`). Sin transitividad, sin roles.

    Valida (en servicio, no hay constraint de BD para el tope):
    - Que ambos clientes existan.
    - Que no sea auto-vínculo.
    - Que el par no esté ya vinculado (en cualquier orden).
    - Que NINGUNO de los dos exceda MAX_VINCULOS_FAMILIARES (4) vínculos
      existentes — el tope aplica a ambos clientes del par, no solo a uno.
    """
    if id_cliente == id_cliente_relacionado:
        raise ValueError("Un cliente no puede vincularse consigo mismo")

    if obtener_cliente(db, id_cliente) is None:
        raise ValueError(f"Cliente {id_cliente} no encontrado")
    if obtener_cliente(db, id_cliente_relacionado) is None:
        raise ValueError(f"Cliente {id_cliente_relacionado} no encontrado")

    id_a, id_b = sorted((id_cliente, id_cliente_relacionado))

    ya_vinculados = (
        db.query(Familiar)
        .filter(Familiar.id_cliente_a == id_a, Familiar.id_cliente_b == id_b)
        .first()
    )
    if ya_vinculados is not None:
        raise ValueError("Estos clientes ya están vinculados como familiares")

    if _contar_vinculos(db, id_a) >= MAX_VINCULOS_FAMILIARES:
        raise ValueError(f"El cliente {id_a} ya alcanzó el máximo de {MAX_VINCULOS_FAMILIARES} vínculos familiares")
    if _contar_vinculos(db, id_b) >= MAX_VINCULOS_FAMILIARES:
        raise ValueError(f"El cliente {id_b} ya alcanzó el máximo de {MAX_VINCULOS_FAMILIARES} vínculos familiares")

    vinculo = Familiar(id_cliente_a=id_a, id_cliente_b=id_b)
    db.add(vinculo)
    db.commit()
    db.refresh(vinculo)
    return vinculo


def desvincular_familiar(db: Session, id_cliente: int, id_vinculo: int) -> None:
    """
    Elimina un vínculo familiar. Se exige `id_cliente` (no solo `id_vinculo`)
    para validar que quien pide la desvinculación es parte del vínculo —
    evita que cualquier id_vinculo válido se borre desde el endpoint de un
    cliente ajeno al par.
    """
    vinculo = db.query(Familiar).filter(Familiar.id_vinculo == id_vinculo).first()
    if vinculo is None:
        raise ValueError(f"Vínculo {id_vinculo} no encontrado")
    if id_cliente not in (vinculo.id_cliente_a, vinculo.id_cliente_b):
        raise ValueError(f"El cliente {id_cliente} no forma parte del vínculo {id_vinculo}")

    db.delete(vinculo)
    db.commit()