from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import Pedido, Cliente
from app.schemas.pedido import PedidoCreate


def crear_pedido(db: Session, data: PedidoCreate) -> Pedido:
    cliente = db.query(Cliente).filter(
        Cliente.id_cliente == data.id_cliente
    ).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente {data.id_cliente} no encontrado"
        )

    pedido = Pedido(
        id_cliente=data.id_cliente,
        producto=data.producto,
        id_producto_externo=data.id_producto_externo,
        marca=data.marca,
        talla=data.talla,
        opcion_producto=data.opcion_producto,
        opcion_marca=data.opcion_marca,
        opcion_talla=data.opcion_talla,
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


def obtener_pedidos_cliente(db: Session, id_cliente: int) -> list[Pedido]:
    return (
        db.query(Pedido)
        .filter(Pedido.id_cliente == id_cliente)
        .order_by(Pedido.fecha.desc())
        .all()
    )
