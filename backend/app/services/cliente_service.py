from sqlalchemy.orm import Session
from app.models.models import Cliente
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
        estatus="activo",
    )
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


def rehabilitar_cliente(db: Session, id_cliente: int) -> Cliente | None:
    """
    Cambia estatus de 'inactivo' a 'activo'.
    Solo opera si el cliente existe y está en estatus 'inactivo'.
    'liquidado' no es un valor válido del enum EstatusCliente (INC-07);
    era código muerto porque ningún cliente podía llegar a tenerlo.
    """
    cliente = obtener_cliente(db, id_cliente)
    if not cliente:
        return None
    if cliente.estatus == "inactivo":
        cliente.estatus = "activo"
        db.commit()
        db.refresh(cliente)
    return cliente
