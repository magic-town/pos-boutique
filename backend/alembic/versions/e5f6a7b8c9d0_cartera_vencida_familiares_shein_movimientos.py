"""agrega cartera_vencida, familiares, shein_movimientos y columnas cartera en shein_clientes

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-15

Rediseño POS (docs/REGLAS_NEGOCIO.md §2, §6):
- cartera_vencida: archivo de clientes morosos cancelados. Sin FKs.
- familiares: pares de clientes emparentados. FK doble a clientes.
- shein_movimientos: abonos a la cartera de crédito Shein. FK a shein_clientes.
- shein_clientes: agrega saldo, estatus, frecuencia_pago, dia_pago_especifico,
  frecuencia_pago_detalle, fecha_pago_programada.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. cartera_vencida (tabla independiente, sin FKs) ──────────────
    op.create_table(
        "cartera_vencida",
        sa.Column("id_cartera_vencida", sa.Integer(), primary_key=True, index=True),
        sa.Column("no_cliente_original", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("colonia", sa.String(), nullable=False),
        sa.Column("telefono", sa.Integer(), nullable=False),
        sa.Column("ref_nombre", sa.String(), nullable=False),
        sa.Column("ref_colonia", sa.String(), nullable=False),
        sa.Column("ref_telefono", sa.Integer(), nullable=True),
        sa.Column("saldo_cancelado", sa.Float(), nullable=False),
        sa.Column("fecha_registro_original", sa.String(), nullable=False),
        sa.Column("fecha_cancelacion", sa.String(), nullable=False),
    )

    # ── 2. familiares (pares de clientes emparentados) ────────────────
    op.create_table(
        "familiares",
        sa.Column("id_vinculo", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "id_cliente_a", sa.Integer(),
            sa.ForeignKey("clientes.id_cliente"), nullable=False,
        ),
        sa.Column(
            "id_cliente_b", sa.Integer(),
            sa.ForeignKey("clientes.id_cliente"), nullable=False,
        ),
        sa.CheckConstraint("id_cliente_a < id_cliente_b", name="ck_familiares_orden"),
        sa.UniqueConstraint("id_cliente_a", "id_cliente_b", name="uq_familiares"),
    )

    # ── 3. Columnas de cartera en shein_clientes ──────────────────────
    # SQLite no soporta ADD COLUMN con ENUM directamente; usamos batch mode.
    with op.batch_alter_table("shein_clientes") as batch_op:
        batch_op.add_column(sa.Column(
            "frecuencia_pago",
            sa.Enum("semanal", "quincenal", "dia_especifico_mes", "otro",
                    name="frecuenciapagoshein"),
            nullable=False,
            server_default="semanal",
        ))
        batch_op.add_column(sa.Column(
            "dia_pago_especifico", sa.Integer(), nullable=True,
        ))
        batch_op.add_column(sa.Column(
            "frecuencia_pago_detalle", sa.String(60), nullable=True,
        ))
        batch_op.add_column(sa.Column(
            "saldo", sa.Float(), nullable=False, server_default="0",
        ))
        batch_op.add_column(sa.Column(
            "estatus",
            sa.Enum("activo", "inactivo", name="estatussheincliente"),
            nullable=False,
            server_default="inactivo",
        ))
        batch_op.add_column(sa.Column(
            "fecha_pago_programada", sa.Date(), nullable=True,
        ))

    # ── 4. shein_movimientos (abonos a cartera Shein) ─────────────────
    op.create_table(
        "shein_movimientos",
        sa.Column("id_shein_movimiento", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "id_shein_cliente", sa.Integer(),
            sa.ForeignKey("shein_clientes.id_shein_cliente"), nullable=False,
        ),
        sa.Column("monto", sa.Float(), nullable=False),
        sa.Column(
            "forma_pago",
            sa.Enum("efectivo", "transferencia", "tarjeta",
                    name="formapagoshein"),
            nullable=False,
        ),
        sa.Column("saldo_resultante", sa.Float(), nullable=False),
        sa.Column(
            "fecha", sa.DateTime(),
            server_default=sa.func.now(), nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("shein_movimientos")

    with op.batch_alter_table("shein_clientes") as batch_op:
        batch_op.drop_column("fecha_pago_programada")
        batch_op.drop_column("estatus")
        batch_op.drop_column("saldo")
        batch_op.drop_column("frecuencia_pago_detalle")
        batch_op.drop_column("dia_pago_especifico")
        batch_op.drop_column("frecuencia_pago")

    op.drop_table("familiares")
    op.drop_table("cartera_vencida")
