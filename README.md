# pos-boutique

Sistema de punto de venta y control de crédito para una boutique de ropa,
calzado y accesorios. Gestiona cartera de clientes a crédito, pedidos a proveedor,
inventario/catalogo propio, ventas de intermediación (Shein) y recargas telefónicas, desde
un panel único de operación diaria.

> **Estado actual del proyecto:** en reestructuración activa. El código existente
> fue construido sobre un modelo de datos anterior al actual. Antes de escribir
> una sola línea nueva, lee `docs/AUDITORIA.md` — es el inventario real de qué
> está construido, qué está desalineado y qué falta.

---

## Documentación — orden de lectura recomendado

| Orden | Documento | Para qué sirve |
|---|---|---|
| 1 | [`docs/FULLSTACK/*.md`](docs/FULLSTACK/README.md) | **Fuente de verdad.** Especificación de pantallas, formularios y flujos de UI/UX. Tiene precedencia sobre cualquier otro documento si hay contradicción. |
| 2 | [`docs/REGLAS_NEGOCIO.md`](docs/REGLAS_NEGOCIO.md) | Modelo de datos completo (tablas, enums, relaciones) y reglas de negocio puras, sin UI. |
| 3 | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Stack técnico, estructura de carpetas, decisiones de arquitectura (auth, base de datos, despliegue). |

---

## Stack técnico (resumen — detalle completo en `ARQUITECTURA.md`)

- **Backend:** FastAPI + SQLAlchemy (síncrono) + SQLite + Alembic
- **Autenticación:** JWT + bcrypt (actualmente desactivada en MVP, ver `ARQUITECTURA.md`)
- **Frontend:** React + TypeScript + Vite *(planeado — no inicializado aún)*

## Estructura del repositorio

```
backend/
├── alembic/          # Migraciones de base de datos
├── app/
│   ├── api/           # Endpoints (routers)
│   ├── core/          # Configuración, seguridad
│   ├── db/            # Conexión a base de datos
│   ├── models/        # Modelos SQLAlchemy
│   ├── schemas/        # Schemas Pydantic (validación de entrada/salida)
│   └── services/        # Lógica de negocio
├── tests/             # Pruebas (actualmente sin cobertura)
└── pos.db             # Base de datos SQLite local

docs/                  # Toda la documentación del proyecto
frontend/src/          # Sin inicializar
scripts/               # Scripts utilitarios (ej. importación de cartera)
```

## Puesta en marcha (backend)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

> Nota: estos pasos asumen la convención estándar de un proyecto FastAPI con
> Alembic. Si tu flujo de arranque real es distinto (puerto, variables de
> entorno, seed de usuarios), avísame para corregir esta sección — no quiero
> repetir el error de documentar algo que no se verificó.

## Convenciones del proyecto

- Las fechas se almacenan en `YYYY-MM-DD` (o timestamp completo cuando aplica) y se muestran en UI como `DD-MM-YYYY`.
- Los montos se manejan como `Float`/`Integer` según la tabla — ver `REGLAS_NEGOCIO.md` para el detalle exacto por campo.
- El proyecto es de **un solo negocio, una sola operadora** — no hay, ni se planea, soporte multi-empresa o multi-sucursal.
