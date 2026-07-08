"""agrega apartados, apartados_articulos y FK id_apartado en movimientos

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-08

Diseño cerrado en docs/REPORT.md §3.3 / docs/REGLAS_NEGOCIO.md §5:
- apartados: cabecera del lote de apartado.
- apartados_articulos: detalle, 1 a N artículos por lote.
- movimientos.id_apartado: FK nullable, solo se usa cuando operacion='apartado'.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "apartados",
        sa.Column("id_apartado", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "id_cliente", sa.Integer(),
            sa.ForeignKey("clientes.id_cliente"), nullable=False,
        ),
        sa.Column(
            "fecha_apartado", sa.DateTime(),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column("monto_primer_pago", sa.Float(), nullable=False),
        sa.Column("saldo_pendiente", sa.Float(), nullable=False),
        sa.Column(
            "estatus",
            sa.Enum("abierto", "liquidado", name="estatusapartado"),
            nullable=False,
            server_default="abierto",
        ),
    )

    op.create_table(
        "apartados_articulos",
        sa.Column("id_apartado_articulo", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "id_apartado", sa.Integer(),
            sa.ForeignKey("apartados.id_apartado"), nullable=False,
        ),
        sa.Column(
            "id_producto", sa.Integer(),
            sa.ForeignKey("inventario.id_producto"), nullable=True,
        ),
        sa.Column("precio_producto", sa.Float(), nullable=False),
        sa.Column(
            "estatus_articulo",
            sa.Enum("vigente", "vendido", "cancelado", name="estatusapartadoarticulo"),
            nullable=False,
            server_default="vigente",
        ),
    )

    # SQLite no soporta ALTER TABLE ADD CONSTRAINT directo -> batch mode
    # (recrea la tabla internamente para agregar la FK).
    with op.batch_alter_table("movimientos") as batch_op:
        batch_op.add_column(sa.Column("id_apartado", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_movimientos_id_apartado",
            "apartados",
            ["id_apartado"],
            ["id_apartado"],
        )


def downgrade() -> None:
    with op.batch_alter_table("movimientos") as batch_op:
        batch_op.drop_constraint("fk_movimientos_id_apartado", type_="foreignkey")
        batch_op.drop_column("id_apartado")

    op.drop_table("apartados_articulos")
    op.drop_table("apartados")
