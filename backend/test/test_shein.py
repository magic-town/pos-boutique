"""
Tests del módulo Shein. Mapeado a docs/FULLSTACK/module_shein.md.

Cubre los 5 flujos (Registrar Cliente, Registrar Pedido, Lista de Pedidos,
Registrar Corte, Consulta de Cortes) más los 3 fixes de esta sesión:
INC-15 (agregar artículo a pedido existente), INC-16 (monto_pedido_vigente
en Lista de Pedidos) e INC-17 (autoconfirmar 'vigente' al crear el corte).
"""

import pytest


def _crear_shein_cliente(client, headers, **overrides):
    payload = {
        "nombre": "Cliente Shein Test",
        "colonia": "Centro",
        "telefono": 4441234567,
    }
    payload.update(overrides)
    resp = client.post("/api/v1/shein/clientes", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_shein_pedido(client, headers, id_shein_cliente, articulos=None, **overrides):
    payload = {
        "id_shein_cliente": id_shein_cliente,
        "articulos": articulos or [
            {"producto": "Blusa", "tipo_producto": "Importado", "monto": 300},
        ],
    }
    payload.update(overrides)
    resp = client.post("/api/v1/shein/pedidos", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _resolver_articulo(client, headers, id_shein_articulo, estatus_articulo, monto_vigente=None):
    payload = {"estatus_articulo": estatus_articulo}
    if monto_vigente is not None:
        payload["monto_vigente"] = monto_vigente
    return client.patch(
        f"/api/v1/shein/pedidos/articulos/{id_shein_articulo}",
        headers=headers,
        json=payload,
    )


class TestRegistrarClienteShein:
    def test_alta_basica(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers, nombre="Ana Torres")
        assert cliente["nombre"] == "Ana Torres"
        assert "id_shein_cliente" in cliente

    def test_nombre_vacio_rechazado(self, client, auth_headers):
        resp = client.post(
            "/api/v1/shein/clientes",
            headers=auth_headers,
            json={"nombre": "   ", "colonia": "Centro", "telefono": 4441234567},
        )
        assert resp.status_code == 422

    def test_telefono_9_digitos_rechazado(self, client, auth_headers):
        resp = client.post(
            "/api/v1/shein/clientes",
            headers=auth_headers,
            json={"nombre": "Prueba", "colonia": "Centro", "telefono": 123456789},
        )
        assert resp.status_code == 422

    def test_telefono_11_digitos_rechazado(self, client, auth_headers):
        resp = client.post(
            "/api/v1/shein/clientes",
            headers=auth_headers,
            json={"nombre": "Prueba", "colonia": "Centro", "telefono": 12345678901},
        )
        assert resp.status_code == 422

    def test_listar_clientes(self, client, auth_headers):
        _crear_shein_cliente(client, auth_headers, nombre="Zaira Listado")
        _crear_shein_cliente(client, auth_headers, nombre="Ana Listado")
        clientes = client.get("/api/v1/shein/clientes", headers=auth_headers).json()
        nombres = [c["nombre"] for c in clientes]
        assert nombres == sorted(nombres)


class TestRegistrarPedidoShein:
    def test_cliente_inexistente_404(self, client, auth_headers):
        resp = client.post(
            "/api/v1/shein/pedidos",
            headers=auth_headers,
            json={"id_shein_cliente": 999999, "articulos": [
                {"producto": "Blusa", "tipo_producto": "Importado", "monto": 100},
            ]},
        )
        assert resp.status_code == 404

    def test_pedido_sin_articulos_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        resp = client.post(
            "/api/v1/shein/pedidos",
            headers=auth_headers,
            json={"id_shein_cliente": cliente["id_shein_cliente"], "articulos": []},
        )
        assert resp.status_code == 422

    def test_pedido_con_4_articulos_aceptado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        articulos = [
            {"producto": f"Producto {i}", "tipo_producto": "Nacional", "monto": 100 * i}
            for i in range(1, 5)
        ]
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"], articulos)
        assert len(pedido["articulos"]) == 4

    def test_pedido_con_5_articulos_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        articulos = [
            {"producto": f"Producto {i}", "tipo_producto": "Nacional", "monto": 100}
            for i in range(1, 6)
        ]
        resp = client.post(
            "/api/v1/shein/pedidos",
            headers=auth_headers,
            json={"id_shein_cliente": cliente["id_shein_cliente"], "articulos": articulos},
        )
        assert resp.status_code == 422

    def test_articulo_nace_vigente_sin_monto_vigente(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        articulo = pedido["articulos"][0]
        assert articulo["estatus_articulo"] == "vigente"
        assert articulo["monto_vigente"] is None

    def test_monto_debe_ser_positivo(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        resp = client.post(
            "/api/v1/shein/pedidos",
            headers=auth_headers,
            json={"id_shein_cliente": cliente["id_shein_cliente"], "articulos": [
                {"producto": "Blusa", "tipo_producto": "Importado", "monto": 0},
            ]},
        )
        assert resp.status_code == 422

    def test_producto_vacio_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        resp = client.post(
            "/api/v1/shein/pedidos",
            headers=auth_headers,
            json={"id_shein_cliente": cliente["id_shein_cliente"], "articulos": [
                {"producto": "   ", "tipo_producto": "Importado", "monto": 100},
            ]},
        )
        assert resp.status_code == 422


class TestAgregarArticuloPedidoExistente:
    """INC-15: pedido editable mientras id_shein_corte IS NULL."""

    def test_agregar_articulo_sube_conteo_y_monto_vigente(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"],
            articulos=[{"producto": "Blusa", "tipo_producto": "Importado", "monto": 300}],
        )
        resp = client.post(
            f"/api/v1/shein/pedidos/{pedido['id_shein_pedido']}/articulos",
            headers=auth_headers,
            json={"producto": "Pantalón", "tipo_producto": "Nacional", "monto": 450},
        )
        assert resp.status_code == 201, resp.text
        actualizado = resp.json()
        assert len(actualizado["articulos"]) == 2
        assert actualizado["monto_pedido_vigente"] == 750  # 300 + 450, ambos vigente
        assert actualizado["monto_pedido"] == 0             # nada confirmado todavía

    def test_agregar_5to_articulo_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        articulos = [
            {"producto": f"Producto {i}", "tipo_producto": "Nacional", "monto": 100}
            for i in range(1, 5)
        ]
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"], articulos)
        resp = client.post(
            f"/api/v1/shein/pedidos/{pedido['id_shein_pedido']}/articulos",
            headers=auth_headers,
            json={"producto": "Extra", "tipo_producto": "Nacional", "monto": 100},
        )
        assert resp.status_code == 409

    def test_agregar_articulo_pedido_inexistente_404(self, client, auth_headers):
        resp = client.post(
            "/api/v1/shein/pedidos/999999/articulos",
            headers=auth_headers,
            json={"producto": "Blusa", "tipo_producto": "Importado", "monto": 100},
        )
        assert resp.status_code == 404

    def test_agregar_articulo_pedido_ya_en_corte_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        client.post(
            "/api/v1/shein/cortes",
            headers=auth_headers,
            json={
                "fecha_corte": "2026-07-05",
                "id_shein_pedidos": [pedido["id_shein_pedido"]],
                "total_ticket": 300,
            },
        )
        resp = client.post(
            f"/api/v1/shein/pedidos/{pedido['id_shein_pedido']}/articulos",
            headers=auth_headers,
            json={"producto": "Tardío", "tipo_producto": "Nacional", "monto": 100},
        )
        assert resp.status_code == 409


class TestListaDePedidos:
    def test_filtrar_por_cliente(self, client, auth_headers):
        cliente_a = _crear_shein_cliente(client, auth_headers, nombre="Cliente A Lista")
        cliente_b = _crear_shein_cliente(client, auth_headers, nombre="Cliente B Lista")
        _crear_shein_pedido(client, auth_headers, cliente_a["id_shein_cliente"])
        _crear_shein_pedido(client, auth_headers, cliente_b["id_shein_cliente"])

        pedidos = client.get(
            "/api/v1/shein/pedidos",
            headers=auth_headers,
            params={"id_shein_cliente": cliente_a["id_shein_cliente"]},
        ).json()
        assert all(p["id_shein_cliente"] == cliente_a["id_shein_cliente"] for p in pedidos)

    def test_monto_pedido_vigente_antes_de_corte(self, client, auth_headers):
        """INC-16: la Lista de Pedidos debe reflejar el monto capturado aunque
        nada esté 'confirmado' todavía (eso solo pasa en Corte)."""
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"],
            articulos=[{"producto": "Blusa", "tipo_producto": "Importado", "monto": 250}],
        )
        pedidos = client.get(
            "/api/v1/shein/pedidos",
            headers=auth_headers,
            params={"id_shein_cliente": cliente["id_shein_cliente"]},
        ).json()
        encontrado = next(p for p in pedidos if p["id_shein_pedido"] == pedido["id_shein_pedido"])
        assert encontrado["monto_pedido_vigente"] == 250
        assert encontrado["monto_pedido"] == 0

    def test_sin_corte_filtra_pendientes(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pendiente = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        en_corte = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        client.post(
            "/api/v1/shein/cortes",
            headers=auth_headers,
            json={
                "fecha_corte": "2026-07-05",
                "id_shein_pedidos": [en_corte["id_shein_pedido"]],
                "total_ticket": 300,
            },
        )
        pendientes = client.get(
            "/api/v1/shein/pedidos",
            headers=auth_headers,
            params={"id_shein_cliente": cliente["id_shein_cliente"], "sin_corte": True},
        ).json()
        ids = [p["id_shein_pedido"] for p in pendientes]
        assert pendiente["id_shein_pedido"] in ids
        assert en_corte["id_shein_pedido"] not in ids


class TestResolverArticulo:
    def test_articulo_inexistente_404(self, client, auth_headers):
        resp = _resolver_articulo(client, auth_headers, 999999, "confirmado")
        assert resp.status_code == 404

    def test_variacion_de_precio_conserva_monto_original(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"],
            articulos=[{"producto": "Blusa", "tipo_producto": "Importado", "monto": 300}],
        )
        articulo_id = pedido["articulos"][0]["id_shein_articulo"]
        resp = _resolver_articulo(client, auth_headers, articulo_id, "confirmado", monto_vigente=350)
        assert resp.status_code == 200, resp.text
        actualizado = resp.json()
        assert actualizado["monto"] == 300       # original, sin tocar
        assert actualizado["monto_vigente"] == 350

    def test_no_se_puede_resolver_articulo_de_pedido_ya_en_corte(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        articulo_id = pedido["articulos"][0]["id_shein_articulo"]
        client.post(
            "/api/v1/shein/cortes",
            headers=auth_headers,
            json={
                "fecha_corte": "2026-07-05",
                "id_shein_pedidos": [pedido["id_shein_pedido"]],
                "total_ticket": 300,
            },
        )
        resp = _resolver_articulo(client, auth_headers, articulo_id, "cancelado")
        assert resp.status_code == 409


class TestRegistrarCorte:
    def test_autoconfirma_vigente_sin_tocar(self, client, auth_headers):
        """INC-17: solo se resuelve a mano el artículo que cambió de precio;
        el otro se autoconfirma al crear el corte, sin intervención."""
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(
            client, auth_headers, cliente["id_shein_cliente"],
            articulos=[
                {"producto": "Blusa", "tipo_producto": "Importado", "monto": 300},
                {"producto": "Pantalón", "tipo_producto": "Nacional", "monto": 450},
            ],
        )
        art_1, art_2 = pedido["articulos"]
        # Solo se resuelve a mano el artículo 2 (cambió de precio); el 1 se deja 'vigente' a propósito.
        _resolver_articulo(client, auth_headers, art_2["id_shein_articulo"], "confirmado", monto_vigente=500)

        resp = client.post(
            "/api/v1/shein/cortes",
            headers=auth_headers,
            json={
                "fecha_corte": "2026-07-05",
                "id_shein_pedidos": [pedido["id_shein_pedido"]],
                "total_ticket": 750,
            },
        )
        assert resp.status_code == 201, resp.text
        corte = resp.json()
        assert corte["suma_pedidos"] == 800     # 300 (autoconfirmado) + 500 (resuelto a mano)
        assert corte["cupon"] == 50              # 800 - 750

        actualizado = client.get(
            "/api/v1/shein/pedidos", headers=auth_headers,
            params={"id_shein_cliente": cliente["id_shein_cliente"]},
        ).json()[0]
        assert all(a["estatus_articulo"] == "confirmado" for a in actualizado["articulos"])
        assert actualizado["id_shein_corte"] == corte["id_shein_corte"]
        assert actualizado["estatus_pago"] == "pago_pendiente"

    def test_pedido_todos_cancelados_queda_fuera_sin_castigo(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        cancelado = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        confirmado = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        _resolver_articulo(client, auth_headers, cancelado["articulos"][0]["id_shein_articulo"], "cancelado")
        _resolver_articulo(client, auth_headers, confirmado["articulos"][0]["id_shein_articulo"], "confirmado")

        resp = client.post(
            "/api/v1/shein/cortes",
            headers=auth_headers,
            json={
                "fecha_corte": "2026-07-05",
                "id_shein_pedidos": [cancelado["id_shein_pedido"], confirmado["id_shein_pedido"]],
                "total_ticket": 300,
            },
        )
        assert resp.status_code == 201, resp.text

        pedidos = client.get(
            "/api/v1/shein/pedidos", headers=auth_headers,
            params={"id_shein_cliente": cliente["id_shein_cliente"]},
        ).json()
        p_cancelado = next(p for p in pedidos if p["id_shein_pedido"] == cancelado["id_shein_pedido"])
        p_confirmado = next(p for p in pedidos if p["id_shein_pedido"] == confirmado["id_shein_pedido"])
        assert p_cancelado["id_shein_corte"] is None
        assert p_cancelado["estatus_pago"] is None
        assert p_confirmado["id_shein_corte"] is not None

    def test_pedido_no_encontrado_404(self, client, auth_headers):
        resp = client.post(
            "/api/v1/shein/cortes",
            headers=auth_headers,
            json={"fecha_corte": "2026-07-05", "id_shein_pedidos": [999999], "total_ticket": 100},
        )
        assert resp.status_code == 404

    def test_pedido_ya_en_corte_previo_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        client.post(
            "/api/v1/shein/cortes", headers=auth_headers,
            json={"fecha_corte": "2026-07-05", "id_shein_pedidos": [pedido["id_shein_pedido"]], "total_ticket": 300},
        )
        resp = client.post(
            "/api/v1/shein/cortes", headers=auth_headers,
            json={"fecha_corte": "2026-07-06", "id_shein_pedidos": [pedido["id_shein_pedido"]], "total_ticket": 300},
        )
        assert resp.status_code == 409

    def test_total_ticket_no_positivo_rechazado(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        resp = client.post(
            "/api/v1/shein/cortes", headers=auth_headers,
            json={"fecha_corte": "2026-07-05", "id_shein_pedidos": [pedido["id_shein_pedido"]], "total_ticket": 0},
        )
        assert resp.status_code == 422


class TestConsultaDeCortes:
    def test_listar_y_detalle(self, client, auth_headers):
        cliente = _crear_shein_cliente(client, auth_headers)
        pedido = _crear_shein_pedido(client, auth_headers, cliente["id_shein_cliente"])
        creado = client.post(
            "/api/v1/shein/cortes", headers=auth_headers,
            json={"fecha_corte": "2026-07-05", "id_shein_pedidos": [pedido["id_shein_pedido"]], "total_ticket": 250},
        ).json()

        cortes = client.get("/api/v1/shein/cortes", headers=auth_headers).json()
        assert any(c["id_shein_corte"] == creado["id_shein_corte"] for c in cortes)

        detalle = client.get(f"/api/v1/shein/cortes/{creado['id_shein_corte']}", headers=auth_headers).json()
        assert detalle["suma_pedidos"] == 300
        assert detalle["cupon"] == 50

    def test_corte_inexistente_404(self, client, auth_headers):
        resp = client.get("/api/v1/shein/cortes/999999", headers=auth_headers)
        assert resp.status_code == 404


def test_escenario_shein_ciclo_completo(client, auth_headers):
    """Reproduce el ciclo completo verificado manualmente con curl: crear
    pedido, agregarle un artículo, variar precio de uno solo, dejar el otro
    sin tocar, cortar, y confirmar que todo termina resuelto correctamente."""
    cliente = _crear_shein_cliente(client, auth_headers, nombre="Escenario Completo")

    pedido = _crear_shein_pedido(
        client, auth_headers, cliente["id_shein_cliente"],
        articulos=[{"producto": "Blusa", "tipo_producto": "Importado", "monto": 300}],
    )
    ampliado = client.post(
        f"/api/v1/shein/pedidos/{pedido['id_shein_pedido']}/articulos",
        headers=auth_headers,
        json={"producto": "Pantalón", "tipo_producto": "Nacional", "monto": 450},
    ).json()
    assert ampliado["monto_pedido_vigente"] == 750

    art_1, art_2 = ampliado["articulos"]
    _resolver_articulo(client, auth_headers, art_2["id_shein_articulo"], "confirmado", monto_vigente=500)

    corte = client.post(
        "/api/v1/shein/cortes", headers=auth_headers,
        json={
            "fecha_corte": "2026-07-05",
            "id_shein_pedidos": [pedido["id_shein_pedido"]],
            "total_ticket": 750,
        },
    ).json()
    assert corte["suma_pedidos"] == 800
    assert corte["cupon"] == 50

    final = client.get(
        "/api/v1/shein/pedidos", headers=auth_headers,
        params={"id_shein_cliente": cliente["id_shein_cliente"]},
    ).json()[0]
    assert final["monto_pedido"] == 800
    assert final["monto_pedido_vigente"] == 0
    assert all(a["estatus_articulo"] == "confirmado" for a in final["articulos"])
