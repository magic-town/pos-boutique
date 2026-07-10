## Autenticación y Configuración

---

### Autenticación

Al abrir `pos-boutique` se presenta la ventana de login.

> **Estado actual:** la autenticación está **activa**. Todos los endpoints están
> protegidos con `Depends(get_current_user)`. `config.py` no tiene flag `AUTH_ENABLED`.
> La sesión se maneja con JWT real (`python-jose`). No se desactiva en MVP.

**Campos:**

| Etiqueta   | Modelo     | Tipo   | Reglas                                                   |
| ---------- | ---------- | ------ | -------------------------------------------------------- |
| Usuario    | `usuario`  | String | 4 a 16 caracteres. Sin espacios.                         |
| Contraseña | `password` | String | 4 a 10 caracteres. Al menos una mayúscula. Input oculto. |

**Tabla `usuarios`:**

```sql
CREATE TABLE usuarios (
    id_usuario     INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario        TEXT     NOT NULL UNIQUE,
    password_hash  TEXT     NOT NULL,   -- bcrypt. Nunca texto plano.
    rol            TEXT     NOT NULL DEFAULT 'estandar'
                       CHECK (rol IN ('estandar', 'admin')),
    activo         INTEGER  NOT NULL DEFAULT 1,   -- 1 = activo, 0 = desactivado
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Usuarios iniciales (seed):**

> ⚠️ **Nota de seguridad:** no subir contraseñas reales (ni de seed) en texto
> plano a ningún documento versionado en git.

```python
# backend/db/seed.py
usuarios = [
    {"usuario": "sonia",     "password": "<REDACTADO -- ver nota de seguridad>", "rol": "estandar"},
    {"usuario": "operador2", "password": "<REDACTADO -- ver nota de seguridad>",  "rol": "estandar"}
]
```

**Notas de seguridad:**
- Las contraseñas se almacenan como hash `bcrypt`. Nunca en texto plano.
- La sesión se maneja con JWT. El token se genera al hacer login y se incluye en cada request al backend vía header `Authorization: Bearer <token>`.
- No hay recuperación de contraseña por correo — el sistema opera offline. La recuperación la hace el desarrollador directamente en la DB.

---

### Módulo Setting

Botón `⚙️` visible en el Panel Principal. Abre una ventana de configuración del sistema.
Es un esqueleto funcional en MVP — no se construye flujo complejo hasta que el sistema
esté en producción.

#### Opciones disponibles

```yaml
titulo_ventana: Configuración del Sistema
secciones:
  - titulo: Usuarios
    opciones:
      - Agregar nuevo usuario
      - Cambiar contraseña
      - Cambiar rol de usuario   # solo edición de enum; sin lógica de permisos diferenciada en MVP
  - titulo: Información del sistema
    campos:
      - Zona horaria: almacenada en la tabla `configuracion` (clave `zona_horaria`). Solo lectura. Informativo.
  - titulo: Métodos de pago
    descripcion: Activa o desactiva las formas de pago disponibles en el Panel Principal.
    controles:
      - Efectivo:               activo, no desactivable
      - Transferencia bancaria: activo. Campo editable para CLABE.
                                Permite agregar múltiples CLABE (ej: BBVA + Banamex).
      - Tarjeta débito:         activo por defecto. Puede desactivarse.
      - Tarjeta crédito:        activo por defecto. Puede desactivarse.
      - Meses sin intereses (MSI): bloqueado por defecto. Puede activarse.
      - Vales:                  bloqueado por defecto. Puede activarse.
```

**Tabla `configuracion`:**

```sql
CREATE TABLE configuracion (
    clave   TEXT PRIMARY KEY,
    valor   TEXT NOT NULL
);

-- Valores iniciales (seed):
-- ('pago_efectivo_activo',        '1')
-- ('pago_transferencia_activo',   '1')
-- ('pago_tarjeta_debito_activo',  '1')
-- ('pago_tarjeta_credito_activo', '1')
-- ('pago_msi_activo',             '0')
-- ('pago_vales_activo',           '0')
-- ('clabe_1',                     '')
-- ('clabe_2',                     '')
-- ('zona_horaria',                'America/Mexico_City')
```

> Los permisos diferenciados entre `estandar` y `admin` se implementan en versiones futuras.
> La entidad `rol` ya existe en DB — cuando llegue el momento solo se añade lógica de
> verificación en el backend sin cambio de esquema.

#### Endpoints (`/api/v1/setting`)

Todos protegidos con `Depends(get_current_user)`.

| Endpoint                                  | Método | Función                                                                                 |
| ------------------------------------------ | ------ | ---------------------------------------------------------------------------------------- |
| `/setting/usuarios`                        | POST   | Agregar nuevo usuario. 409 si el usuario ya existe.                                     |
| `/setting/usuarios/{id_usuario}/password`  | PATCH  | Cambiar contraseña.                                                                       |
| `/setting/usuarios/{id_usuario}/rol`       | PATCH  | Cambiar rol (`estandar`/`admin`). Solo edición de enum, sin lógica de permisos.          |
| `/setting/zona-horaria`                    | GET    | Solo lectura. Devuelve el valor de `configuracion` para la clave `zona_horaria`.         |
| `/setting/configuracion`                   | GET    | Lista todas las claves/valores de `configuracion` (métodos de pago, CLABEs, zona horaria). |
| `/setting/configuracion/{clave}`           | PATCH  | Actualiza una clave. Para claves de métodos de pago, `valor` debe ser `'0'` o `'1'`. `pago_efectivo_activo` rechaza `'0'` (409, no desactivable). |

Las CLABEs (`clabe_1`, `clabe_2`) se actualizan por el mismo endpoint genérico de
`configuracion`, como texto libre — sin validación de formato en MVP.

---
