"""
Tests del módulo Inventario. Mapeado a docs/FULLSTACK/module_inventario.md.
"""

import pytest


def _crear_producto(client, headers, **overrides):
    payload = {
        "categoria": "dama",
        "tipo_producto": "informal",
        "descripcion": "Producto test",
        "marca": "Aspik",
        "precio_venta": 500,
        "stock": 10,
    }
    payload.update(overrides)
    resp = client.post("/api/v1/inventario", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestAgregarProducto:
    def test_alta_basica(self, client, auth_headers):
        producto = _crear_producto(client, auth_headers, descripcion="Blusa dama")
        assert producto["estatus"] == "disponible"
        assert producto["precio_descuento"] is None


class TestCambiarEstatus:
    def test_transicion_a_en_ruta_requiere_descripcion(self, client, auth_headers):
        producto = _crear_producto(client, auth_headers)
        resp = client.patch(
            f"/api/v1/inventario/{producto['id_producto']}/estatus",
            headers=auth_headers,
            json={"nuevo_estatus": "en_ruta"},
        )
        assert resp.status_code == 422  # falta descripcion_ruta

        resp = client.patch(
            f"/api/v1/inventario/{producto['id_producto']}/estatus",
            headers=auth_headers,
            json={"nuevo_estatus": "en_ruta", "descripcion_ruta": "Exhibición en feria"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["descripcion_ruta"] == "Exhibición en feria"

    def test_transicion_invalida_rechazada(self, client, auth_headers):
        producto = _crear_producto(client, auth_headers)
        # vendido -> disponible no está en las transiciones válidas
        client.patch(f"/api/v1/inventario/{producto['id_producto']}/estatus", headers=auth_headers, json={"nuevo_estatus": "vendido"})
        resp = client.patch(
            f"/api/v1/inventario/{producto['id_producto']}/estatus",
            headers=auth_headers,
            json={"nuevo_estatus": "disponible"},
        )
        assert resp.status_code == 400

    def test_precio_descuento_debe_ser_menor_a_precio_venta(self, client, auth_headers):
        producto = _crear_producto(client, auth_headers, precio_venta=500)
        resp = client.patch(
            f"/api/v1/inventario/{producto['id_producto']}/estatus",
            headers=auth_headers,
            json={"nuevo_estatus": "disponible_c/descuento", "precio_descuento": 600},
        )
        assert resp.status_code == 400


class TestDescuentoMasivo:
    def test_aplicar_por_marca_y_retirar(self, client, auth_headers):
        marca = "MarcaTestUnica"
        p1 = _crear_producto(client, auth_headers, marca=marca, precio_venta=1000)
        p2 = _crear_producto(client, auth_headers, marca=marca, precio_venta=2000)
        _crear_producto(client, auth_headers, marca="OtraMarca", precio_venta=500)  # no debe afectarse

        resp = client.post(
            "/api/v1/inventario/descuento-masivo",
            headers=auth_headers,
            json={"segmento": {"marca": marca}, "pct": 20},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["productos_afectados"] == 2

        consulta = client.get("/api/v1/inventario", headers=auth_headers, params={"marca": marca}).json()
        precios = {p["id_producto"]: p["precio_descuento"] for p in consulta}
        assert precios[p1["id_producto"]] == 800    # 1000 * 0.8
        assert precios[p2["id_producto"]] == 1600   # 2000 * 0.8

        resp = client.post(
            "/api/v1/inventario/descuento-masivo/retirar",
            headers=auth_headers,
            json={"segmento": {"marca": marca}},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["productos_afectados"] == 2

    def test_precio_fijo_mayor_a_venta_se_omite(self, client, auth_headers):
        marca = "MarcaPrecioFijoTest"
        barato = _crear_producto(client, auth_headers, marca=marca, precio_venta=50)
        caro = _crear_producto(client, auth_headers, marca=marca, precio_venta=500)

        resp = client.post(
            "/api/v1/inventario/descuento-masivo",
            headers=auth_headers,
            json={"segmento": {"marca": marca}, "precio_fijo": 99},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["productos_afectados"] == 1  # solo "caro"
        assert barato["id_producto"] in data["productos_omitidos"]

    def test_segmento_vacio_rechazado(self, client, auth_headers):
        resp = client.post(
            "/api/v1/inventario/descuento-masivo",
            headers=auth_headers,
            json={"segmento": {}, "pct": 10},
        )
        assert resp.status_code == 422

    def test_no_afecta_productos_vendidos(self, client, auth_headers):
        marca = "MarcaVendidoTest"
        producto = _crear_producto(client, auth_headers, marca=marca, precio_venta=500)
        client.patch(f"/api/v1/inventario/{producto['id_producto']}/estatus", headers=auth_headers, json={"nuevo_estatus": "vendido"})

        resp = client.post(
            "/api/v1/inventario/descuento-masivo",
            headers=auth_headers,
            json={"segmento": {"marca": marca}, "pct": 50},
        )
        assert resp.status_code == 200
        assert resp.json()["productos_afectados"] == 0  # 'vendido' no es 'disponible', se ignora
