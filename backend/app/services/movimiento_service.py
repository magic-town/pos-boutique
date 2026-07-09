"""
Lógica de negocio del Panel Principal -- Movimientos (REGLAS_NEGOCIO.md §5,
module_movimientos.md).

Apartado deja de manejarse dentro de registrar_movimiento() -- tiene su
propia cabecera+detalle (apartados / apartados_articulos) y su propio
schema (ApartadoCreate, app/schemas/apartado.py), mismo criterio de
separación que Pedidos tiene respecto a un movimiento genérico.

Invariante global respetada en todo este archivo (REGLAS_NEGOCIO.md §11):
el saldo del cliente NUNCA se sobrescribe -- siempre += o -=.
"""

from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import (
    Apartado,
    ApartadoArticulo,
    Cliente,
    EstatusApartado,
    EstatusApartadoArticulo,
    EstatusInventario,
    FrecuenciaPago,
    Inventario,
    Movimiento,
    Operacion,
)
from app.schemas.apartado import ApartadoCreate
from app.schemas.movimiento import MovimientoCreate
from app.services.cliente_service import sincronizar_estatus

_DISPONIBLES = (EstatusInventario.disponible, EstatusInventario.disponible_c_descuento)


# ──────────────────────────────────────────────────────────────────────────
# Helpers comunes
# ──────────────────────────────────────────────────────────────────────────

def _resolver_cliente(db: Session, id_cliente: int) -> Cliente:
    cliente = db.query(Cliente).filter(Cliente.id_cliente == id_cliente).first()
    if cliente is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Cliente {id_cliente} no encontrado"
        )
    return cliente


def _ultimo_dia_mes(anio: int, mes: int) -> int:
    if mes == 12:
        return 31
    return (date(anio, mes + 1, 1) - timedelta(days=1)).day


def _siguientes_meses(desde: date, cuantos: int = 3):
    """Genera (anio, mes) de 'desde' en adelante, para buscar la próxima
    ocurrencia de una fecha de calendario sin cruzar años a mano."""
    anio, mes = desde.year, desde.month
    for i in range(cuantos):
        m = mes + i
        a = anio + (m - 1) // 12
        m = (m - 1) % 12 + 1
        yield a, m


def _proxima_fecha_quincenal(desde: date) -> date:
    """Próxima fecha entre {día 15, último día del mes} posterior a 'desde'
    (REGLAS_NEGOCIO.md §2 regla 2, quincenal)."""
    candidatos = []
    for anio, mes in _siguientes_meses(desde):
        candidatos.append(date(anio, mes, 15))
        candidatos.append(date(anio, mes, _ultimo_dia_mes(anio, mes)))
    return min(c for c in candidatos if c > desde)


def _proxima_fecha_dia_especifico(desde: date, dia: int) -> date:
    """Próxima ocurrencia de 'dia' posterior a 'desde', con clamp al último
    día del mes si 'dia' no existe en ese mes (REGLAS_NEGOCIO.md §2 regla 2,
    dia_especifico_mes)."""
    for anio, mes in _siguientes_meses(desde):
        candidato = date(anio, mes, min(dia, _ultimo_dia_mes(anio, mes)))
        if candidato > desde:
            return candidato
    raise RuntimeError("No se encontró próxima fecha de pago en el rango buscado.")


def _recalcular_fecha_pago_programada(cliente: Cliente, fecha_abono: date) -> None:
    """Se recalcula en cada abono, nunca al registrar cliente ni apartado
    (REGLAS_NEGOCIO.md §2 regla 2)."""
    if cliente.frecuencia_pago == FrecuenciaPago.semanal:
        cliente.fecha_pago_programada = fecha_abono + timedelta(days=7)
    elif cliente.frecuencia_pago == FrecuenciaPago.quincenal:
        cliente.fecha_pago_programada = _proxima_fecha_quincenal(fecha_abono)
    elif cliente.frecuencia_pago == FrecuenciaPago.dia_especifico_mes:
        cliente.fecha_pago_programada = _proxima_fecha_dia_especifico(
            fecha_abono, cliente.dia_pago_especifico
        )
    # 'otro' -- el sistema nunca calcula esta fecha, permanece NULL siempre.


def _liquidar_apartado_si_corresponde(db: Session, apartado: Apartado) -> None:
    """REGLAS_NEGOCIO.md §5 regla 5. Artículos vigentes con id_producto
    existente pasan a vendido, igual que el inventario ligado."""
    if apartado.saldo_pendiente > 0:
        return

    apartado.estatus = EstatusApartado.liquidado

    articulos_vigentes = (
        db.query(ApartadoArticulo)
        .filter(
            ApartadoArticulo.id_apartado == apartado.id_apartado,
            ApartadoArticulo.estatus_articulo == EstatusApartadoArticulo.vigente,
            ApartadoArticulo.id_producto.isnot(None),
        )
        .all()
    )
    for articulo in articulos_vigentes:
        articulo.estatus_articulo = EstatusApartadoArticulo.vendido
        producto = (
            db.query(Inventario)
            .filter(Inventario.id_producto == articulo.id_producto)
            .first()
        )
        if producto is not None:
            producto.estatus = EstatusInventario.vendido
            producto.changed_status = date.today()


# ──────────────────────────────────────────────────────────────────────────
# Contado / Abono / Gasto
# ──────────────────────────────────────────────────────────────────────────

def registrar_movimiento(db: Session, data: MovimientoCreate) -> Movimiento:
    """Orquesta contado / abono / gasto. 'apartado' no se maneja aquí --
    usa crear_apartado() (module_movimientos.md, tabla 'Campos activos por
    operación': Apartado tiene forma/estructura propia, no genérica)."""
    if data.operacion == Operacion.apartado:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La operación 'apartado' usa el endpoint dedicado (ApartadoCreate), "
            "no registrar_movimiento().",
        )

    cliente = _resolver_cliente(db, data.id_cliente) if data.id_cliente is not None else None
    saldo_resultante = None
    id_producto_movimiento = None

    try:
        if data.operacion == Operacion.contado:
            if data.id_producto is not None:
                producto = (
                    db.query(Inventario)
                    .filter(
                        Inventario.id_producto == data.id_producto,
                        Inventario.estatus.in_(_DISPONIBLES),
                    )
                    .first()
                )
                if producto is not None:
                    producto.stock -= 1
                    if producto.stock <= 0:
                        producto.estatus = EstatusInventario.vendido
                    producto.changed_status = date.today()
                    id_producto_movimiento = producto.id_producto
                # Sin coincidencia: descripción/precio se capturaron a mano en el
                # frontend (van en 'monto'), sin efecto en inventario.

        elif data.operacion == Operacion.abono:
            if cliente is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, "Cliente no encontrado"
                )
            if data.monto > cliente.saldo:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"El abono (${data.monto:.2f}) supera el saldo actual "
                    f"(${cliente.saldo:.2f}) del cliente",
                )

            cliente.saldo -= data.monto  # invariante: nunca se sobrescribe
            saldo_resultante = round(cliente.saldo, 2)

            fecha_abono = date.today()
            _recalcular_fecha_pago_programada(cliente, fecha_abono)

            apartado_abierto = (
                db.query(Apartado)
                .filter(
                    Apartado.id_cliente == cliente.id_cliente,
                    Apartado.estatus == EstatusApartado.abierto,
                )
                .first()
            )
            if apartado_abierto is not None:
                apartado_abierto.saldo_pendiente = round(
                    apartado_abierto.saldo_pendiente - data.monto, 2
                )
                _liquidar_apartado_si_corresponde(db, apartado_abierto)

            sincronizar_estatus(cliente)  # auto activo/inactivo, nunca manual

        # 'gasto': sin cliente ni producto, descripcion ya validada obligatoria
        # en el schema (MovimientoCreate) -- ver app/schemas/movimiento.py.

        movimiento = Movimiento(
            operacion=data.operacion,
            id_cliente=data.id_cliente,
            id_producto=id_producto_movimiento,
            monto=data.monto,
            forma_pago=data.forma_pago,
            saldo_resultante=saldo_resultante,
            descripcion=data.descripcion,
        )
        db.add(movimiento)
        db.commit()
        db.refresh(movimiento)
        return movimiento
    except Exception:
        db.rollback()
        raise


def cancelar_movimiento(db: Session, id_movimiento: int) -> dict:
    """Cancela el último movimiento registrado para el cliente asociado.
    Correcciones de registros históricos se hacen con abono compensatorio
    -- este método no edita registros pasados (module_movimientos.md,
    regla 10 de Apartado, aplicada aquí a Movimientos en general)."""
    movimiento = (
        db.query(Movimiento).filter(Movimiento.id_movimiento == id_movimiento).first()
    )
    if not movimiento:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Movimiento {id_movimiento} no encontrado"
        )

    if movimiento.id_cliente is not None:
        ultimo = (
            db.query(Movimiento)
            .filter(Movimiento.id_cliente == movimiento.id_cliente)
            .order_by(Movimiento.fecha.desc(), Movimiento.id_movimiento.desc())
            .first()
        )
        if ultimo.id_movimiento != id_movimiento:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Solo se puede cancelar el último movimiento del cliente. "
                "Para corregir registros anteriores, registra un abono compensatorio.",
            )

        if movimiento.saldo_resultante is not None:
            anterior = (
                db.query(Movimiento)
                .filter(
                    Movimiento.id_cliente == movimiento.id_cliente,
                    Movimiento.id_movimiento != id_movimiento,
                    Movimiento.saldo_resultante.isnot(None),
                )
                .order_by(Movimiento.fecha.desc(), Movimiento.id_movimiento.desc())
                .first()
            )
            cliente = db.query(Cliente).filter(
                Cliente.id_cliente == movimiento.id_cliente
            ).first()
            cliente.saldo = anterior.saldo_resultante if anterior else 0.0
            sincronizar_estatus(cliente)

    db.delete(movimiento)
    db.commit()
    return {"detail": f"Movimiento {id_movimiento} cancelado correctamente"}


def obtener_movimientos_cliente(db: Session, id_cliente: int) -> list[Movimiento]:
    return (
        db.query(Movimiento)
        .filter(Movimiento.id_cliente == id_cliente)
        .order_by(Movimiento.fecha.desc())
        .all()
    )


# ──────────────────────────────────────────────────────────────────────────
# Apartado (module_movimientos.md, 'Comportamiento -- Registrar Apartado')
# ──────────────────────────────────────────────────────────────────────────

def obtener_apartado_abierto(db: Session, id_cliente: int) -> Apartado | None:
    """Usado por Abono para mostrar saldo_pendiente en vivo al buscar
    cliente (module_movimientos.md, 'Abonar / Liquidar' paso 1)."""
    return (
        db.query(Apartado)
        .filter(Apartado.id_cliente == id_cliente, Apartado.estatus == EstatusApartado.abierto)
        .first()
    )


def crear_apartado(db: Session, data: ApartadoCreate) -> Apartado:
    """Transacción única: cabecera + detalle + movimiento de caja + saldo +
    inventario (REGLAS_NEGOCIO.md §5, reglas de Apartado 1-4)."""
    cliente = _resolver_cliente(db, data.id_cliente)

    if obtener_apartado_abierto(db, cliente.id_cliente) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El cliente ya tiene un apartado abierto. Debe liquidarse antes de "
            "registrar uno nuevo.",
        )

    try:
        # Resolver cada artículo: lookup en inventario si hay id_producto,
        # autollenado gana sobre lo capturado (mismo criterio que
        # _resolver_monto en pedido_service.py).
        resueltos = []  # (id_producto_o_None, precio, producto_o_None)
        total = 0.0
        for art in data.articulos:
            producto = None
            precio = art.precio_producto
            if art.id_producto is not None:
                producto = (
                    db.query(Inventario)
                    .filter(
                        Inventario.id_producto == art.id_producto,
                        Inventario.estatus.in_(_DISPONIBLES),
                    )
                    .first()
                )
                if producto is not None:
                    precio = float(producto.precio_venta)

            if precio is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "precio_producto es obligatorio cuando id_producto no tiene "
                    "coincidencia en inventario.",
                )

            total += precio
            resueltos.append((producto.id_producto if producto else None, precio, producto))

        saldo_pendiente = round(total - data.monto_primer_pago, 2)

        apartado = Apartado(
            id_cliente=cliente.id_cliente,
            monto_primer_pago=data.monto_primer_pago,
            saldo_pendiente=saldo_pendiente,
            estatus=EstatusApartado.abierto,
        )
        db.add(apartado)
        db.flush()  # necesitamos id_apartado para el detalle y el movimiento

        for id_producto, precio, producto in resueltos:
            db.add(
                ApartadoArticulo(
                    id_apartado=apartado.id_apartado,
                    id_producto=id_producto,
                    precio_producto=precio,
                    estatus_articulo=EstatusApartadoArticulo.vigente,
                )
            )
            if producto is not None:
                producto.estatus = EstatusInventario.apartado
                producto.changed_status = date.today()

        cliente.saldo += saldo_pendiente  # invariante: nunca se sobrescribe
        sincronizar_estatus(cliente)

        db.add(
            Movimiento(
                operacion=Operacion.apartado,
                id_cliente=cliente.id_cliente,
                id_apartado=apartado.id_apartado,
                monto=data.monto_primer_pago,
                forma_pago=data.forma_pago,
                saldo_resultante=saldo_pendiente,
            )
        )

        db.commit()
        db.refresh(apartado)
        return apartado
    except Exception:
        db.rollback()
        raise


def cancelar_articulo_apartado(db: Session, id_apartado_articulo: int) -> ApartadoArticulo:
    """REGLAS_NEGOCIO.md §5, regla 6. No ajusta saldo_pendiente ni
    clientes.saldo -- la deuda permanece. El cliente puede cancelar 1, 2, o
    todos los artículos del lote uno por uno -- el lote (apartados) nunca se
    da de baja como unidad: sigue 'abierto' hasta que saldo_pendiente llega
    a 0 vía abonos, sin importar cuántos artículos se hayan cancelado."""
    articulo = (
        db.query(ApartadoArticulo)
        .filter(ApartadoArticulo.id_apartado_articulo == id_apartado_articulo)
        .first()
    )
    if articulo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artículo de apartado no encontrado.")
    if articulo.estatus_articulo != EstatusApartadoArticulo.vigente:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Solo se pueden cancelar artículos en estatus 'vigente'.",
        )

    try:
        articulo.estatus_articulo = EstatusApartadoArticulo.cancelado
        if articulo.id_producto is not None:
            producto = (
                db.query(Inventario)
                .filter(Inventario.id_producto == articulo.id_producto)
                .first()
            )
            if producto is not None:
                producto.estatus = EstatusInventario.disponible
                producto.changed_status = date.today()

        db.commit()
        db.refresh(articulo)
        return articulo
    except Exception:
        db.rollback()
        raise