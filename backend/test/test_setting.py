"""
Tests del módulo Setting/Configuración.

Mapeado 1:1 a docs/FULL_STACK/module_setting.md y a
app/api/v1/endpoints/setting.py. Usa las fixtures compartidas de
conftest.py (client, auth_headers, db_session) -- no duplica fixtures de
cliente/auth aquí (ver convención en conftest.py).

Cobertura:
- Usuarios: agregar, cambiar password, cambiar rol.
- Información del sistema: zona horaria (solo lectura).
- Configuración: listar, actualizar clave, reglas de métodos de pago
  (valor '0'/'1', efectivo no desactivable).
- Autorización: todos los endpoints requieren token.

No se prueba lógica de permisos diferenciada estandar/admin porque el
spec la marca explícitamente como "sin lógica de permisos diferenciada
en MVP" -- ver REPORT.md §3, fila de Setting.
"""

import uuid

import pytest

from app.db.database import SessionLocal
from app.models.models import Usuario, Configuracion

BASE = "/api/v1/setting"


def _usuario_payload(rol="estandar"):
    sufijo = uuid.uuid4().hex[:8]
    return {
        "usuario": f"test{sufijo}",
        "password": "Clave123",
        "rol": rol,
    }


# ──────────────────────────────────────────────────────────────────────────
# Usuarios
# ──────────────────────────────────────────────────────────────────────────

class TestAgregarUsuario:
    def test_agregar_usuario_ok(self, client, auth_headers):
        payload = _usuario_payload()
        resp = client.post(f"{BASE}/usuarios", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["usuario"] == payload["usuario"]
        assert "password" not in data
        assert "password_hash" not in data

    def test_agregar_usuario_duplicado_409(self, client, auth_headers):
        payload = _usuario_payload()
        resp1 = client.post(f"{BASE}/usuarios", json=payload, headers=auth_headers)
        assert resp1.status_code == 201, resp1.text

        resp2 = client.post(f"{BASE}/usuarios", json=payload, headers=auth_headers)
        assert resp2.status_code == 409

    @pytest.mark.parametrize(
        "password",
        [
            "abc",          # menos de 4 caracteres
            "a" * 11,       # más de 10 caracteres
            "clave123",     # sin mayúscula
            "",             # vacío
        ],
    )
    def test_agregar_usuario_password_invalido_422(self, client, auth_headers, password):
        payload = _usuario_payload()
        payload["password"] = password
        resp = client.post(f"{BASE}/usuarios", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_agregar_usuario_rol_invalido_422(self, client, auth_headers):
        payload = _usuario_payload()
        payload["rol"] = "superadmin"
        resp = client.post(f"{BASE}/usuarios", json=payload, headers=auth_headers)
        assert resp.status_code == 422


class TestCambiarPassword:
    def test_cambiar_password_ok_y_permite_login(self, client, auth_headers):
        payload = _usuario_payload()
        creado = client.post(f"{BASE}/usuarios", json=payload, headers=auth_headers).json()

        nueva = "Nueva123"
        resp = client.patch(
            f"{BASE}/usuarios/{creado['id_usuario']}/password",
            json={"password": nueva},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text

        login_nueva = client.post(
            "/api/v1/auth/login",
            data={"username": payload["usuario"], "password": nueva},
        )
        assert login_nueva.status_code == 200

        login_vieja = client.post(
            "/api/v1/auth/login",
            data={"username": payload["usuario"], "password": payload["password"]},
        )
        assert login_vieja.status_code == 401

    def test_cambiar_password_usuario_inexistente_404(self, client, auth_headers):
        resp = client.patch(
            f"{BASE}/usuarios/999999/password",
            json={"password": "Nueva123"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_cambiar_password_invalido_422(self, client, auth_headers):
        payload = _usuario_payload()
        creado = client.post(f"{BASE}/usuarios", json=payload, headers=auth_headers).json()
        resp = client.patch(
            f"{BASE}/usuarios/{creado['id_usuario']}/password",
            json={"password": "sinmayuscula"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestCambiarRol:
    def test_cambiar_rol_ok(self, client, auth_headers, db_session):
        payload = _usuario_payload(rol="estandar")
        creado = client.post(f"{BASE}/usuarios", json=payload, headers=auth_headers).json()

        resp = client.patch(
            f"{BASE}/usuarios/{creado['id_usuario']}/rol",
            json={"rol": "admin"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text

        # Verificado directo en BD (no depende de qué exponga UsuarioRead).
        db_session.expire_all()
        usuario_db = db_session.get(Usuario, creado["id_usuario"])
        assert usuario_db.rol == "admin"

    def test_cambiar_rol_invalido_422(self, client, auth_headers):
        payload = _usuario_payload()
        creado = client.post(f"{BASE}/usuarios", json=payload, headers=auth_headers).json()
        resp = client.patch(
            f"{BASE}/usuarios/{creado['id_usuario']}/rol",
            json={"rol": "superadmin"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_cambiar_rol_usuario_inexistente_404(self, client, auth_headers):
        resp = client.patch(
            f"{BASE}/usuarios/999999/rol",
            json={"rol": "admin"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# Información del sistema
# ──────────────────────────────────────────────────────────────────────────

class TestZonaHoraria:
    def test_zona_horaria_lectura(self, client, auth_headers):
        resp = client.get(f"{BASE}/zona-horaria", headers=auth_headers)
        assert resp.status_code == 200
        # Seed esperado por module_setting.md; si se reconfiguró a mano,
        # este assert es la señal de que cambió el valor sembrado.
        assert resp.json()["zona_horaria"] == "America/Mexico_City"


# ──────────────────────────────────────────────────────────────────────────
# Configuración (métodos de pago, CLABEs, etc.)
# ──────────────────────────────────────────────────────────────────────────

class TestConfiguracion:
    def test_listar_configuracion(self, client, auth_headers):
        resp = client.get(f"{BASE}/configuracion", headers=auth_headers)
        assert resp.status_code == 200
        claves = {c["clave"] for c in resp.json()}
        # Claves mínimas esperadas por el seed de module_setting.md.
        assert {
            "pago_efectivo_activo",
            "pago_transferencia_activo",
            "pago_tarjeta_debito_activo",
            "pago_tarjeta_credito_activo",
            "pago_msi_activo",
            "pago_vales_activo",
            "zona_horaria",
        }.issubset(claves)

    def test_efectivo_no_se_puede_desactivar(self, client, auth_headers):
        resp = client.patch(
            f"{BASE}/configuracion/pago_efectivo_activo",
            json={"valor": "0"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_activar_y_revertir_msi(self, client, auth_headers):
        # MSI: bloqueado por defecto, puede activarse -- se revierte al
        # final para no dejar estado alterado entre corridas de la suite.
        resp_on = client.patch(
            f"{BASE}/configuracion/pago_msi_activo",
            json={"valor": "1"},
            headers=auth_headers,
        )
        assert resp_on.status_code == 200
        assert resp_on.json()["valor"] == "1"

        resp_off = client.patch(
            f"{BASE}/configuracion/pago_msi_activo",
            json={"valor": "0"},
            headers=auth_headers,
        )
        assert resp_off.status_code == 200
        assert resp_off.json()["valor"] == "0"

    def test_metodo_pago_valor_invalido_422(self, client, auth_headers):
        resp = client.patch(
            f"{BASE}/configuracion/pago_tarjeta_debito_activo",
            json={"valor": "activo"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_clabe_acepta_texto_libre(self, client, auth_headers, db_session):
        resp = client.patch(
            f"{BASE}/configuracion/clabe_1",
            json={"valor": "012180001234567895"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["valor"] == "012180001234567895"
        # limpiar -- CLABE de prueba no debe quedar persistida entre corridas
        db_session.expire_all()
        config = db_session.get(Configuracion, "clabe_1")
        config.valor = ""
        db_session.commit()

    def test_clave_inexistente_404(self, client, auth_headers):
        resp = client.patch(
            f"{BASE}/configuracion/clave_que_no_existe",
            json={"valor": "1"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# Autorización -- todos los endpoints están protegidos (module_setting.md)
# ──────────────────────────────────────────────────────────────────────────

class TestAutorizacion:
    @pytest.mark.parametrize(
        "metodo,ruta,json_body",
        [
            ("get", f"{BASE}/zona-horaria", None),
            ("get", f"{BASE}/configuracion", None),
            ("post", f"{BASE}/usuarios", {"usuario": "x", "password": "Abcd1234", "rol": "estandar"}),
            ("patch", f"{BASE}/usuarios/1/password", {"password": "Abcd1234"}),
            ("patch", f"{BASE}/usuarios/1/rol", {"rol": "admin"}),
            ("patch", f"{BASE}/configuracion/pago_msi_activo", {"valor": "1"}),
        ],
    )
    def test_endpoint_sin_token_401(self, client, metodo, ruta, json_body):
        kwargs = {"json": json_body} if json_body is not None else {}
        resp = getattr(client, metodo)(ruta, **kwargs)
        assert resp.status_code == 401
