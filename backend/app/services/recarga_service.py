from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.models import Recarga
from app.schemas.recarga import RecargaCreate


def crear_recarga(db: Session, data: RecargaCreate) -> Recarga:
    """INSERT en recargas. `fecha` la genera el backend (server_default)."""
    recarga = Recarga(
        compania=data.compania,
        monto=data.monto,
    )
    db.add(recarga)
    db.commit()
    db.refresh(recarga)
    return recarga


def obtener_totales_dia(db: Session) -> list[dict]:
    """Resumen del día actual agrupado por compañía — ver module_recargas.md:
    SELECT compania, COUNT(*) AS qty, SUM(monto) AS total
    FROM recargas WHERE DATE(fecha) = DATE('now') GROUP BY compania."""
    filas = (
        db.query(
            Recarga.compania.label("compania"),
            func.count(Recarga.id_recarga).label("qty"),
            func.sum(Recarga.monto).label("total"),
        )
        .filter(func.date(Recarga.fecha) == func.date("now"))
        .group_by(Recarga.compania)
        .all()
    )
    return [{"compania": f.compania, "qty": f.qty, "total": f.total} for f in filas]
