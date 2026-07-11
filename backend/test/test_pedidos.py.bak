"""
Tests del módulo Pedidos. Mapeado a docs/FULLSTACK/module_pedidos.md.

Todo lo aquí probado ya se validó manualmente con curl en sesión de
desarrollo (ver REPORT.md §5 paso 1) -- esta suite lo automatiza para que
correrlo no dependa de descifrar tokens a mano cada vez.
"""

import pytest


def _saldo(db_session_factory, no_cliente):
    from app.db.database import SessionLocal
    from app.models.models import Cliente
    db = SessionLocal()
    try:
        return db.query(Cliente).filter(Cliente.no_cliente == no_cliente).first().saldo
    finally:
        db.close()


def _crear_pedido_informal(client, headers, no_cliente, producto, monto):
    resp = client.post(
        "/api/v1/pedidos",
        headers=headers,
        json={
            "no_cliente": no_cliente,
            "articulos": [{
                "principal": {
                    "tipo_producto": "informal",
                    "producto": producto,
                    "marca": "N/A",
                    "talla": "M",
                    "monto": monto,
                }
            }],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["articulos"][0]["id_articulo"]


# ──────────────────────────────────────────────────────────────────────────
# Registrar Pedido
# ──────────────────────────────────────────────────────────────────────────

class TestRegistrarPedido:
    def test_formal_con_catalogo_autollena_monto(self, client, auth_headers, cliente_prueba):
        """id_producto real de Price_Shoes -- ajusta si tu import de precios
        no tiene este código (ver §2 REPORT.md para conteos por proveedor)."""
        from app.db.database import SessionLocal
        from app.models.models import PrecioCatalogo, ProveedorCatalogo

        db = SessionLocal()
        precio = db.query(PrecioCatalogo).filter(
            PrecioCatalogo.proveedor == ProveedorCatalogo.Price_Shoes
        ).order_by(PrecioCatalogo.fecha_catalogo.desc()).first()
        db.close()
        if precio is None:
            pytest.skip("No hay precios_catalogo importado -- correr importar_precios.py primero.")

        resp = client.post(
            "/api/v1/pedidos",
            headers=auth_headers,
            json={
                "no_cliente": cliente_prueba.no_cliente,
                "articulos": [{
                    "principal": {
                        "tipo_producto": "formal",
                        "proveedor": "Price_Shoes",
                        "id_producto": precio.id_producto,
                        "producto": "Zapato test",
                        "marca": "N/A",
                        "talla": "24",
                        "monto": 1,  # se ignora: el catálogo manda
                    }
                }],
            },
        )
        assert resp.status_code == 201, resp.text
        articulo = resp.json()["articulos"][0]
        assert articulo["monto"] == precio.precio_venta
        assert articulo["estatus_articulo"] == "vigente"

    def test_informal_respeta_monto_libre(self, client, auth_headers, cliente_prueba):
        resp = client.post(
            "/api/v1/pedidos",
            headers=auth_headers,
            json={
                "no_cliente": cliente_prueba.no_cliente,
                "articulos": [{
                    "principal": {
                        "tipo_producto": "informal",
                        "producto": "Blusa test",
                        "marca": "N/A",
                        "talla": "M",
                        "monto": 350,
                    }
                }],
            },
        )
        assert resp.status_code == 201, resp.text
        articulo = resp.json()["articulos"][0]
        assert articulo["proveedor"] is None
        assert articulo["monto"] == 350.0

    def test_cliente_inexistente_devuelve_404(self, client, auth_headers):
        resp = client.post(
            "/api/v1/pedidos",
            headers=auth_headers,
            json={
                "no_cliente": "NO-EXISTE-999",
                "articulos": [{
                    "principal": {
                        "tipo_producto": "informal",
                        "producto": "Blusa test",
                        "monto": 100,
                    }
                }],
            },
        )
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# Límite de alternativas (REGLAS_NEGOCIO.md §3 regla 2)
# ──────────────────────────────────────────────────────────────────────────

class TestLimiteAlternativas:
    def test_price_shoes_acepta_3_alternativas(self, client, auth_headers, cliente_prueba):
        resp = client.post(
            "/api/v1/pedidos",
            headers=auth_headers,
            json={
                "no_cliente": cliente_prueba.no_cliente,
                "articulos": [{
                    "principal": {
                        "tipo_producto": "formal", "proveedor": "Price_Shoes",
                        "id_producto": "AAA", "producto": "Principal", "monto": 100,
                    },
                    "alternativas": [
                        {"tipo_producto": "formal", "proveedor": "Price_Shoes", "id_producto": "BBB", "producto": "Alt1", "monto": 100},
                        {"tipo_producto": "formal", "proveedor": "Price_Shoes", "id_producto": "CCC", "producto": "Alt2", "monto": 100},
                        {"tipo_producto": "formal", "proveedor": "Price_Shoes", "id_producto": "DDD", "producto": "Alt3", "monto": 100},
                    ],
                }],
            },
        )
        assert resp.status_code == 201, resp.text
        assert len(resp.json()["articulos"]) == 4  # 1 principal + 3 alternativas

    def test_price_shoes_rechaza_4_alternativas(self, client, auth_headers, cliente_prueba):
        resp = client.post(
            "/api/v1/pedidos",
            headers=auth_headers,
            json={
                "no_cliente": cliente_prueba.no_cliente,
                "articulos": [{
                    "principal": {
                        "tipo_producto": "formal", "proveedor": "Price_Shoes",
                        "id_producto": "AAA", "producto": "Principal", "monto": 100,
                    },
                    "alternativas": [
                        {"tipo_producto": "formal", "proveedor": "Price_Shoes", "id_producto": str(i), "producto": f"Alt{i}", "monto": 100}
                        for i in range(4)
                    ],
                }],
            },
        )
        assert resp.status_code == 422

    def test_otro_proveedor_rechaza_2_alternativas(self, client, auth_headers, cliente_prueba):
        resp = client.post(
            "/api/v1/pedidos",
            headers=auth_headers,
            json={
                "no_cliente": cliente_prueba.no_cliente,
                "articulos": [{
                    "principal": {
                        "tipo_producto": "formal", "proveedor": "Pakar",
                        "id_producto": "AAA", "producto": "Principal", "monto": 100,
                    },
                    "alternativas": [
                        {"tipo_producto": "formal", "proveedor": "Pakar", "id_producto": "BBB", "producto": "Alt1", "monto": 100},
                        {"tipo_producto": "formal", "proveedor": "Pakar", "id_producto": "CCC", "producto": "Alt2", "monto": 100},
                    ],
                }],
            },
        )
        assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────
# Lista de Surtido / Devolución / Cancelación
# ──────────────────────────────────────────────────────────────────────────

class TestSurtidoDevolucionCancelacion:
    def test_surtir_sube_saldo(self, client, auth_headers, cliente_prueba):
        id_articulo = _crear_pedido_informal(client, auth_headers, cliente_prueba.no_cliente, "Producto surtir", 200)
        
        from app.db.database import SessionLocal
        from app.models.models import Cliente
        db = SessionLocal()
        saldo_antes = db.query(Cliente).filter(Cliente.no_cliente == cliente_prueba.no_cliente).first().saldo
        db.close()
        assert saldo_antes == 0.0  # no debe subir al solo registrar el pedido, solo al surtir

        resp = client.patch(f"/api/v1/pedidos/lista-surtido/{id_articulo}/surtir", headers=auth_headers)
        assert resp.status_code == 200, resp.text

        from app.db.database import SessionLocal
        from app.models.models import Cliente
        db = SessionLocal()
        cliente = db.query(Cliente).filter(Cliente.no_cliente == cliente_prueba.no_cliente).first()
        saldo, estatus = cliente.saldo, cliente.estatus
        db.close()
        assert saldo == 200.0
        assert estatus.value == "activo"  # surtir activa al cliente en automático

    def test_devolucion_revierte_saldo(self, client, auth_headers, cliente_prueba):
        id_articulo = _crear_pedido_informal(client, auth_headers, cliente_prueba.no_cliente, "Producto devolver", 150)
        client.patch(f"/api/v1/pedidos/lista-surtido/{id_articulo}/surtir", headers=auth_headers)

        resp = client.post(
            "/api/v1/pedidos/devolucion",
            headers=auth_headers,
            json={"no_cliente": cliente_prueba.no_cliente, "id_articulo": id_articulo},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["id_articulo_sustituye"] == id_articulo

        from app.db.database import SessionLocal
        from app.models.models import Cliente
        db = SessionLocal()
        cliente = db.query(Cliente).filter(Cliente.no_cliente == cliente_prueba.no_cliente).first()
        saldo, estatus = cliente.saldo, cliente.estatus
        db.close()
        assert saldo == 0.0
        assert estatus.value == "inactivo"  # liquidó por devolución -- regresa a inactivo

    def test_cancelar_vigente_no_afecta_saldo(self, client, auth_headers, cliente_prueba):
        id_articulo = _crear_pedido_informal(client, auth_headers, cliente_prueba.no_cliente, "Producto cancelar vigente", 300)

        resp = client.post(
            "/api/v1/pedidos/cancelacion",
            headers=auth_headers,
            json={"no_cliente": cliente_prueba.no_cliente, "id_articulo": id_articulo},
        )
        assert resp.status_code == 200, resp.text

        from app.db.database import SessionLocal
        from app.models.models import Cliente
        db = SessionLocal()
        cliente = db.query(Cliente).filter(Cliente.no_cliente == cliente_prueba.no_cliente).first()
        saldo, estatus = cliente.saldo, cliente.estatus
        db.close()
        assert saldo == 0.0
        assert estatus.value == "inactivo"  # nunca llegó a impactar saldo -- sigue/ya está inactivo

    def test_cancelar_en_almacen_revierte_saldo(self, client, auth_headers, cliente_prueba):
        id_articulo = _crear_pedido_informal(client, auth_headers, cliente_prueba.no_cliente, "Producto cancelar surtido", 400)
        client.patch(f"/api/v1/pedidos/lista-surtido/{id_articulo}/surtir", headers=auth_headers)

        resp = client.post(
            "/api/v1/pedidos/cancelacion",
            headers=auth_headers,
            json={"no_cliente": cliente_prueba.no_cliente, "id_articulo": id_articulo},
        )
        assert resp.status_code == 200, resp.text

        from app.db.database import SessionLocal
        from app.models.models import Cliente
        db = SessionLocal()
        cliente = db.query(Cliente).filter(Cliente.no_cliente == cliente_prueba.no_cliente).first()
        saldo, estatus = cliente.saldo, cliente.estatus
        db.close()
        assert saldo == 0.0
        assert estatus.value == "inactivo"  # cancelar un en_almacen revierte el saldo a 0 -- desactiva


# ──────────────────────────────────────────────────────────────────────────
# Escenario realista: 3 artículos, 1 aceptado, 1 devuelto, 1 cancelado
# ──────────────────────────────────────────────────────────────────────────

def test_escenario_pedido_de_tres_articulos_mixto(client, auth_headers, cliente_prueba):
    """Reproduce el caso pedido por el usuario: un cliente encarga 3
    artículos en el mismo pedido. Antes de que lleguen, cancela uno. De los
    otros dos que sí llegan (en_almacen), se queda con uno (aceptado -- fin
    del flujo) y devuelve el otro. Verifica saldo en cada punto del camino,
    no solo el estado final."""
    no_cliente = cliente_prueba.no_cliente

    resp = client.post(
        "/api/v1/pedidos",
        headers=auth_headers,
        json={
            "no_cliente": no_cliente,
            "articulos": [
                {"principal": {"tipo_producto": "informal", "producto": "Blusa A (se acepta)", "monto": 300}},
                {"principal": {"tipo_producto": "informal", "producto": "Blusa B (se devuelve)", "monto": 250}},
                {"principal": {"tipo_producto": "informal", "producto": "Blusa C (se cancela)", "monto": 180}},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    articulos = resp.json()["articulos"]
    assert len(articulos) == 3
    id_a, id_b, id_c = (a["id_articulo"] for a in articulos)

    def saldo_actual():
        from app.db.database import SessionLocal
        from app.models.models import Cliente
        db = SessionLocal()
        try:
            return db.query(Cliente).filter(Cliente.no_cliente == no_cliente).first().saldo
        finally:
            db.close()

    assert saldo_actual() == 0.0  # nada ha llegado todavía

    # El cliente cambia de opinión sobre C antes de que llegue.
    resp = client.post(
        "/api/v1/pedidos/cancelacion",
        headers=auth_headers,
        json={"no_cliente": no_cliente, "id_articulo": id_c},
    )
    assert resp.status_code == 200, resp.text
    assert saldo_actual() == 0.0  # cancelar un vigente no debe tocar saldo

    # Llegan A y B a la tienda (surtido).
    for id_articulo in (id_a, id_b):
        resp = client.patch(f"/api/v1/pedidos/lista-surtido/{id_articulo}/surtir", headers=auth_headers)
        assert resp.status_code == 200, resp.text

    assert saldo_actual() == 550.0  # 300 (A) + 250 (B)

    def estatus_actual():
        from app.db.database import SessionLocal
        from app.models.models import Cliente
        db = SessionLocal()
        try:
            return db.query(Cliente).filter(Cliente.no_cliente == no_cliente).first().estatus
        finally:
            db.close()

    assert estatus_actual().value == "activo"  # ya llegó producto -- se activó en automático

    # El cliente acepta A (no se hace nada más -- en_almacen es estado final
    # para un artículo aceptado) y devuelve B.
    resp = client.post(
        "/api/v1/pedidos/devolucion",
        headers=auth_headers,
        json={"no_cliente": no_cliente, "id_articulo": id_b},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["id_articulo_sustituye"] == id_b

    assert saldo_actual() == 300.0  # solo queda A, aceptado
    assert estatus_actual().value == "activo"  # sigue con saldo pendiente -- sigue activo

    # Estados finales esperados: A en_almacen, B devuelto, C cancelado.
    from app.db.database import SessionLocal
    from app.models.models import PedidoArticulo
    db = SessionLocal()
    try:
        estatus = {
            a.id_articulo: a.estatus_articulo.value
            for a in db.query(PedidoArticulo).filter(PedidoArticulo.id_articulo.in_([id_a, id_b, id_c]))
        }
    finally:
        db.close()
    assert estatus[id_a] == "en_almacen"
    assert estatus[id_b] == "devuelto"
    assert estatus[id_c] == "cancelado"
