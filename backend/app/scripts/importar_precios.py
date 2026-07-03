"""
Sincroniza tabla_precios.ods -> tabla precios_catalogo en SQLite.

Uso:
    python -m app.scripts.importar_precios /ruta/a/tabla_precios.ods

Reglas (REGLAS_NEGOCIO.md §3, invariantes globales §11):
- Solo hace INSERT. Nunca borra ni sobreescribe filas existentes.
- Una fila es "nueva" si la combinación (proveedor, id_producto, fecha_catalogo)
  no existe ya en precios_catalogo. El desempate de precio vigente en tiempo de
  consulta se resuelve después, por MAX(fecha_catalogo) -- este script no decide
  eso, solo acumula historial.
- La columna "redondea" presente en las 3 pestañas del .ods se descarta
  deliberadamente: no forma parte del modelo de datos (decisión confirmada,
  ver sesión de desarrollo -- no está en models.py ni en REGLAS_NEGOCIO.md).

Estructura de pestañas (REGLAS_NEGOCIO.md §3.1 / module_pedidos.md):

    Pestaña        Columna id   Columna precio   Columna base    Formato fecha
    price_shoes    ID           precio_venta     Sug_credito     "DD-mes_es-YYYY"
    pakar          CÓDIGO       precio_venta     2 PAGO          "DD-mes_es-YYYY"
    cklass         modelo       precio_venta     precio_base     ISO YYYY-MM-DD

Columnas auxiliares (catalogo, temporada, pagina) se preservan por fidelidad
al archivo original, igual que precio_base -- no se usan por el POS pero se
guardan (REGLAS_NEGOCIO.md §3, PrecioCatalogo).
"""

import argparse
import sys
from datetime import date, datetime

import pandas as pd

from app.db.database import SessionLocal
from app.models.models import PrecioCatalogo, ProveedorCatalogo

# id_producto está definido como String(12) en el modelo (REGLAS_NEGOCIO.md §3).
MAX_LEN_ID_PRODUCTO = 12

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Mapeo de cada pestaña a su configuración de columnas reales del .ods.
PESTANAS = {
    "price_shoes": {
        "proveedor": ProveedorCatalogo.Price_Shoes,
        "col_id": "ID",
        "col_precio": "precio_venta",
        "col_base": "Sug_credito",
        "col_catalogo": "catalogo",
        "col_temporada": "temp",
        "col_pagina": "Pag",
        "col_fecha": "fecha",
        "fecha_formato": "texto_es",
    },
    "pakar": {
        "proveedor": ProveedorCatalogo.Pakar,
        "col_id": "CÓDIGO",
        "col_precio": "precio_venta",
        "col_base": "2 PAGO",
        "col_catalogo": "catalogo",
        "col_temporada": "temporada",
        "col_pagina": "PÁG.",
        "col_fecha": "fecha",
        "fecha_formato": "texto_es",
    },
    "cklass": {
        "proveedor": ProveedorCatalogo.Cklass,
        "col_id": "modelo",
        "col_precio": "precio_venta",
        "col_base": "precio_base",
        "col_catalogo": "catalogo",
        "col_temporada": "temp",
        "col_pagina": "pag",
        "col_fecha": "fecha",
        "fecha_formato": "iso",
    },
}


def _parsear_fecha_texto_es(valor: str) -> date:
    """'02-mayo-2026' -> date(2026, 5, 2)."""
    dia_str, mes_str, anio_str = str(valor).strip().split("-")
    mes = MESES_ES.get(mes_str.strip().lower())
    if mes is None:
        raise ValueError(f"Mes en español no reconocido: '{mes_str}' (valor original: '{valor}')")
    return date(int(anio_str), mes, int(dia_str))


def _parsear_fecha_iso(valor) -> date:
    if isinstance(valor, date):
        return valor
    return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date()


def _parsear_pagina(valor) -> int | None:
    """pagina es auxiliar (no usada por el POS, REGLAS_NEGOCIO.md §3). En datos
    reales aparecen valores alfanuméricos (p. ej. '166BEBES'); se guardan como
    NULL en vez de fallar el import -- decisión confirmada: no tiene
    implicaciones en el archivo original ni en el sistema, la columna no se
    usa por el POS."""
    if pd.isna(valor):
        return None
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None


def _normalizar_fecha(valor, formato: str) -> date:
    if formato == "texto_es":
        return _parsear_fecha_texto_es(valor)
    if formato == "iso":
        return _parsear_fecha_iso(valor)
    raise ValueError(f"Formato de fecha desconocido: {formato}")


def _leer_pestana(ruta_ods: str, pestana: str, config: dict) -> list[dict]:
    """Lee una pestaña y devuelve filas normalizadas listas para insertar."""
    df = pd.read_excel(ruta_ods, sheet_name=pestana, engine="odf")

    filas = []
    omitidas = 0
    for i, row in df.iterrows():
        id_producto = str(row[config["col_id"]]).strip()
        if len(id_producto) > MAX_LEN_ID_PRODUCTO:
            print(
                f"  [AVISO] {pestana} fila {i}: id_producto '{id_producto}' excede "
                f"{MAX_LEN_ID_PRODUCTO} caracteres -- omitida.",
                file=sys.stderr,
            )
            omitidas += 1
            continue

        try:
            fecha_catalogo = _normalizar_fecha(row[config["col_fecha"]], config["fecha_formato"])
        except ValueError as e:
            print(f"  [AVISO] {pestana} fila {i}: fecha inválida ({e}) -- omitida.", file=sys.stderr)
            omitidas += 1
            continue

        filas.append({
            "proveedor": config["proveedor"],
            "id_producto": id_producto,
            "precio_venta": int(row[config["col_precio"]]),
            "fecha_catalogo": fecha_catalogo,
            "catalogo": None if pd.isna(row.get(config["col_catalogo"])) else str(row.get(config["col_catalogo"])),
            "temporada": None if pd.isna(row.get(config["col_temporada"])) else str(row.get(config["col_temporada"])),
            "pagina": _parsear_pagina(row.get(config["col_pagina"])),
            "precio_base": None if pd.isna(row.get(config["col_base"])) else int(row.get(config["col_base"])),
        })

    if omitidas:
        print(f"  {pestana}: {omitidas} fila(s) omitida(s) por error de formato.")
    return filas


def importar(ruta_ods: str) -> None:
    db = SessionLocal()
    try:
        # Claves ya existentes en SQLite -- se cargan una sola vez para no
        # golpear la BD fila por fila contra ~25,000 registros del .ods.
        existentes = {
            (p.proveedor, p.id_producto, p.fecha_catalogo)
            for p in db.query(
                PrecioCatalogo.proveedor,
                PrecioCatalogo.id_producto,
                PrecioCatalogo.fecha_catalogo,
            ).all()
        }
        print(f"Filas ya existentes en precios_catalogo: {len(existentes)}")

        total_leidas = 0
        total_nuevas = 0
        nuevas_objetos = []

        for pestana, config in PESTANAS.items():
            print(f"\nLeyendo pestaña '{pestana}'...")
            filas = _leer_pestana(ruta_ods, pestana, config)
            total_leidas += len(filas)

            for fila in filas:
                clave = (fila["proveedor"], fila["id_producto"], fila["fecha_catalogo"])
                if clave in existentes:
                    continue
                existentes.add(clave)  # evita duplicados dentro del mismo archivo
                nuevas_objetos.append(PrecioCatalogo(**fila))
                total_nuevas += 1

            print(f"  {pestana}: {len(filas)} fila(s) leída(s).")

        if nuevas_objetos:
            db.bulk_save_objects(nuevas_objetos)
            db.commit()

        print(f"\nTotal leídas: {total_leidas}")
        print(f"Total nuevas insertadas: {total_nuevas}")
        print(f"Total omitidas (ya existían): {total_leidas - total_nuevas}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Importa tabla_precios.ods a precios_catalogo (solo INSERT).")
    parser.add_argument("ruta_ods", help="Ruta al archivo tabla_precios.ods")
    args = parser.parse_args()
    importar(args.ruta_ods)


if __name__ == "__main__":
    main()
