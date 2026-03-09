from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class Operacion(enum.Enum):
    contado   = "contado"
    apartado  = "apartado"
    abono     = "abono"
    gasto     = "gasto"

class FormaPago(enum.Enum):
    efectivo     = "efectivo"
    transferencia = "transferencia"

class Cliente(Base):
    __tablename__ = "clientes"

    id_cliente  = Column(Integer, primary_key=True, index=True)
    no_cliente  = Column(String, unique=True, index=True)
    nombre      = Column(String, nullable=False)
    colonia     = Column(String, nullable=False)
    telefono    = Column(String, nullable=False)
    referencia_nombre   = Column(String)
    referencia_colonia  = Column(String)
    referencia_telefono = Column(String)
    saldo       = Column(Float, default=0.0)
    fecha_registro = Column(DateTime, server_default=func.now())

    movimientos     = relationship("Movimiento", back_populates="cliente")
    pedidos         = relationship("Pedido", back_populates="cliente")
    pedidos_shein   = relationship("PedidoShein", back_populates="cliente")

class Inventario(Base):
    __tablename__ = "inventario"

    id_producto  = Column(Integer, primary_key=True, index=True)
    descripcion  = Column(String, nullable=False)
    marca        = Column(String)
    talla        = Column(String)
    cantidad     = Column(Integer, default=1)
    precio       = Column(Float)
    fecha_registro = Column(DateTime, server_default=func.now())

    movimientos = relationship("Movimiento", back_populates="producto")

class Pedido(Base):
    __tablename__ = "pedidos"

    id_pedido   = Column(Integer, primary_key=True, index=True)
    id_cliente  = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False)
    producto    = Column(String, nullable=False)
    id_producto = Column(String, nullable=True)
    marca       = Column(String)
    talla       = Column(String)
    opcion_producto = Column(String)
    opcion_marca    = Column(String)
    opcion_talla    = Column(String)
    fecha       = Column(DateTime, server_default=func.now())

    cliente = relationship("Cliente", back_populates="pedidos")

class PedidoShein(Base):
    __tablename__ = "pedidos_shein"

    id_pedido_shein = Column(Integer, primary_key=True, index=True)
    id_cliente      = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False)
    producto        = Column(String, nullable=False)
    monto           = Column(Float)
    bono_aplicado   = Column(Float, default=0.0)
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
