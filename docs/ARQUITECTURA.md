# Arquitectura — pos-boutique

> Este documento responde **cómo está construido el sistema**, no qué hace ni qué
> reglas de negocio aplica (eso vive en `REGLAS_NEGOCIO.md`) ni cómo se ve la UI
> (eso vive en `00_FULLSTACK_DEVELOPMENT.md`).

---

## 1. Alcance del sistema

`pos-boutique` es una aplicación **de un solo negocio, una sola operadora, un solo
punto de venta físico**. No existe ni se planea:
- Soporte multi-empresa o multi-sucursal.
- Roles corporativos jerárquicos (gerente regional, supervisor de zona, etc.).
- Sincronización multi-dispositivo en tiempo real entre puntos de venta.

> Nota histórica: una versión anterior de este documento introducía tablas
> `empresas`, `sucursales` e `impuestos` con relaciones corporativas. Eso nunca
> formó parte del alcance real del proyecto y fue retirado por completo.

El sistema corre **localmente**, en la máquina de operación del negocio, con base
de datos SQLite en archivo.

---

## 2. Stack técnico

| Capa | Tecnología | Notas |
|---|---|---|
| Backend | FastAPI | Framework principal de la API REST |
| ORM | SQLAlchemy (**síncrono**) | El acceso a SQLite es síncrono. No se usa `aiosqlite` ni sesiones async |
| Migraciones | Alembic | Toda alteración de esquema pasa por una migración versionada |
| Base de datos | SQLite (archivo local `pos.db`) | Adecuado para el volumen de operación de un solo negocio |
| Validación | Pydantic (schemas) | Separados de los modelos SQLAlchemy — ver sección 4 |
| Autenticación | JWT + bcrypt | Ver sección 5 |
| Frontend (planeado) | React + TypeScript + Vite | No inicializado aún |

---

## 3. Estructura de capas (backend)

```
Request HTTP
    │
    ▼
app/api/v1/endpoints/*      ← Routers. Reciben request, validan con schemas, delegan a services.
    │
    ▼
app/schemas/*                ← Pydantic. Validación de entrada/salida. No contienen lógica de negocio.
    │
    ▼
app/services/*               ← Lógica de negocio pura. Orquesta transacciones, valida reglas.
    │
    ▼
app/models/*                 ← SQLAlchemy. Definición de tablas. Sin lógica de negocio.
    │
    ▼
app/db/database.py           ← Conexión y sesión de SQLAlchemy (síncrona)
```

**Regla de capas:** un endpoint nunca construye una query directamente ni aplica
reglas de negocio inline — siempre delega a un `service`. Un `service` nunca
devuelve un objeto SQLAlchemy crudo a un endpoint sin pasar por un `schema` de
salida.

---

## 4. Modelo de datos

El modelo de datos completo (tablas, enums, relaciones) vive en `REGLAS_NEGOCIO.md`,
no aquí. Este documento solo señala las decisiones **técnicas** sobre ese modelo:

- Las migraciones de Alembic son la única forma válida de alterar el esquema.
  Nunca se edita el archivo `pos.db` directamente.
- Los enums de negocio (`Operacion`, `FormaPago`, `EstatusInventario`, etc.) se
  definen como `enum.Enum` de Python y se mapean a `Enum` de SQLAlchemy — no como
  `String` libre. Esto fue una causa de bugs en la versión anterior del código
  (estados como `"liquidado"` que no existían en ningún enum, capturados como string suelto).
- Las fechas se almacenan en `Date` (solo fecha) o `DateTime` (timestamp completo)
  según lo que indique cada tabla — no todo el sistema usa el mismo tipo de columna.

---

## 5. Autenticación y seguridad

- Las contraseñas se almacenan como hash `bcrypt`. Nunca en texto plano.
- La sesión se maneja con JWT. El token se genera al hacer login y se envía en
  cada request al backend vía header `Authorization: Bearer <token>`.
- **MVP:** el login está construido pero **desactivado** mediante la variable
  `AUTH_ENABLED` en `backend/app/core/config.py`. Se activa cuando el sistema
  entra a operación real.
- No hay recuperación de contraseña por correo — el sistema opera offline. La
  recuperación la hace el desarrollador directamente en la base de datos.
- Los roles (`estandar`, `admin`) existen en el esquema desde el MVP, pero la
  lógica de permisos diferenciados se implementa en versiones futuras, sin
  necesidad de cambiar el esquema cuando llegue ese momento.

---

## 6. Despliegue

> **Pendiente de confirmación.** No tengo evidencia verificada de cómo se
> despliega hoy el sistema en producción (servicio systemd, proceso manual,
> nombre de máquina). Si me confirmas ese flujo, lo documento aquí con precisión
> en vez de asumirlo.

---

## 7. Pruebas

- Framework: a confirmar (pytest es el estándar para FastAPI, pero no hay
  evidencia de configuración existente en `backend/tests/`).
- Criterio de "completado" para cualquier funcionalidad: modelo → migración →
  schema → endpoint → lógica de negocio correcta → **test que la cubre y pasa**.
  Sin test, una funcionalidad se considera parcial, no completa — ver
  `docs/AUDITORIA.md` para el criterio aplicado hoy al estado del proyecto.
