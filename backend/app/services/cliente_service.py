import calendar
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session
from app.models.models import Cliente, Apartado
from app.schemas.cliente import ClienteCreate


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