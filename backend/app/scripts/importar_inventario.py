"""
Carga inicial (o por lote) de inventario_bz.ods -> tabla inventario.

Uso:
    python -m app.scripts.importar_inventario /ruta/a/inventario_bz.ods

Reglas (FULLSTACK/module_inventario.md, sección "Carga inicial"):
- Solo INSERT. Cada fila del .ods es un producto nuevo -- no hay clave
  natural en el archivo para detectar duplicados (a diferencia de
  tabla_precios.ods). Responsabilidad operativa: correr esto solo cuando hay
  mercancía genuinamente nueva.
- precio_descuento NUNCA viene del archivo -- siempre NULL al importar,
  igual que "Agregar Producto". El descuento es exclusivo del sistema
  (endpoints /inventario/descuento-masivo).
- Columnas esperadas (PROVISIONAL -- ajustar el diccionario COLUMNAS de abajo
  contra el archivo real cuando se suba con rótulos + muestra):
  categoria, tipo_producto, descripcion, talla, color, marca, precio_venta, stock.
"""

import argparse

import pandas as pd

from app.db.database import SessionLocal
from app.models.models import CategoriaInventario, EstatusInventario, Inventario, TipoProducto

# Nombres de columna esperados en el .ods -- AJUSTAR contra el archivo real.
COLUMNAS = {
    "categoria": "categoria",
    "tipo_producto": "tipo_producto",
    "descripcion": "descripcion",
    "talla": "talla",
    "color": "color",
    "marca": "marca",
    "precio_venta": "precio_venta",
    "stock": "stock",
}

MAX_LEN = {"descripcion": 40, "talla": 10, "color": 10, "marca": 12}


def _leer_filas(ruta_ods: str) -> list[dict]:
    df = pd.read_excel(ruta_ods, engine="odf")

    filas = []
    omitidas = 0
    for i, row in df.iterrows():
        try:
            categoria = CategoriaInventario(str(row[COLUMNAS["categoria"]]).strip().lower())
            tipo_producto = TipoProducto(str(row[COLUMNAS["tipo_producto"]]).strip().lower())
        except ValueError as e:
            print(f"  [AVISO] fila {i}: valor de enum inválido ({e}) -- omitida.")
            omitidas += 1
            continue

        descripcion = str(row[COLUMNAS["descripcion"]]).strip()
        if len(descripcion) > MAX_LEN["descripcion"]:
            print(f"  [AVISO] fila {i}: descripcion excede {MAX_LEN['descripcion']} caracteres -- omitida.")
            omitidas += 1
            continue

        def _campo_opcional(nombre_col, maxlen):
            val = row.get(COLUMNAS[nombre_col])
            if pd.isna(val):
                return None
            val = str(val).strip()
            if len(val) > maxlen:
                print(f"  [AVISO] fila {i}: {nombre_col} '{val}' excede {maxlen} caracteres -- se trunca.")
                return val[:maxlen]
            return val

        filas.append({
            "categoria": categoria,
            "tipo_producto": tipo_producto,
            "descripcion": descripcion,
            "talla": _campo_opcional("talla", MAX_LEN["talla"]),
            "color": _campo_opcional("color", MAX_LEN["color"]),
            "marca": _campo_opcional("marca", MAX_LEN["marca"]),
            "precio_venta": int(row[COLUMNAS["precio_venta"]]),
            "stock": int(row[COLUMNAS["stock"]]) if not pd.isna(row.get(COLUMNAS["stock"])) else 0,
        })

    if omitidas:
        print(f"\n{omitidas} fila(s) omitida(s) por error de formato.")
    return filas


def importar(ruta_ods: str) -> None:
    db = SessionLocal()
    try:
        filas = _leer_filas(ruta_ods)
        productos = [
            Inventario(
                **fila,
                precio_descuento=None,
                estatus=EstatusInventario.disponible,
                descripcion_ruta=None,
            )
            for fila in filas
        ]
        db.bulk_save_objects(productos)
        db.commit()
        print(f"\nTotal leídas: {len(filas)}")
        print(f"Total insertadas: {len(productos)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Carga inicial de inventario_bz.ods a la tabla inventario.")
    parser.add_argument("ruta_ods", help="Ruta al archivo inventario_bz.ods")
    args = parser.parse_args()
    importar(args.ruta_ods)


if __name__ == "__main__":
    main()
