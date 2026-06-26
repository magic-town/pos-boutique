![](docs/assets/cover.png)

## pos-boutique

Sistema de gestión POS para tienda de ropa con modelo de crédito local.
Digitaliza y consistencia un proceso operativo existente: registro de clientes,
pedidos, movimientos de caja y control de saldo.

---

## Tabla de contenidos

- [pos-boutique](#pos-boutique)
- [Tabla de contenidos](#tabla-de-contenidos)
- [Contexto](#contexto)
- [Modelo de negocio](#modelo-de-negocio)
- [Stack](#stack)
- [Arquitectura](#arquitectura)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación y ejecución](#instalación-y-ejecución)
  - [Requisitos](#requisitos)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Módulos](#módulos)
  - [Operaciones del Panel Principal](#operaciones-del-panel-principal)
- [Modelo de datos](#modelo-de-datos)
- [Versionado](#versionado)
- [Contribución](#contribución)
- [Estado actual](#estado-actual)

---

## Contexto

Pequeña empresa de tienda de ropa. Operación actual: lápiz y papel.
El sistema no reemplaza el proceso — lo digitaliza para eliminar inconsistencias
y dejar trazabilidad de cada operación.

## Modelo de negocio 

Boutique de ropa con esquema de crédito local y financiamiento directo al cliente.

El negocio comercializa prendas de vestir y accesorios mediante venta directa y pedidos por catálogo. Una parte importante de las operaciones se realiza bajo un esquema de crédito interno, donde la empresa financia directamente la compra y el cliente liquida su saldo mediante pagos periódicos (abonos) hasta completar el monto adeudado.

---

## Stack

| Capa           | Tecnología         | Justificación                                              |
|----------------|--------------------|------------------------------------------------------------|
| Frontend       | React + Vite       | Ligero, rápido, ampliamente documentado                    |
| Backend        | FastAPI (Python)   | Simple, moderno, genera docs de API automáticamente        |
| Base de datos  | SQLite             | Sin servidor, archivo único, respaldable con copiar/pegar  |
| Despliegue     | Local (PC tienda)  | Sin dependencia de internet ni infraestructura externa     |
| Actualizaciones| Git + GitHub       | Push desde desarrollo, pull en producción                  |

---

## Arquitectura

```
pos-boutique/
├── frontend/        # React + Vite — interfaz de usuario
├── backend/         # FastAPI — lógica de negocio y API REST
├── docs/            # Documentación técnica y de negocio
└── scripts/         # Scripts de instalación y arranque
```

El frontend consume la API REST del backend vía HTTP local.
El backend lee y escribe en un archivo SQLite único (`pos.db`).
Ambos corren en la misma máquina (PC de la ejecutiva).

```
Navegador (frontend) ──HTTP──▶ FastAPI (backend) ──▶ SQLite (pos.db)
```

---

## Estructura del proyecto

```
pos-boutique/
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ui/          # Botones, inputs, badges — elementos base
│       │   ├── forms/       # Formularios: cliente, pedido, operación
│       │   ├── modals/      # Ventanas emergentes: apartado, confirmaciones
│       │   └── layout/      # Header, sidebar, contenedor principal
│       ├── pages/           # Vistas: Panel Principal, Consulta, Piso de Venta
│       ├── hooks/           # Custom hooks: useCliente, useOperacion, etc.
│       ├── services/        # Llamadas a la API (fetch/axios)
│       ├── store/           # Estado global (si aplica: Zustand o Context)
│       └── utils/           # Helpers: formato de moneda, fechas, validaciones
│
├── backend/
│   └── app/
│       ├── api/
│       │   └── v1/
│       │       └── endpoints/   # Rutas: clientes, pedidos, movimientos, etc.
│       ├── core/                # Configuración, variables de entorno
│       ├── db/                  # Conexión SQLite, inicialización de tablas
│       ├── models/              # Modelos ORM (SQLAlchemy)
│       ├── schemas/             # Esquemas de validación (Pydantic)
│       └── services/            # Lógica de negocio desacoplada de las rutas
│
├── backend/tests/               # Pruebas unitarias e integración
├── docs/                        # Documentación técnica y decisiones de diseño
└── scripts/                     # install.sh, start.sh, backup.sh
```

---

## Instalación y ejecución

### Requisitos

- Python 3.11+
- Node.js 20+
- Git

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API disponible en: `http://localhost:8000`
Documentación automática: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Interfaz disponible en: `http://localhost:5173`

---

## Módulos

| Módulo            | Descripción                                              | Tabla principal   |
|-------------------|----------------------------------------------------------|-------------------|
| Agregar Cliente   | Registro de nuevo cliente con referencia (garante)       | clientes          |
| Pedido            | Pedido de catálogo formal o informal                     | pedidos           |
| Shein             | Pedido especial vía app Shein; siempre de contado        | pedidos_shein     |
| Piso de Venta     | Venta de producto físico en stock (activo en v0.2)       | inventario        |
| Consulta          | Historial de movimientos, saldo y estatus por cliente    | movimientos       |
| Panel Principal   | Registro de operaciones de caja (Contado, Apartado, etc.)| movimientos       |

### Operaciones del Panel Principal

| Operación | Cliente     | Producto | `saldo_resultante` | `forma_pago`                    |
|-----------|-------------|----------|--------------------|---------------------------------|
| Contado   | Opcional    | Sí       | NULL               | efectivo / transferencia / tarjeta |
| Apartado  | Obligatorio | Sí       | precio − 1er pago  | efectivo / transferencia / tarjeta |
| Abono     | Obligatorio | No       | saldo anterior − monto | efectivo / transferencia / tarjeta |
| Gasto     | No          | No       | NULL               | efectivo / transferencia / tarjeta |

---

## Modelo de datos

```
clientes
  id_cliente      INTEGER  PK AUTOINCREMENT
  no_cliente      TEXT     NOT NULL UNIQUE        -- Autogenerado: {Colonia}-{consecutivo}
  nombre          TEXT     NOT NULL
  colonia         TEXT     NOT NULL
  telefono        TEXT     NOT NULL
  ref_nombre      TEXT     NOT NULL               -- Nombre del garante
  ref_colonia     TEXT     NOT NULL               -- Colonia del garante
  ref_telefono    TEXT                            -- Teléfono del garante (nullable)
  saldo           REAL     NOT NULL DEFAULT 0     -- Deuda activa. Positivo = debe.
  estatus         TEXT     NOT NULL DEFAULT 'activo' -- activo | liquidado | rehabilitar
  fecha_registro  TEXT     NOT NULL               -- ISO 8601

pedidos
  id_pedido           INTEGER  PK AUTOINCREMENT
  id_cliente          INTEGER  NOT NULL FK → clientes
  producto            TEXT     NOT NULL
  id_producto_externo TEXT                        -- ID del proveedor (nullable)
  marca               TEXT
  talla               TEXT
  opcion_producto     TEXT                        -- Artículo alternativo (nullable)
  opcion_marca        TEXT
  opcion_talla        TEXT
  fecha               TEXT     NOT NULL           -- ISO 8601

pedidos_shein
  id_pedido_shein INTEGER  PK AUTOINCREMENT
  id_cliente      INTEGER  NOT NULL FK → clientes
  producto        TEXT     NOT NULL
  monto           REAL     NOT NULL
  fecha           TEXT     NOT NULL               -- ISO 8601

inventario
  id_producto     INTEGER  PK AUTOINCREMENT
  descripcion     TEXT     NOT NULL
  marca           TEXT
  talla           TEXT
  cantidad        INTEGER  NOT NULL DEFAULT 0
  precio          REAL     NOT NULL
  fecha_registro  TEXT     NOT NULL               -- ISO 8601

movimientos
  id_movimiento    INTEGER  PK AUTOINCREMENT
  operacion        TEXT     NOT NULL              -- Enum: contado | apartado | abono | gasto
  id_cliente       INTEGER  FK → clientes         -- nullable
  id_producto      INTEGER  FK → inventario       -- nullable; solo si es Piso de Venta
  monto            REAL     NOT NULL
  forma_pago       TEXT     NOT NULL              -- Enum: efectivo | transferencia | tarjeta
  saldo_resultante REAL                           -- nullable; solo en apartado y abono
  notas            TEXT                           -- nullable
  fecha            TEXT     NOT NULL              -- ISO 8601
```

Toda operación genera un registro en `movimientos`.
Las relaciones con `clientes` e `inventario` son opcionales según el tipo de operación.
La fuente de verdad completa del modelo está en `docs/REGLAS_NEGOCIO.md`.

---

## Versionado

| Versión | Alcance                                                        | Estado     |
|---------|----------------------------------------------------------------|------------|
| v0.1    | MVP: clientes, panel de operaciones, consulta                  | En curso   |
| v0.2    | Piso de Venta + integración inventario (spreadsheet → DB)      | Pendiente  |
| v0.3    | Devoluciones, préstamos de exhibición, operaciones especiales  | Pendiente  |
| v1.0    | Sistema estable, probado en operación real                     | Pendiente  |

El versionado sigue [Semantic Versioning](https://semver.org/lang/es/).
Cada versión se ramifica desde `main` como `release/vX.X`.

---

## Contribución

```bash
# Clonar el repositorio
git clone https://github.com/<org>/pos-boutique.git
cd pos-boutique

# Crear rama de trabajo
git checkout -b feature/nombre-de-la-funcionalidad

# Al terminar
git push origin feature/nombre-de-la-funcionalidad
# Abrir Pull Request hacia main
```

Convenciones de commits:

```
feat:     nueva funcionalidad
fix:      corrección de bug
docs:     cambios en documentación
refactor: reestructura sin cambio de comportamiento
chore:    tareas de mantenimiento (deps, config)
```

---

## Estado actual

- [x] Repositorio creado
- [x] Estructura de carpetas
- [x] venv backend
- [x] Dependencias backend (`requirements.txt`)
- [x] Modelos ORM (`models.py`) — 5 tablas + enums
- [x] Base de datos SQLite (`pos.db`) — tablas creadas
- [ ] Modelos ORM actualizados a patrones modernos (lifespan, DeclarativeBase)
- [ ] Schemas Pydantic (`schemas/`)
- [ ] Configuración centralizada (`core/config.py`, `.env`)
- [ ] CORS middleware
- [ ] Alembic inicializado y primera migración
- [ ] Endpoints API REST (`api/v1/endpoints/`)
- [ ] Servicios de lógica de negocio (`services/`)
- [ ] Frontend inicializado (`npm create vite`)
- [ ] Tests
