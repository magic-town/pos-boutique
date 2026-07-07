from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import Movimiento, Cliente, Operacion
from app.schemas.movimiento import MovimientoCreate
from app.services.cliente_service import sincronizar_estatus


def registrar_movimiento(db: Session, data: MovimientoCreate) -> Movimiento:
    """
    Orquesta el registro de una operación de caja.
    - Valida que el cliente exista cuando es requerido.
    - Calcula saldo_resultante según la operación.
    - Actualiza clientes.saldo en la misma transacción.
    - Sincroniza clientes.estatus (derivado de saldo, nunca manual) en la
      misma transacción -- ver cliente_service.sincronizar_estatus().
    """
    cliente = None
    saldo_resultante = None

    if data.id_cliente is not None:
        cliente = db.query(Cliente).filter(
            Cliente.id_cliente == data.id_cliente
        ).first()
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {data.id_cliente} no encontrado"
            )

    if data.operacion == Operacion.apartado:
        # monto = saldo pendiente (precio_total - primer_pago, calculado en el frontend)
        # El ingreso a caja del primer pago se registra como contado por separado.
        if data.monto < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El saldo pendiente del apartado no puede ser negativo"
            )
        saldo_resultante = round(data.monto, 2)
        cliente.saldo = saldo_resultante  # INC-05 pendiente (Movimientos): debería sumarse, no sobrescribirse
        sincronizar_estatus(cliente)

    elif data.operacion == Operacion.abono:
        nuevo_saldo = round(cliente.saldo - data.monto, 2)
        if nuevo_saldo < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"El abono (${data.monto:.2f}) supera el saldo actual "
                    f"(${cliente.saldo:.2f}) del cliente"
                )
            )
        saldo_resultante = nuevo_saldo
        cliente.saldo = nuevo_saldo
        sincronizar_estatus(cliente)

    movimiento = Movimiento(
        operacion=data.operacion,
        id_cliente=data.id_cliente,
        id_producto=data.id_producto,
        monto=data.monto,
        forma_pago=data.forma_pago,
        saldo_resultante=saldo_resultante,
        notas=data.notas,
    )

    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


def cancelar_movimiento(db: Session, id_movimiento: int) -> dict:
    """
    Cancela el último movimiento registrado para el cliente asociado.
    - Solo opera si es el movimiento más reciente del cliente.
    - Si el movimiento tenía saldo_resultante, recalcula clientes.saldo
      buscando el saldo_resultante del movimiento anterior.
    - Para contado y gasto (sin saldo) solo elimina el registro.
    - Regla: correcciones de registros históricos se hacen con abono
      compensatorio — este método no edita registros pasados.
    """
    movimiento = db.query(Movimiento).filter(
        Movimiento.id_movimiento == id_movimiento
    ).first()

    if not movimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movimiento {id_movimiento} no encontrado"
        )

    # Si tiene cliente, verificar que sea el último movimiento de ese cliente
    if movimiento.id_cliente is not None:
        ultimo = (
            db.query(Movimiento)
            .filter(Movimiento.id_cliente == movimiento.id_cliente)
            .order_by(Movimiento.fecha.desc(), Movimiento.id_movimiento.desc())
            .first()
        )
        if ultimo.id_movimiento != id_movimiento:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Solo se puede cancelar el último movimiento del cliente. "
                    "Para corregir registros anteriores, registra un abono compensatorio."
                )
            )

        # Revertir saldo del cliente
        if movimiento.saldo_resultante is not None:
            # Buscar el saldo_resultante del movimiento anterior
            anterior = (
                db.query(Movimiento)
                .filter(
                    Movimiento.id_cliente == movimiento.id_cliente,
                    Movimiento.id_movimiento != id_movimiento,
                    Movimiento.saldo_resultante.isnot(None)
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
