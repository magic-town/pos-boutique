from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import PedidoShein, Cliente
from app.schemas.pedido_shein import PedidoSheinCreate


def crear_pedido_shein(db: Session, data: PedidoSheinCreate) -> PedidoShein:
    cliente = db.query(Cliente).filter(
        Cliente.id_cliente == data.id_cliente
    ).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente {data.id_cliente} no encontrado"
        )

    pedido = PedidoShein(
        id_cliente=data.id_cliente,
        producto=data.producto,
        monto=data.monto,
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


def obtener_pedidos_shein_cliente(db: Session, id_cliente: int) -> list[PedidoShein]:
    return (
        db.query(PedidoShein)
        .filter(PedidoShein.id_cliente == id_cliente)
        .order_by(PedidoShein.fecha.desc())
        .all()
    )
