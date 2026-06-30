from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./pos.db"

    # Antes hardcodeados en app/services/auth_service.py.
    # En producción, SECRET_KEY debe sobreescribirse vía .env — nunca
    # commitear el valor real al repo. Rotar esta clave invalida todos
    # los tokens activos.
    SECRET_KEY: str = "pos-boutique-secret-key-cambiar-en-produccion"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRY_HOURS: int = 8  # sesión de una jornada laboral

    class Config:
        env_file = ".env"


settings = Settings()
