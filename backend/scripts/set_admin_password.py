"""
Fija (o crea) la contraseña de un usuario admin directo en pos.db.
Misma lógica que test/conftest.py::_fijar_password_admin, pero standalone
para poder loguearte por curl fuera de pytest.

Uso:
    cd backend
    python3 scripts/set_admin_password.py --usuario admin --password "TuPasswordReal123"

Si el usuario no existe, se crea con rol=admin, activo=1.
Si ya existe, solo se sobrescribe password_hash.
"""
import argparse
import sys

sys.path.insert(0, ".")  # asume que se corre desde backend/

from passlib.context import CryptContext
from app.db.database import SessionLocal
from app.models.models import Usuario

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--usuario", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.usuario == args.usuario).first()
        hash_ = _pwd_context.hash(args.password)
        if usuario is None:
            usuario = Usuario(usuario=args.usuario, password_hash=hash_, rol="admin", activo=1)
            db.add(usuario)
            print(f"Usuario '{args.usuario}' creado con rol=admin.")
        else:
            usuario.password_hash = hash_
            print(f"Password de '{args.usuario}' actualizada.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
