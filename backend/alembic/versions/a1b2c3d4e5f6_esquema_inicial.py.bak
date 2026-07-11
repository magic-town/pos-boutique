"""esquema inicial — alineado a REGLAS_NEGOCIO.md / 00_FULLSTACK_DEVELOPMENT.md

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-29

Reemplaza por completo el historial anterior (38241ae2061c, 97592862ac88).
pos.db fue reseteado — no hay datos que migrar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── clientes ────────────────────────────────────────────────────────────
    op.create_table(
        'clientes',
        sa.Column('id_cliente', sa.Integer(), nullable=False),
        sa.Column('no_cliente', sa.String(), nullable=False),
        sa.Column('nombre', sa.String(length=40), nullable=False),
        sa.Column('colonia', sa.String(length=20), nullable=False),
        sa.Column('telefono', sa.Integer(), nullable=False),
        sa.Column('frecuencia_pago', sa.Enum(
            'semanal', 'quincenal', 'dia_especifico_mes', 'otro',
            name='frecuenciapago'), nullable=False),
        sa.Column('ref_nombre', sa.String(length=40), nullable=False),
        sa.Column('ref_colonia', sa.String(length=40), nullable=False),
        sa.Column('ref_telefono', sa.Integer(), nullable=True),
        sa.Column('saldo', sa.Float(), nullable=False),
        sa.Column('estatus', sa.Enum('activo', 'inactivo', name='estatuscliente'), nullable=False),
        sa.Column('fecha_registro', sa.Date(), server_default=sa.text('(CURRENT_DATE)'), nullable=False),
        sa.Column('fecha_pago_programada', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id_cliente'),
    )
    op.create_index(op.f('ix_clientes_id_cliente'), 'clientes', ['id_cliente'], unique=False)
    op.create_index(op.f('ix_clientes_no_cliente'), 'clientes', ['no_cliente'], unique=True)

    # ── pedidos (cabecera) ──────────────────────────────────────────────────
    op.create_table(
        'pedidos',
        sa.Column('id_pedido', sa.Integer(), nullable=False),
        sa.Column('id_cliente', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), server_default=sa.text('(CURRENT_DATE)'), nullable=False),
        sa.ForeignKeyConstraint(['id_cliente'], ['clientes.id_cliente']),
        sa.PrimaryKeyConstraint('id_pedido'),
    )
    op.create_index(op.f('ix_pedidos_id_pedido'), 'pedidos', ['id_pedido'], unique=False)

    # ── pedidos_articulos (detalle) ─────────────────────────────────────────
    op.create_table(
        'pedidos_articulos',
        sa.Column('id_articulo', sa.Integer(), nullable=False),
        sa.Column('id_pedido', sa.Integer(), nullable=False),
        sa.Column('rol', sa.Enum('principal', 'alternativa', name='rolarticulo'), nullable=False),
        sa.Column('id_articulo_principal', sa.Integer(), nullable=True),
        sa.Column('tipo_producto', sa.Enum('formal', 'informal', name='tipoproducto'), nullable=False),
        sa.Column('proveedor', sa.Enum(
            'Price_Shoes', 'Pakar', 'Cklass', 'otro', name='proveedor'), nullable=True),
        sa.Column('id_producto', sa.String(length=12), nullable=True),
        sa.Column('producto', sa.String(length=40), nullable=False),
        sa.Column('marca', sa.String(length=20), nullable=True),
        sa.Column('talla', sa.String(length=8), nullable=True),
        sa.Column('monto', sa.Float(), nullable=True),
        sa.Column('estatus_articulo', sa.Enum(
            'vigente', 'en_almacen', 'devuelto', 'cancelado', name='estatusarticulo'), nullable=False),
        sa.Column('id_articulo_sustituye', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['id_pedido'], ['pedidos.id_pedido']),
        sa.ForeignKeyConstraint(['id_articulo_principal'], ['pedidos_articulos.id_articulo']),
        sa.ForeignKeyConstraint(['id_articulo_sustituye'], ['pedidos_articulos.id_articulo']),
        sa.PrimaryKeyConstraint('id_articulo'),
    )
    op.create_index(op.f('ix_pedidos_articulos_id_articulo'), 'pedidos_articulos', ['id_articulo'], unique=False)

    # ── inventario ──────────────────────────────────────────────────────────
    op.create_table(
        'inventario',
        sa.Column('id_producto', sa.Integer(), nullable=False),
        sa.Column('categoria', sa.Enum(
            'dama', 'caballero', 'infantil', 'accesorio', 'calzado', name='categoriainventario'), nullable=False),
        sa.Column('tipo_producto', sa.Enum('formal', 'informal', name='tipoproducto'), nullable=False),
        sa.Column('descripcion', sa.String(length=40), nullable=False),
        sa.Column('talla', sa.String(length=10), nullable=True),
        sa.Column('color', sa.String(length=10), nullable=True),
        sa.Column('marca', sa.String(length=12), nullable=True),
        sa.Column('precio_venta', sa.Integer(), nullable=False),
        sa.Column('precio_descuento', sa.Integer(), nullable=True),
        sa.Column('stock', sa.Integer(), nullable=False),
        sa.Column('estatus', sa.Enum(
            'disponible', 'disponible_c/descuento', 'en_ruta', 'apartado', 'vendido',
            name='estatusinventario'), nullable=False),
        sa.Column('descripcion_ruta', sa.String(), nullable=True),
        sa.Column('created', sa.Date(), server_default=sa.text('(CURRENT_DATE)'), nullable=False),
        sa.Column('changed_status', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id_producto'),
    )
    op.create_index(op.f('ix_inventario_id_producto'), 'inventario', ['id_producto'], unique=False)

    # ── movimientos ─────────────────────────────────────────────────────────
    op.create_table(
        'movimientos',
        sa.Column('id_movimiento', sa.Integer(), nullable=False),
        sa.Column('operacion', sa.Enum('contado', 'apartado', 'abono', 'gasto', name='operacion'), nullable=False),
        sa.Column('id_cliente', sa.Integer(), nullable=True),
        sa.Column('id_producto', sa.Integer(), nullable=True),
        sa.Column('monto', sa.Float(), nullable=False),
        sa.Column('forma_pago', sa.Enum('efectivo', 'transferencia', 'tarjeta', name='formapago'), nullable=False),
        sa.Column('saldo_resultante', sa.Float(), nullable=True),
        sa.Column('descripcion', sa.String(length=60), nullable=True),
        sa.Column('fecha', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['id_cliente'], ['clientes.id_cliente']),
        sa.ForeignKeyConstraint(['id_producto'], ['inventario.id_producto']),
        sa.PrimaryKeyConstraint('id_movimiento'),
    )
    op.create_index(op.f('ix_movimientos_id_movimiento'), 'movimientos', ['id_movimiento'], unique=False)

    # ── shein_clientes ──────────────────────────────────────────────────────
    op.create_table(
        'shein_clientes',
        sa.Column('id_shein_cliente', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=20), nullable=False),
        sa.Column('colonia', sa.String(length=12), nullable=False),
        sa.Column('telefono', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id_shein_cliente'),
    )
    op.create_index(op.f('ix_shein_clientes_id_shein_cliente'), 'shein_clientes', ['id_shein_cliente'], unique=False)

    # ── shein_cortes ────────────────────────────────────────────────────────
    op.create_table(
        'shein_cortes',
        sa.Column('id_shein_corte', sa.Integer(), nullable=False),
        sa.Column('fecha_corte', sa.Date(), nullable=False),
        sa.Column('total_pedidos', sa.Integer(), nullable=False),
        sa.Column('suma_montos', sa.Float(), nullable=False),
        sa.Column('porcentaje_bono', sa.Float(), nullable=False),
        sa.Column('bono_monto', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id_shein_corte'),
    )
    op.create_index(op.f('ix_shein_cortes_id_shein_corte'), 'shein_cortes', ['id_shein_corte'], unique=False)

    # ── shein_pedidos ───────────────────────────────────────────────────────
    op.create_table(
        'shein_pedidos',
        sa.Column('id_shein_pedido', sa.Integer(), nullable=False),
        sa.Column('id_shein_cliente', sa.Integer(), nullable=False),
        sa.Column('id_shein_corte', sa.Integer(), nullable=True),
        sa.Column('producto', sa.String(), nullable=False),
        sa.Column('monto', sa.Float(), nullable=False),
        sa.Column('monto_vigente', sa.Float(), nullable=True),
        sa.Column('fecha', sa.Date(), server_default=sa.text('(CURRENT_DATE)'), nullable=False),
        sa.ForeignKeyConstraint(['id_shein_cliente'], ['shein_clientes.id_shein_cliente']),
        sa.ForeignKeyConstraint(['id_shein_corte'], ['shein_cortes.id_shein_corte']),
        sa.PrimaryKeyConstraint('id_shein_pedido'),
    )
    op.create_index(op.f('ix_shein_pedidos_id_shein_pedido'), 'shein_pedidos', ['id_shein_pedido'], unique=False)

    # ── recargas ────────────────────────────────────────────────────────────
    op.create_table(
        'recargas',
        sa.Column('id_recarga', sa.Integer(), nullable=False),
        sa.Column('compania', sa.Enum('Telcel', 'Movistar', 'Unefon', 'ATT', name='compania'), nullable=False),
        sa.Column('monto', sa.Float(), nullable=False),
        sa.Column('fecha', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id_recarga'),
    )
    op.create_index(op.f('ix_recargas_id_recarga'), 'recargas', ['id_recarga'], unique=False)

    # ── usuarios ────────────────────────────────────────────────────────────
    op.create_table(
        'usuarios',
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('usuario', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('rol', sa.String(), nullable=False),
        sa.Column('activo', sa.Integer(), nullable=False),
        sa.Column('fecha_registro', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id_usuario'),
    )
    op.create_index(op.f('ix_usuarios_id_usuario'), 'usuarios', ['id_usuario'], unique=False)
    op.create_index(op.f('ix_usuarios_usuario'), 'usuarios', ['usuario'], unique=True)

    # ── configuracion ───────────────────────────────────────────────────────
    op.create_table(
        'configuracion',
        sa.Column('clave', sa.String(), nullable=False),
        sa.Column('valor', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('clave'),
    )
    configuracion_table = sa.table(
        'configuracion',
        sa.column('clave', sa.String),
        sa.column('valor', sa.String),
    )
    op.bulk_insert(
        configuracion_table,
        [
            {'clave': 'pago_efectivo_activo', 'valor': '1'},
            {'clave': 'pago_transferencia_activo', 'valor': '1'},
            {'clave': 'pago_tarjeta_debito_activo', 'valor': '1'},
            {'clave': 'pago_tarjeta_credito_activo', 'valor': '1'},
            {'clave': 'pago_msi_activo', 'valor': '0'},
            {'clave': 'pago_vales_activo', 'valor': '0'},
            {'clave': 'clabe_1', 'valor': ''},
            {'clave': 'clabe_2', 'valor': ''},
            {'clave': 'zona_horaria', 'valor': 'America/Mexico_City'},
        ],
    )


def downgrade() -> None:
    op.drop_table('configuracion')
    op.drop_index(op.f('ix_usuarios_usuario'), table_name='usuarios')
    op.drop_index(op.f('ix_usuarios_id_usuario'), table_name='usuarios')
    op.drop_table('usuarios')
    op.drop_index(op.f('ix_recargas_id_recarga'), table_name='recargas')
    op.drop_table('recargas')
    op.drop_index(op.f('ix_shein_pedidos_id_shein_pedido'), table_name='shein_pedidos')
    op.drop_table('shein_pedidos')
    op.drop_index(op.f('ix_shein_cortes_id_shein_corte'), table_name='shein_cortes')
    op.drop_table('shein_cortes')
    op.drop_index(op.f('ix_shein_clientes_id_shein_cliente'), table_name='shein_clientes')
    op.drop_table('shein_clientes')
    op.drop_index(op.f('ix_movimientos_id_movimiento'), table_name='movimientos')
    op.drop_table('movimientos')
    op.drop_index(op.f('ix_inventario_id_producto'), table_name='inventario')
    op.drop_table('inventario')
    op.drop_index(op.f('ix_pedidos_articulos_id_articulo'), table_name='pedidos_articulos')
    op.drop_table('pedidos_articulos')
    op.drop_index(op.f('ix_pedidos_id_pedido'), table_name='pedidos')
    op.drop_table('pedidos')
    op.drop_index(op.f('ix_clientes_no_cliente'), table_name='clientes')
    op.drop_index(op.f('ix_clientes_id_cliente'), table_name='clientes')
    op.drop_table('clientes')
