"""
Endpoints del módulo Pedidos (module_pedidos.md).

Reemplaza por completo app/api/v1/endpoints/pedidos.py (viejo, modelo plano)
-- REPORT.md §4.1 lo marca como reemplazo total, sin nada reutilizable.

NOTA DE INTEGRACIÓN: el import de get_current_user de abajo sigue el mismo
patrón de protección que REPORT.md confirma en clientes.py y movimientos.py
("Todos protegidos con Depends(get_current_user)"), pero auth_service.py no
se vio directamente en esta sesión (REPORT.md §4.2 lo marca como bloqueante
pendiente para el paso 7 de auth). Ajusta la ruta de este import si en tu
proyecto get_current_user vive en otro módulo.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.pedido import (
    ArticuloCancelableOut,
    ArticuloDevolvibleOut,
    CancelacionConfirmar,
    DevolucionConfirmar,
    DevolucionPrecarga,
    ListaSurtidoItem,
    MontoLookupOut,
    PedidoCreate,
    PedidoRead,
    ValidarClienteOut,
)
from app.services import pedido_service
from app.services.auth_service import get_current_user  # AJUSTA si la ruta real difiere

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


# ──────────────────────────────────────────────────────────────────────────
# Búsqueda previa de cliente (modal_busqueda_cliente_pedido)
# ──────────────────────────────────────────────────────────────────────────

@router.get("/clientes/{no_cliente}/validar", response_model=ValidarClienteOut)
def validar_cliente(
    no_cliente: str,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    cliente = pedido_service.resolver_cliente(db, no_cliente)
    return ValidarClienteOut(no_cliente=cliente.no_cliente, nombre=cliente.nombre)


# ──────────────────────────────────────────────────────────────────────────
# Lookup de precio en vivo (autollenado de monto en el formulario)
# ──────────────────────────────────────────────────────────────────────────

@router.get("/precio", response_model=MontoLookupOut)
def consultar_precio(
    proveedor: str,
    id_producto: str,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    from app.models.models import Proveedor

    monto = pedido_service.lookup_precio(db, Proveedor(proveedor), id_producto)
    return MontoLookupOut(encontrado=monto is not None, monto=float(monto) if monto is not None else None)


# ──────────────────────────────────────────────────────────────────────────
# Opción 1 — Registrar Pedido
# ──────────────────────────────────────────────────────────────────────────

@router.post("", response_model=PedidoRead, status_code=201)
def registrar_pedido(
    payload: PedidoCreate,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    return pedido_service.crear_pedido(db, payload)


# ──────────────────────────────────────────────────────────────────────────
# Opción 2 — Registrar Devolución
# ──────────────────────────────────────────────────────────────────────────

@router.get("/devolucion/{no_cliente}/articulos", response_model=list[ArticuloDevolvibleOut])
def listar_articulos_devolvibles(
    no_cliente: str,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    articulos = pedido_service.obtener_articulos_devolvibles(db, no_cliente)
    return [
        ArticuloDevolvibleOut(
            id_articulo=a.id_articulo,
            fecha=a.pedido.fecha,
            tipo_producto=a.tipo_producto,
            proveedor=a.proveedor,
            producto=a.producto,
            marca=a.marca,
            talla=a.talla,
            monto=a.monto,
        )
        for a in articulos
    ]


@router.post("/devolucion", response_model=DevolucionPrecarga)
def confirmar_devolucion(
    payload: DevolucionConfirmar,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    articulo = pedido_service.registrar_devolucion(db, payload.no_cliente, payload.id_articulo)
    return DevolucionPrecarga(
        tipo_producto=articulo.tipo_producto,
        proveedor=articulo.proveedor,
        marca=articulo.marca,
        talla=articulo.talla,
        id_articulo_sustituye=articulo.id_articulo,
    )


# ──────────────────────────────────────────────────────────────────────────
# Opción 3 — Cancelar Artículo
# ──────────────────────────────────────────────────────────────────────────

@router.get("/cancelacion/{no_cliente}/articulos", response_model=list[ArticuloCancelableOut])
def listar_articulos_cancelables(
    no_cliente: str,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    articulos = pedido_service.obtener_articulos_cancelables(db, no_cliente)
    return [
        ArticuloCancelableOut(
            id_articulo=a.id_articulo,
            fecha=a.pedido.fecha,
            producto=a.producto,
            marca=a.marca,
            talla=a.talla,
            proveedor=a.proveedor,
            monto=a.monto,
            estatus_articulo=a.estatus_articulo,
        )
        for a in articulos
    ]


@router.post("/cancelacion", status_code=200)
def confirmar_cancelacion(
    payload: CancelacionConfirmar,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    pedido_service.cancelar_articulo(db, payload.no_cliente, payload.id_articulo)
    return {"mensaje": "Artículo cancelado correctamente."}


# ──────────────────────────────────────────────────────────────────────────
# Opción 4 — Lista de Surtido
# ──────────────────────────────────────────────────────────────────────────

@router.get("/lista-surtido", response_model=list[ListaSurtidoItem])
def lista_surtido(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    filas = pedido_service.obtener_lista_surtido(db, fecha_inicio, fecha_fin)
    return [
        ListaSurtidoItem(
            id_articulo=f.id_articulo,
            no_cliente=f.no_cliente,
            nombre=f.nombre,
            rol=f.rol,
            producto=f.producto,
            marca=f.marca,
            talla=f.talla,
            proveedor=f.proveedor,
            id_producto=f.id_producto,
            monto=f.monto,
            fecha=f.fecha,
        )
        for f in filas
    ]


@router.patch("/lista-surtido/{id_articulo}/surtir", status_code=200)
def surtir_articulo(
    id_articulo: int,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    pedido_service.surtir_articulo(db, id_articulo)
    return {"mensaje": "Artículo marcado como en_almacen. Saldo actualizado."}
