# pos-boutique

Sistema de punto de venta y control de crédito para una boutique de ropa,
calzado y accesorios. Gestiona cartera de clientes a crédito, pedidos a proveedor,
inventario/catalogo propio, ventas de intermediación (Shein) y recargas telefónicas, desde
un panel único de operación diaria.

> **Estado actual del proyecto:** en reestructuración activa. El código existente
> fue construido sobre un modelo de datos anterior al actual. Antes de escribir
> una sola línea nueva, lee `docs/REPORT.md` — es el inventario real de qué
> está construido, qué está desalineado y qué falta.

---

## Documentación — orden de lectura recomendado

| Orden | Documento | Para qué sirve |
|---|---|---|
| 0 | [`docs/REPORT.md`](docs/REPORT.md) | **Léelo primero.** Bitácora de estado: qué está construido y con test en verde ahora mismo, qué está desalineado, qué falta. No es spec — nunca decide una regla de negocio nueva, solo documenta el estado real del código contra los tres documentos de abajo. |
| 1 | [`docs/spec/*.md`](docs/spec/README.md) | **Fuente de verdad.** Especificación de pantallas, formularios y flujos de UI/UX, módulo por módulo. Tiene precedencia sobre cualquier otro documento si hay contradicción. |
| 2 | [`docs/REGLAS_NEGOCIO.md`](docs/REGLAS_NEGOCIO.md) | Modelo de datos completo (tablas, enums, relaciones) y reglas de negocio puras, sin UI. |
| 3 | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Stack técnico, estructura de carpetas, decisiones de arquitectura (auth, base de datos, despliegue). |

**Regla de precedencia si dos documentos se contradicen:**
`docs/spec/module_*.md` > `docs/REGLAS_NEGOCIO.md` > `docs/ARQUITECTURA.md`.
`docs/REPORT.md` nunca es fuente de una decisión de diseño — solo refleja el
estado actual del código contra esos tres.

---

## Cómo está organizado el filesystem

```
docs/
├── REPORT.md              # Bitácora de estado (léelo primero, ver arriba)
├── spec/                  # Fuente de verdad — qué construir, módulo por módulo
│   ├── README.md          # Índice de specs
│   ├── resumen_tablas.md  # Índice de tablas de todos los módulos
│   └── module_*.md        # Un archivo por módulo: pantallas, formularios, flujos
├── REGLAS_NEGOCIO.md      # Modelo de datos completo + reglas de negocio, sin UI
├── ARQUITECTURA.md        # Stack técnico, estructura de carpetas, decisiones técnicas
├── frontend/              # Planeación de frontend — "cuándo y en qué orden",
│   │                      # a propósito separado de spec/ ("qué construir")
│   ├── ROADMAP_FRONTEND.md              # Mapa global
│   └── implementation_plan_frontend.md  # Paso 0
└── assets/                # Imágenes referenciadas por los documentos de arriba

backend/
├── app/                   # Código: api/, core/, db/, models/, schemas/, services/
├── alembic/versions/      # Migraciones — el esquema real de pos.db nace aquí
└── test/                  # Un test_<módulo>.py por módulo, mapeado 1:1 a app/
    └── docs/              # Espejo en lenguaje humano de cada test_<módulo>.py
                            # (ej. test/docs/casos_setting.md). No es spec —
                            # es una ayuda de lectura del propio test.

frontend/src/               # Frontend — sin inicializar
scripts/                    # Utilitarios de una sola vez (ej. carga inicial de cartera)
```

Si necesitas la spec de un módulo específico, no busques en `ARQUITECTURA.md`
ni en `REGLAS_NEGOCIO.md` primero — ve directo a `docs/spec/module_<nombre>.md`.
Esos dos documentos solo cubren lo transversal (todo el sistema), no el
detalle de un módulo.

---

## Stack técnico (resumen — detalle completo en `ARQUITECTURA.md`)

- **Backend:** FastAPI + SQLAlchemy (síncrono) + SQLite + Alembic
- **Autenticación:** JWT + bcrypt (actualmente desactivada en MVP, ver `ARQUITECTURA.md`)
- **Frontend:** React + TypeScript + Vite *(planeado — no inicializado aún)*

## Estructura del repositorio

```
backend/
├── alembic/           # Migraciones de base de datos
├── app/
│   ├── api/            # Endpoints (routers)
│   ├── core/            # Configuración, seguridad
│   ├── db/               # Conexión a base de datos
│   ├── models/            # Modelos SQLAlchemy
│   ├── schemas/            # Schemas Pydantic (validación de entrada/salida)
│   └── services/            # Lógica de negocio
├── test/               # Un test_<módulo>.py por módulo — ver docs/REPORT.md
│   └── docs/            # para el estado real de cobertura, módulo por módulo
├── scripts/            # Utilitarios del backend (ej. set_admin_password.py)
└── pos.db              # Base de datos SQLite local

docs/                   # Toda la documentación del proyecto — ver sección de arriba
frontend/src/           # Sin inicializar
scripts/                # Scripts utilitarios de una sola vez (ej. carga inicial de cartera)
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
