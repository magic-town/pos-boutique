from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class Operacion(enum.Enum):
    contado  = "contado"
    apartado = "apartado"
    abono    = "abono"
    gasto    = "gasto"


class FormaPago(enum.Enum):
    efectivo      = "efectivo"
    transferencia = "transferencia"
    tarjeta       = "tarjeta"


class EstatusInventario(enum.Enum):
    disponible           = "disponible"
    vendido              = "vendido"
    disponible_descuento = "disponible c/descuento"
    en_ruta              = "en_ruta"


class Cliente(Base):
    __tablename__ = "clientes"

    id_cliente     = Column(Integer, primary_key=True, index=True)
    no_cliente     = Column(String, unique=True, index=True, nullable=False)
    nombre         = Column(String, nullable=False)
    colonia        = Column(String, nullable=False)
    telefono       = Column(String, nullable=False)
    ref_nombre     = Column(String, nullable=False)
    ref_colonia    = Column(String, nullable=False)
    ref_telefono   = Column(String, nullable=True)
    saldo          = Column(Float, nullable=False, default=0.0)
    estatus        = Column(String, nullable=False, default="activo")  # activo | liquidado | rehabilitar
    fecha_registro = Column(DateTime, server_default=func.now())

    movimientos   = relationship("Movimiento", back_populates="cliente")
    pedidos       = relationship("Pedido", back_populates="cliente")
    pedidos_shein = relationship("PedidoShein", back_populates="cliente")


class Inventario(Base):
    __tablename__ = "inventario"

    id_producto    = Column(Integer, primary_key=True, index=True)
    categoria      = Column(String)                                        # ej. dama, caballero, niño
    estilo         = Column(String)                                        # ej. informal, formal
    descripcion    = Column(String, nullable=False)
    talla          = Column(String)
    color          = Column(String)
    marca          = Column(String)
    precio_venta   = Column(Float, nullable=False)
    stock          = Column(Integer, nullable=False, default=0)
    estatus        = Column(Enum(EstatusInventario), nullable=False,
                            default=EstatusInventario.disponible)
    change_status  = Column(DateTime, nullable=True)                       # fecha del último cambio de estatus
    fecha_registro = Column(DateTime, server_default=func.now())

    movimientos = relationship("Movimiento", back_populates="producto")


class Pedido(Base):
    __tablename__ = "pedidos"

    id_pedido           = Column(Integer, primary_key=True, index=True)
    id_cliente          = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False)
    producto            = Column(String, nullable=False)
    id_producto_externo = Column(String, nullable=True)   # ID del proveedor si lo tiene
    marca               = Column(String)
    talla               = Column(String)
    opcion_producto     = Column(String, nullable=True)
    opcion_marca        = Column(String, nullable=True)
    opcion_talla        = Column(String, nullable=True)
    fecha               = Column(DateTime, server_default=func.now())

    cliente = relationship("Cliente", back_populates="pedidos")


class PedidoShein(Base):
    __tablename__ = "pedidos_shein"

    id_pedido_shein = Column(Integer, primary_key=True, index=True)
    id_cliente      = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False)
    producto        = Column(String, nullable=False)
    monto           = Column(Float, nullable=False)
    fecha           = Column(DateTime, server_default=func.now())

    cliente = relationship("Cliente", back_populates="pedidos_shein")


class Movimiento(Base):
    __tablename__ = "movimientos"

    id_movimiento    = Column(Integer, primary_key=True, index=True)
    operacion        = Column(Enum(Operacion), nullable=False)
    id_cliente       = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=True)
    id_producto      = Column(Integer, ForeignKey("inventario.id_producto"), nullable=True)
    monto            = Column(Float, nullable=False)
    forma_pago       = Column(Enum(FormaPago), nullable=False)
    saldo_resultante = Column(Float, nullable=True)
    notas            = Column(String, nullable=True)
    fecha            = Column(DateTime, server_default=func.now())

    cliente  = relationship("Cliente", back_populates="movimientos")
    producto = relationship("Inventario", back_populates="movimientos")
