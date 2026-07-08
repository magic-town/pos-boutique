"""
Modelo de datos alineado a docs/FULL_STACK/*.md + docs/REGLAS_NEGOCIO.md
(fuentes de verdad — ver docs/REPORT.md §1 para la jerarquía completa).

13 tablas migradas y verificadas contra pos.db (alembic_version = c3d4e5f6a7b8):
clientes, pedidos, pedidos_articulos, precios_catalogo, inventario, movimientos,
shein_clientes, shein_pedidos, shein_pedidos_articulos, shein_cortes, recargas,
usuarios, configuracion. clientes incluye dia_pago_especifico y
frecuencia_pago_detalle como columnas reales (REGLAS_NEGOCIO.md §2).

Apartado (cabecera-detalle, ver docs/REPORT.md §3.3): las clases Apartado y
ApartadoArticulo, y la FK id_apartado en Movimiento, ya están escritas en este
archivo y verificadas columna por columna contra el diseño cerrado — pero
apartados y apartados_articulos todavía NO existen en pos.db (no aparecen en
.tables). Migración Alembic pendiente: agregar ambas tablas y la FK
id_apartado a movimientos.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey,
    Enum, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


# ──────────────────────────────────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────────────────────────────────

class FrecuenciaPago(enum.Enum):
    semanal = "semanal"
    quincenal = "quincenal"
    dia_especifico_mes = "dia_especifico_mes"
    otro = "otro"


class EstatusCliente(enum.Enum):
    activo = "activo"
    inactivo = "inactivo"


class RolArticulo(enum.Enum):
    principal = "principal"
    alternativa = "alternativa"


class TipoProducto(enum.Enum):
    formal = "formal"
    informal = "informal"


class Proveedor(enum.Enum):
    Price_Shoes = "Price_Shoes"
    Pakar = "Pakar"
    Cklass = "Cklass"
    otro = "otro"


class EstatusArticulo(enum.Enum):
    vigente = "vigente"
    en_almacen = "en_almacen"
    devuelto = "devuelto"
    cancelado = "cancelado"


class CategoriaInventario(enum.Enum):
    dama = "dama"
    caballero = "caballero"
    infantil = "infantil"
    accesorio = "accesorio"
    calzado = "calzado"


class EstatusInventario(enum.Enum):
    disponible = "disponible"
    disponible_c_descuento = "disponible_c/descuento"
    en_ruta = "en_ruta"
    apartado = "apartado"
    vendido = "vendido"


class Operacion(enum.Enum):
    contado = "contado"
    apartado = "apartado"
    abono = "abono"
    gasto = "gasto"


class FormaPago(enum.Enum):
    efectivo = "efectivo"
    transferencia = "transferencia"
    tarjeta = "tarjeta"


class Compania(enum.Enum):
    Telcel = "Telcel"
    Movistar = "Movistar"
    Unefon = "Unefon"
    ATT = "AT&T"


class ProveedorCatalogo(enum.Enum):
    """Subconjunto de Proveedor: precios_catalogo nunca aplica a 'otro'
    (ese proveedor no tiene catálogo digitalizado). No reutiliza el enum
    Proveedor de pedidos_articulos porque ese sí incluye 'otro'."""
    Price_Shoes = "Price_Shoes"
    Pakar = "Pakar"
    Cklass = "Cklass"


class TipoProductoShein(enum.Enum):
    """No reutiliza TipoProducto (formal/informal) de Pedidos — valores distintos."""
    Nacional = "Nacional"
    Importado = "Importado"


class EstatusArticuloShein(enum.Enum):
    """No reutiliza EstatusArticulo de Pedidos — ciclo de vida distinto,
    Shein no maneja 'en_almacen' ni 'devuelto'."""
    vigente = "vigente"
    confirmado = "confirmado"
    cancelado = "cancelado"


class EstatusPago(enum.Enum):
    pago_pendiente = "pago_pendiente"
    pagado = "pagado"


class EstatusApartado(enum.Enum):
    abierto = "abierto"
    liquidado = "liquidado"


class EstatusApartadoArticulo(enum.Enum):
    vigente = "vigente"
    vendido = "vendido"
    cancelado = "cancelado"


# ──────────────────────────────────────────────────────────────────────────
# MÓDULO CLIENTES
# ──────────────────────────────────────────────────────────────────────────

class Cliente(Base):
    __tablename__ = "clientes"

    id_cliente             = Column(Integer, primary_key=True, index=True)
    no_cliente              = Column(String, unique=True, index=True, nullable=False)
    nombre                  = Column(String(40), nullable=False)
    colonia                 = Column(String(20), nullable=False)
    telefono                = Column(Integer, nullable=False)            # 10 dígitos
    frecuencia_pago         = Column(Enum(FrecuenciaPago), nullable=False)
    dia_pago_especifico     = Column(Integer, nullable=True)   # 1-31; obligatorio solo si frecuencia_pago = dia_especifico_mes (validado en schema)
    frecuencia_pago_detalle = Column(String(60), nullable=True)  # obligatorio solo si frecuencia_pago = otro (validado en schema)
    ref_nombre              = Column(String(40), nullable=False)
    ref_colonia             = Column(String(40), nullable=False)
    ref_telefono            = Column(Integer, nullable=True)             # 10 dígitos, opcional
    saldo                   = Column(Float, nullable=False, default=0.0)
    estatus                 = Column(Enum(EstatusCliente), nullable=False,
                                      default=EstatusCliente.inactivo)
    fecha_registro          = Column(Date, server_default=func.current_date(), nullable=False)
    fecha_pago_programada   = Column(Date, nullable=True)   # NULL hasta el primer abono

    movimientos   = relationship("Movimiento", back_populates="cliente")
    pedidos       = relationship("Pedido", back_populates="cliente")
    apartados     = relationship("Apartado", back_populates="cliente")


# ──────────────────────────────────────────────────────────────────────────
# MÓDULO PEDIDOS (cabecera-detalle)
# ──────────────────────────────────────────────────────────────────────────

class Pedido(Base):
    """Cabecera. Un pedido agrupa de 1 a 4 artículos (pedidos_articulos)."""
    __tablename__ = "pedidos"

    id_pedido  = Column(Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False)
    fecha      = Column(Date, server_default=func.current_date(), nullable=False)

    cliente   = relationship("Cliente", back_populates="pedidos")
    articulos = relationship("PedidoArticulo", back_populates="pedido")


class PedidoArticulo(Base):
    """Detalle. Cada renglón es un artículo, con rol principal o alternativa."""
    __tablename__ = "pedidos_articulos"

    id_articulo            = Column(Integer, primary_key=True, index=True)
    id_pedido               = Column(Integer, ForeignKey("pedidos.id_pedido"), nullable=False)
    rol                     = Column(Enum(RolArticulo), nullable=False, default=RolArticulo.principal)
    id_articulo_principal   = Column(Integer, ForeignKey("pedidos_articulos.id_articulo"), nullable=True)
    tipo_producto           = Column(Enum(TipoProducto), nullable=False)
    proveedor               = Column(Enum(Proveedor), nullable=True)        # NULL si informal
    id_producto             = Column(String(12), nullable=True)             # referencia libre al catálogo del proveedor
    producto                = Column(String(40), nullable=False)
    marca                   = Column(String(20), nullable=True)
    talla                   = Column(String(8), nullable=True)
    monto                   = Column(Float, nullable=True)
    estatus_articulo        = Column(Enum(EstatusArticulo), nullable=False,
                                      default=EstatusArticulo.vigente)
    id_articulo_sustituye   = Column(Integer, ForeignKey("pedidos_articulos.id_articulo"), nullable=True)

    pedido = relationship("Pedido", back_populates="articulos", foreign_keys=[id_pedido])


class PrecioCatalogo(Base):
    """Catálogo de precios por proveedor, importado desde tabla_precios.ods
    vía script manual (importar_precios.py). Solo INSERT, nunca se borra ni
    sobreescribe — SQLite acumula historial completo. Sin UNIQUE: el mismo
    id_producto puede repetirse en catálogos futuros; desempate siempre por
    MAX(fecha_catalogo)."""
    __tablename__ = "precios_catalogo"

    id_precio      = Column(Integer, primary_key=True, index=True)
    proveedor      = Column(Enum(ProveedorCatalogo), nullable=False)
    id_producto    = Column(String(12), nullable=False)   # normalizado desde ID/CÓDIGO/modelo
    precio_venta   = Column(Integer, nullable=False)
    fecha_catalogo = Column(Date, nullable=False)

    # Columnas auxiliares del .ods, preservadas para fidelidad, no usadas por el POS:
    catalogo       = Column(String, nullable=True)
    temporada      = Column(String, nullable=True)
    pagina         = Column(Integer, nullable=True)
    precio_base    = Column(Integer, nullable=True)


# ──────────────────────────────────────────────────────────────────────────
# MÓDULO INVENTARIO
# ──────────────────────────────────────────────────────────────────────────

class Inventario(Base):
    __tablename__ = "inventario"

    id_producto       = Column(Integer, primary_key=True, index=True)
    categoria         = Column(Enum(CategoriaInventario), nullable=False)
    tipo_producto     = Column(Enum(TipoProducto), nullable=False)
    descripcion       = Column(String(40), nullable=False)
    talla             = Column(String(10), nullable=True)
    color             = Column(String(10), nullable=True)
    marca             = Column(String(12), nullable=True)
    precio_venta      = Column(Integer, nullable=False)
    precio_descuento  = Column(Integer, nullable=True)   # NULL = sin descuento activo
    stock             = Column(Integer, nullable=False, default=0)
    estatus           = Column(Enum(EstatusInventario), nullable=False,
                                default=EstatusInventario.disponible)
    descripcion_ruta  = Column(String, nullable=True)    # obligatorio solo si estatus = en_ruta (validado en service)
    created           = Column(Date, server_default=func.current_date(), nullable=False)
    changed_status    = Column(Date, nullable=True)      # autogenerado al cambiar estatus

    movimientos = relationship("Movimiento", back_populates="producto")
    apartados_articulos = relationship("ApartadoArticulo", back_populates="producto")


# ──────────────────────────────────────────────────────────────────────────
# PANEL PRINCIPAL — MOVIMIENTOS
# ──────────────────────────────────────────────────────────────────────────

class Movimiento(Base):
    __tablename__ = "movimientos"

    id_movimiento    = Column(Integer, primary_key=True, index=True)
    operacion        = Column(Enum(Operacion), nullable=False)
    id_cliente       = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=True)
    id_producto      = Column(Integer, ForeignKey("inventario.id_producto"), nullable=True)
    id_apartado      = Column(Integer, ForeignKey("apartados.id_apartado"), nullable=True)
    monto            = Column(Float, nullable=False)
    forma_pago       = Column(Enum(FormaPago), nullable=False)
    saldo_resultante = Column(Float, nullable=True)    # NULL en contado y gasto
    descripcion      = Column(String(60), nullable=True)  # obligatorio solo en 'gasto' (validado en schema)
    fecha            = Column(DateTime, server_default=func.now(), nullable=False)

    cliente  = relationship("Cliente", back_populates="movimientos")
    producto = relationship("Inventario", back_populates="movimientos")
    apartado = relationship("Apartado", back_populates="movimientos")


class Apartado(Base):
    __tablename__ = "apartados"

    id_apartado       = Column(Integer, primary_key=True, index=True)
    id_cliente        = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False)
    fecha_apartado    = Column(DateTime, server_default=func.now(), nullable=False)
    monto_primer_pago = Column(Float, nullable=False)
    saldo_pendiente   = Column(Float, nullable=False)
    estatus           = Column(Enum(EstatusApartado), nullable=False, default=EstatusApartado.abierto)

    cliente     = relationship("Cliente", back_populates="apartados")
    articulos   = relationship("ApartadoArticulo", back_populates="apartado")
    movimientos = relationship("Movimiento", back_populates="apartado")


class ApartadoArticulo(Base):
    __tablename__ = "apartados_articulos"

    id_apartado_articulo = Column(Integer, primary_key=True, index=True)
    id_apartado          = Column(Integer, ForeignKey("apartados.id_apartado"), nullable=False)
    id_producto          = Column(Integer, ForeignKey("inventario.id_producto"), nullable=True)
    precio_producto      = Column(Float, nullable=False)
    estatus_articulo     = Column(Enum(EstatusApartadoArticulo), nullable=False, default=EstatusApartadoArticulo.vigente)

    apartado = relationship("Apartado", back_populates="articulos")
    producto = relationship("Inventario", back_populates="apartados_articulos")


# ──────────────────────────────────────────────────────────────────────────
# MÓDULO SHEIN (independiente de clientes)
# ──────────────────────────────────────────────────────────────────────────

class SheinCliente(Base):
    __tablename__ = "shein_clientes"

    id_shein_cliente = Column(Integer, primary_key=True, index=True)
    nombre           = Column(String(20), nullable=False)
    colonia          = Column(String(12), nullable=False)
    telefono         = Column(Integer, nullable=False)   # 10 dígitos

    pedidos = relationship("SheinPedido", back_populates="cliente")


class SheinCorte(Base):
    __tablename__ = "shein_cortes"

    id_shein_corte  = Column(Integer, primary_key=True, index=True)
    fecha_corte     = Column(Date, nullable=False)
    total_pedidos   = Column(Integer, nullable=False)          # calculado por backend
    suma_pedidos    = Column(Float, nullable=False)             # renombrado desde suma_montos; calculado por backend
    total_ticket    = Column(Float, nullable=False)             # NUEVO: captura manual, pagado en OXXO
    cupon           = Column(Float, nullable=False)             # renombrado desde bono_monto; = suma_pedidos - total_ticket
    # porcentaje_bono ELIMINADO — el cupón ya no se estima por porcentaje interno.

    pedidos = relationship("SheinPedido", back_populates="corte")


class SheinPedido(Base):
    """Cabecera. Un pedido Shein agrupa de 1 a 4 artículos (shein_pedidos_articulos).
    CAMBIA respecto al diseño anterior: deja de ser tabla plana."""
    __tablename__ = "shein_pedidos"

    id_shein_pedido  = Column(Integer, primary_key=True, index=True)
    id_shein_cliente = Column(Integer, ForeignKey("shein_clientes.id_shein_cliente"), nullable=False)
    id_shein_corte   = Column(Integer, ForeignKey("shein_cortes.id_shein_corte"), nullable=True)
    estatus_pago     = Column(Enum(EstatusPago), nullable=True)   # NUEVO — por pedido, nunca en cliente/corte
    fecha            = Column(Date, server_default=func.current_date(), nullable=False)

    cliente   = relationship("SheinCliente", back_populates="pedidos")
    corte     = relationship("SheinCorte", back_populates="pedidos")
    articulos = relationship("SheinPedidoArticulo", back_populates="pedido")


class SheinPedidoArticulo(Base):
    """Detalle (tabla NUEVA). Cada renglón es un artículo Shein — sin concepto
    de alternativa: a diferencia de Pedidos, no aplica rol ni id_articulo_principal."""
    __tablename__ = "shein_pedidos_articulos"

    id_shein_articulo = Column(Integer, primary_key=True, index=True)
    id_shein_pedido    = Column(Integer, ForeignKey("shein_pedidos.id_shein_pedido"), nullable=False)
    id_articulo        = Column(String(20), nullable=True)   # referencia libre a la app Shein, sin FK real
    producto            = Column(String(60), nullable=False)
    tipo_producto        = Column(Enum(TipoProductoShein), nullable=False)
    monto                = Column(Float, nullable=False)       # precio al momento del pedido
    monto_vigente        = Column(Float, nullable=True)        # se llena si el precio varió (sube o baja) al corte
    estatus_articulo     = Column(Enum(EstatusArticuloShein), nullable=False,
                                   default=EstatusArticuloShein.vigente)

    pedido = relationship("SheinPedido", back_populates="articulos")


# ──────────────────────────────────────────────────────────────────────────
# MÓDULO RECARGAS TELEFÓNICAS
# ──────────────────────────────────────────────────────────────────────────

class Recarga(Base):
    __tablename__ = "recargas"

    id_recarga = Column(Integer, primary_key=True, index=True)
    compania   = Column(Enum(Compania), nullable=False)
    monto      = Column(Float, nullable=False)
    fecha      = Column(DateTime, server_default=func.now(), nullable=False)


# ──────────────────────────────────────────────────────────────────────────
# AUTENTICACIÓN
# ──────────────────────────────────────────────────────────────────────────

class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario      = Column(Integer, primary_key=True, index=True)
    usuario         = Column(String, unique=True, nullable=False, index=True)
    password_hash   = Column(String, nullable=False)   # bcrypt
    rol             = Column(String, nullable=False, default="estandar")  # estandar | admin
    activo          = Column(Integer, nullable=False, default=1)          # 1 = activo, 0 = desactivado
    fecha_registro  = Column(DateTime, server_default=func.now())


# ──────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────

class Configuracion(Base):
    __tablename__ = "configuracion"

    clave = Column(String, primary_key=True)
    valor = Column(String, nullable=False)
