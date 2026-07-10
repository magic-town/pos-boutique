"""
test_autenticacion.py — Cobertura completa del módulo de Autenticación.

Cubre:
    1. Hashing de contraseñas (auth_service.hash_password / verificar_password)
    2. Generación de JWT (auth_service.crear_token)
    3. Acceso a usuarios en BD (obtener_usuario / autenticar_usuario / crear_usuario)
    4. Endpoint POST /auth/login, de extremo a extremo (FastAPI + TestClient)
    5. Dependency get_current_user, de extremo a extremo (header -> token -> usuario)
    6. Schemas Pydantic: UsuarioCreate, UsuarioRead, Token, TokenData

Convenciones:
    - BD de prueba: SQLite en memoria, recreada en cada test (aislamiento total).
    - Los tests de endpoint montan una app FastAPI mínima con solo el router
      necesario, en vez de importar app.main completo, para no depender de
      otros módulos (clientes, inventario, etc.) que no son responsabilidad
      de este archivo.
"""

from datetime import datetime, timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.database import Base, get_db
from app.models.models import Usuario
from app.schemas.token import Token, TokenData
from app.schemas.usuario import UsuarioCreate, UsuarioRead
from app.services.auth_service import (
    autenticar_usuario,
    crear_token,
    crear_usuario,
    get_current_user,
    hash_password,
    obtener_usuario,
    verificar_password,
)
from app.api.v1.endpoints.auth import router as auth_router


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def engine():
    """Motor SQLite en memoria, aislado por test (no comparte estado entre tests)."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture()
def db_session(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client_login(db_session):
    """App FastAPI real con el router de auth montado, para probar
    POST /auth/login de extremo a extremo (form data, status codes, token)."""
    app = FastAPI()
    app.include_router(auth_router)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture()
def client_protegido(db_session):
    """App FastAPI mínima con una ruta protegida por get_current_user, para
    probar la dependency completa: header Authorization -> decode -> lookup."""
    app = FastAPI()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/protegida")
    def ruta_protegida(usuario: Usuario = Depends(get_current_user)):
        return {"usuario": usuario.usuario, "rol": usuario.rol}

    return TestClient(app)


@pytest.fixture()
def usuario_activo(db_session):
    return crear_usuario(db_session, usuario="ana", password="clave123", rol="admin")


@pytest.fixture()
def usuario_inactivo(db_session):
    user = crear_usuario(db_session, usuario="bob", password="clave123")
    user.activo = 0
    db_session.commit()
    db_session.refresh(user)
    return user


def _token_valido(usuario: Usuario) -> str:
    return crear_token({"sub": usuario.usuario, "rol": usuario.rol})


# ═══════════════════════════════════════════════════════════════════════════
# 1. HASHING DE CONTRASEÑAS
# ═══════════════════════════════════════════════════════════════════════════

class TestPasswordHashing:

    def test_hash_no_es_igual_al_password_plano(self):
        assert hash_password("clave123") != "clave123"

    def test_hash_es_verificable_con_password_correcto(self):
        hashed = hash_password("clave123")
        assert verificar_password("clave123", hashed) is True

    def test_verificar_rechaza_password_incorrecto(self):
        hashed = hash_password("clave123")
        assert verificar_password("otra-clave", hashed) is False

    def test_hash_genera_salts_distintos_para_mismo_password(self):
        # bcrypt debe generar un hash distinto cada vez (salt aleatorio),
        # aunque ambos verifiquen contra el mismo password.
        h1 = hash_password("clave123")
        h2 = hash_password("clave123")
        assert h1 != h2
        assert verificar_password("clave123", h1)
        assert verificar_password("clave123", h2)


# ═══════════════════════════════════════════════════════════════════════════
# 2. GENERACIÓN DE JWT
# ═══════════════════════════════════════════════════════════════════════════

class TestCrearToken:

    def test_token_incluye_claims_provistos(self):
        token = crear_token({"sub": "ana", "rol": "admin"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "ana"
        assert payload["rol"] == "admin"

    def test_token_expira_segun_default_de_settings(self):
        antes = datetime.utcnow()
        token = crear_token({"sub": "ana"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = datetime.utcfromtimestamp(payload["exp"])
        esperado = antes + timedelta(hours=settings.TOKEN_EXPIRY_HOURS)
        # Tolerancia de unos segundos por el tiempo de ejecución del test.
        assert abs((exp - esperado).total_seconds()) < 5

    def test_token_respeta_expiry_personalizado(self):
        token = crear_token({"sub": "ana"}, expiry=timedelta(minutes=1))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = datetime.utcfromtimestamp(payload["exp"])
        assert exp < datetime.utcnow() + timedelta(minutes=2)

    def test_token_firmado_con_secret_key_correcta(self):
        token = crear_token({"sub": "ana"})
        with pytest.raises(Exception):
            jwt.decode(token, "clave-incorrecta", algorithms=[settings.ALGORITHM])


# ═══════════════════════════════════════════════════════════════════════════
# 3. ACCESO A USUARIOS EN BD
# ═══════════════════════════════════════════════════════════════════════════

class TestObtenerYAutenticarUsuario:

    def test_obtener_usuario_existente(self, db_session, usuario_activo):
        encontrado = obtener_usuario(db_session, "ana")
        assert encontrado is not None
        assert encontrado.id_usuario == usuario_activo.id_usuario

    def test_obtener_usuario_inexistente_retorna_none(self, db_session):
        assert obtener_usuario(db_session, "no-existe") is None

    def test_autenticar_credenciales_correctas(self, db_session, usuario_activo):
        user = autenticar_usuario(db_session, "ana", "clave123")
        assert user is not None
        assert user.usuario == "ana"

    def test_autenticar_password_incorrecto_retorna_none(self, db_session, usuario_activo):
        assert autenticar_usuario(db_session, "ana", "password-equivocado") is None

    def test_autenticar_usuario_inexistente_retorna_none(self, db_session):
        assert autenticar_usuario(db_session, "fantasma", "clave123") is None

    def test_autenticar_usuario_inactivo_retorna_none(self, db_session, usuario_inactivo):
        assert autenticar_usuario(db_session, "bob", "clave123") is None


class TestCrearUsuario:

    def test_crear_usuario_hashea_el_password(self, db_session):
        user = crear_usuario(db_session, usuario="carla", password="clave123")
        assert user.password_hash != "clave123"
        assert verificar_password("clave123", user.password_hash)

    def test_crear_usuario_activo_por_defecto(self, db_session):
        user = crear_usuario(db_session, usuario="carla", password="clave123")
        assert user.activo == 1

    def test_crear_usuario_rol_por_defecto_estandar(self, db_session):
        user = crear_usuario(db_session, usuario="carla", password="clave123")
        assert user.rol == "estandar"

    def test_crear_usuario_persiste_en_bd(self, db_session):
        crear_usuario(db_session, usuario="carla", password="clave123")
        assert obtener_usuario(db_session, "carla") is not None

    def test_crear_usuario_duplicado_lanza_integrity_error(self, db_session, usuario_activo):
        with pytest.raises(IntegrityError):
            crear_usuario(db_session, usuario="ana", password="otra-clave")
        db_session.rollback()


# ═══════════════════════════════════════════════════════════════════════════
# 4. ENDPOINT POST /auth/login
# ═══════════════════════════════════════════════════════════════════════════

class TestEndpointLogin:

    def test_login_exitoso_retorna_token(self, client_login, usuario_activo):
        resp = client_login.post(
            "/auth/login", data={"username": "ana", "password": "clave123"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_token_contiene_sub_y_rol_correctos(self, client_login, usuario_activo):
        resp = client_login.post(
            "/auth/login", data={"username": "ana", "password": "clave123"}
        )
        token = resp.json()["access_token"]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "ana"
        assert payload["rol"] == "admin"

    def test_login_password_incorrecto_devuelve_401(self, client_login, usuario_activo):
        resp = client_login.post(
            "/auth/login", data={"username": "ana", "password": "equivocado"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Usuario o contraseña incorrectos"

    def test_login_usuario_inexistente_devuelve_401(self, client_login):
        resp = client_login.post(
            "/auth/login", data={"username": "fantasma", "password": "clave123"}
        )
        assert resp.status_code == 401

    def test_login_usuario_inactivo_devuelve_401(self, client_login, usuario_inactivo):
        resp = client_login.post(
            "/auth/login", data={"username": "bob", "password": "clave123"}
        )
        assert resp.status_code == 401

    def test_login_mismo_mensaje_para_usuario_y_password_incorrectos(
        self, client_login, usuario_activo
    ):
        # No debe filtrar si el usuario existe o no — mismo status y mensaje.
        r_user = client_login.post(
            "/auth/login", data={"username": "fantasma", "password": "clave123"}
        )
        r_pass = client_login.post(
            "/auth/login", data={"username": "ana", "password": "equivocado"}
        )
        assert r_user.status_code == r_pass.status_code == 401
        assert r_user.json()["detail"] == r_pass.json()["detail"]

    def test_login_sin_campos_devuelve_422(self, client_login):
        resp = client_login.post("/auth/login", data={})
        assert resp.status_code == 422

    def test_login_incluye_header_www_authenticate_en_401(self, client_login, usuario_activo):
        resp = client_login.post(
            "/auth/login", data={"username": "ana", "password": "equivocado"}
        )
        assert resp.headers.get("www-authenticate") == "Bearer"


# ═══════════════════════════════════════════════════════════════════════════
# 5. DEPENDENCY get_current_user (ruta protegida, de extremo a extremo)
# ═══════════════════════════════════════════════════════════════════════════

class TestGetCurrentUser:

    def test_sin_token_devuelve_401(self, client_protegido):
        resp = client_protegido.get("/protegida")
        assert resp.status_code == 401

    def test_token_valido_devuelve_200_y_datos_de_usuario(
        self, client_protegido, usuario_activo
    ):
        token = _token_valido(usuario_activo)
        resp = client_protegido.get(
            "/protegida", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json() == {"usuario": "ana", "rol": "admin"}

    def test_token_malformado_devuelve_401(self, client_protegido):
        resp = client_protegido.get(
            "/protegida", headers={"Authorization": "Bearer esto-no-es-un-jwt"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Token inválido o expirado"

    def test_token_expirado_devuelve_401(self, client_protegido, usuario_activo):
        token = crear_token(
            {"sub": usuario_activo.usuario, "rol": usuario_activo.rol},
            expiry=timedelta(seconds=-1),
        )
        resp = client_protegido.get(
            "/protegida", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    def test_token_firmado_con_otra_clave_devuelve_401(self, client_protegido, usuario_activo):
        token_ajeno = jwt.encode(
            {"sub": usuario_activo.usuario, "rol": usuario_activo.rol},
            "otra-clave-distinta",
            algorithm=settings.ALGORITHM,
        )
        resp = client_protegido.get(
            "/protegida", headers={"Authorization": f"Bearer {token_ajeno}"}
        )
        assert resp.status_code == 401

    def test_token_sin_claim_sub_devuelve_401(self, client_protegido):
        # Token válido y bien firmado, pero sin el claim "sub" (usuario).
        payload = {"rol": "admin", "exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        resp = client_protegido.get(
            "/protegida", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    def test_usuario_del_token_ya_no_existe_en_bd_devuelve_401(
        self, client_protegido, db_session, usuario_activo
    ):
        token = _token_valido(usuario_activo)
        db_session.delete(usuario_activo)
        db_session.commit()
        resp = client_protegido.get(
            "/protegida", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    def test_usuario_desactivado_despues_de_emitir_token_devuelve_401(
        self, client_protegido, db_session, usuario_activo
    ):
        token = _token_valido(usuario_activo)
        usuario_activo.activo = 0
        db_session.commit()
        resp = client_protegido.get(
            "/protegida", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    def test_sin_esquema_bearer_devuelve_401(self, client_protegido, usuario_activo):
        token = _token_valido(usuario_activo)
        # Header sin el prefijo "Bearer " — OAuth2PasswordBearer debe rechazarlo.
        resp = client_protegido.get(
            "/protegida", headers={"Authorization": token}
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# 6. SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class TestSchemaUsuarioCreate:

    def test_datos_validos_se_aceptan(self):
        u = UsuarioCreate(usuario="usuario1", password="Clave123")
        assert u.usuario == "usuario1"
        assert u.rol == "estandar"  # default

    def test_rol_admin_se_acepta(self):
        u = UsuarioCreate(usuario="usuario1", password="Clave123", rol="admin")
        assert u.rol == "admin"

    def test_usuario_vacio_lanza_error(self):
        with pytest.raises(ValidationError):
            UsuarioCreate(usuario="   ", password="Clave123")

    def test_password_vacio_lanza_error(self):
        with pytest.raises(ValidationError):
            UsuarioCreate(usuario="usuario1", password="")

    def test_espacios_al_borde_se_recortan(self):
        u = UsuarioCreate(usuario="  usuario1  ", password="  Clave123  ")
        assert u.usuario == "usuario1"
        assert u.password == "Clave123"

    def test_rol_invalido_lanza_error(self):
        with pytest.raises(ValidationError):
            UsuarioCreate(usuario="usuario1", password="Clave123", rol="superadmin")

    # ── usuario: 4 a 16 caracteres, sin espacios (module_setting.md) ──────

    def test_usuario_muy_corto_lanza_error(self):
        with pytest.raises(ValidationError):
            UsuarioCreate(usuario="abc", password="Clave123")  # 3 caracteres

    def test_usuario_muy_largo_lanza_error(self):
        with pytest.raises(ValidationError):
            UsuarioCreate(usuario="a" * 17, password="Clave123")

    def test_usuario_limite_inferior_valido(self):
        u = UsuarioCreate(usuario="abcd", password="Clave123")  # exactamente 4
        assert u.usuario == "abcd"

    def test_usuario_limite_superior_valido(self):
        u = UsuarioCreate(usuario="a" * 16, password="Clave123")  # exactamente 16
        assert len(u.usuario) == 16

    def test_usuario_con_espacios_internos_lanza_error(self):
        with pytest.raises(ValidationError):
            UsuarioCreate(usuario="juan perez", password="Clave123")

    # ── password: 4 a 10 caracteres, al menos una mayúscula (module_setting.md) ──

    def test_password_muy_corta_lanza_error(self):
        with pytest.raises(ValidationError):
            UsuarioCreate(usuario="usuario1", password="Ab1")  # 3 caracteres

    def test_password_muy_larga_lanza_error(self):
        with pytest.raises(ValidationError):
            UsuarioCreate(usuario="usuario1", password="Clave12345678")  # 13 caracteres

    def test_password_limite_inferior_valido(self):
        u = UsuarioCreate(usuario="usuario1", password="Abcd")  # exactamente 4
        assert u.password == "Abcd"

    def test_password_limite_superior_valido(self):
        u = UsuarioCreate(usuario="usuario1", password="Abcdefghij")  # exactamente 10
        assert len(u.password) == 10

    def test_password_sin_mayuscula_lanza_error(self):
        with pytest.raises(ValidationError):
            UsuarioCreate(usuario="usuario1", password="clave123")


class TestSchemaUsuarioRead:

    def test_se_construye_desde_objeto_orm(self, db_session, usuario_activo):
        leido = UsuarioRead.model_validate(usuario_activo)
        assert leido.usuario == "ana"
        assert leido.rol == "admin"
        assert leido.id_usuario == usuario_activo.id_usuario

    def test_campo_activo_es_int_no_string(self, usuario_activo):
        leido = UsuarioRead.model_validate(usuario_activo)
        assert leido.activo == 1
        assert isinstance(leido.activo, int)

    def test_no_expone_campo_username(self, usuario_activo):
        # Bug histórico: el schema usaba "username" en vez de "usuario".
        leido = UsuarioRead.model_validate(usuario_activo)
        assert not hasattr(leido, "username")
        assert hasattr(leido, "usuario")

    def test_fecha_registro_opcional(self, usuario_activo):
        leido = UsuarioRead.model_validate(usuario_activo)
        assert leido.fecha_registro is not None  # server_default=func.now()


class TestSchemaToken:

    def test_token_type_por_defecto_bearer(self):
        t = Token(access_token="abc123")
        assert t.token_type == "bearer"

    def test_token_data_campos_son_opcionales(self):
        td = TokenData()
        assert td.usuario is None
        assert td.rol is None

    def test_token_data_acepta_valores(self):
        td = TokenData(usuario="ana", rol="admin")
        assert td.usuario == "ana"
        assert td.rol == "admin"
