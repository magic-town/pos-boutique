"""
test/test_recargas.py

Mapeado 1:1 a module_recargas.md. Cubre:
  - creación de recarga (POST /recargas) — casos válidos y de validación
  - autenticación requerida en ambos endpoints
  - resumen del día (GET /recargas/resumen-dia) agrupado por compañía

Nota sobre el resumen del día: la tabla `recargas` no se limpia entre
corridas (ver conftest.py — no se conserva data real, pero eso aplica al
reset de pos.db entre sesiones de trabajo, no a cada test). Por eso
TestResumenDia mide un DELTA: toma el resumen antes de crear sus propias
recargas y compara contra el resumen después, en lugar de asumir totales
absolutos que chocarían con datos de otros tests corridos el mismo día.
"""

import pytest

from app.models.models import Recarga


# ──────────────────────────────────────────────────────────────────────────
# POST /recargas
# ──────────────────────────────────────────────────────────────────────────

class TestCrearRecarga:

    @pytest.mark.parametrize("compania", ["Telcel", "Movistar", "Unefon", "AT&T"])
    def test_crear_recarga_valida(self, client, auth_headers, compania):
        payload = {"compania": compania, "monto": 100.0}
        resp = client.post("/api/v1/recargas", json=payload, headers=auth_headers)

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["compania"] == compania
        assert body["monto"] == 100.0
        assert body["id_recarga"] is not None
        assert body["fecha"] is not None  # autogenerada por el backend

    def test_monto_cero_rechazado(self, client, auth_headers):
        payload = {"compania": "Telcel", "monto": 0}
        resp = client.post("/api/v1/recargas", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_monto_negativo_rechazado(self, client, auth_headers):
        payload = {"compania": "Telcel", "monto": -50}
        resp = client.post("/api/v1/recargas", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_compania_invalida_rechazada(self, client, auth_headers):
        payload = {"compania": "Unifon", "monto": 100.0}  # typo, no es del enum
        resp = client.post("/api/v1/recargas", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_compania_faltante_rechazada(self, client, auth_headers):
        payload = {"monto": 100.0}
        resp = client.post("/api/v1/recargas", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_monto_faltante_rechazado(self, client, auth_headers):
        payload = {"compania": "Telcel"}
        resp = client.post("/api/v1/recargas", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_sin_tope_de_monto(self, client, auth_headers):
        """module_recargas.md: sin validación de tope — la operadora captura
        el monto real."""
        payload = {"compania": "Telcel", "monto": 999999.99}
        resp = client.post("/api/v1/recargas", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text

    def test_no_requiere_cliente_ni_producto(self, client, auth_headers):
        """Tabla independiente, sin FK externas (module_recargas.md)."""
        payload = {"compania": "Movistar", "monto": 200.0}
        resp = client.post("/api/v1/recargas", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        assert "id_cliente" not in resp.json()

    def test_sin_auth_rechazado(self, client):
        payload = {"compania": "Telcel", "monto": 100.0}
        resp = client.post("/api/v1/recargas", json=payload)
        assert resp.status_code == 401

    def test_persistencia_en_bd(self, client, auth_headers, db_session):
        payload = {"compania": "AT&T", "monto": 150.0}
        resp = client.post("/api/v1/recargas", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        id_recarga = resp.json()["id_recarga"]

        recarga = db_session.query(Recarga).get(id_recarga)
        assert recarga is not None
        assert recarga.compania.value == "AT&T"
        assert recarga.monto == 150.0
        assert recarga.fecha is not None


# ──────────────────────────────────────────────────────────────────────────
# GET /recargas/resumen-dia
# ──────────────────────────────────────────────────────────────────────────

class TestResumenDia:

    def _totales_por_compania(self, resumen: list[dict]) -> dict:
        return {fila["compania"]: fila for fila in resumen}

    def test_sin_auth_rechazado(self, client):
        resp = client.get("/api/v1/recargas/resumen-dia")
        assert resp.status_code == 401

    def test_refleja_recargas_creadas_hoy(self, client, auth_headers):
        # Resumen antes de crear -- baseline para medir el delta.
        antes = self._totales_por_compania(
            client.get("/api/v1/recargas/resumen-dia", headers=auth_headers).json()
        )
        qty_antes = antes.get("Telcel", {}).get("qty", 0)
        total_antes = antes.get("Telcel", {}).get("total", 0.0)

        client.post("/api/v1/recargas", json={"compania": "Telcel", "monto": 50.0}, headers=auth_headers)
        client.post("/api/v1/recargas", json={"compania": "Telcel", "monto": 30.0}, headers=auth_headers)

        despues = self._totales_por_compania(
            client.get("/api/v1/recargas/resumen-dia", headers=auth_headers).json()
        )

        assert despues["Telcel"]["qty"] == qty_antes + 2
        assert despues["Telcel"]["total"] == pytest.approx(total_antes + 80.0)

    def test_agrupa_por_compania_de_forma_independiente(self, client, auth_headers):
        antes = self._totales_por_compania(
            client.get("/api/v1/recargas/resumen-dia", headers=auth_headers).json()
        )
        qty_movistar_antes = antes.get("Movistar", {}).get("qty", 0)
        qty_unefon_antes = antes.get("Unefon", {}).get("qty", 0)

        client.post("/api/v1/recargas", json={"compania": "Movistar", "monto": 75.0}, headers=auth_headers)
        client.post("/api/v1/recargas", json={"compania": "Unefon", "monto": 60.0}, headers=auth_headers)

        despues = self._totales_por_compania(
            client.get("/api/v1/recargas/resumen-dia", headers=auth_headers).json()
        )

        # Cada compañía sube solo su propio contador -- no se mezclan.
        assert despues["Movistar"]["qty"] == qty_movistar_antes + 1
        assert despues["Unefon"]["qty"] == qty_unefon_antes + 1

    def test_recarga_recien_creada_aparece_en_el_resumen(self, client, auth_headers):
        resp = client.post("/api/v1/recargas", json={"compania": "AT&T", "monto": 500.0}, headers=auth_headers)
        assert resp.status_code == 201, resp.text

        resumen = self._totales_por_compania(
            client.get("/api/v1/recargas/resumen-dia", headers=auth_headers).json()
        )
        assert "AT&T" in resumen
        assert resumen["AT&T"]["qty"] >= 1
