# Spec de Stack — Espejo Android

> **Qué es este documento:** define la arquitectura técnica, el stack y el alcance
> funcional del espejo Android de `pos-boutique`. No reemplaza a `ARQUITECTURA.md`
> (que describe el sistema principal) — lo extiende con la capa de acceso móvil.
>
> **Contexto:** el sistema actual es local, corre en una PC con SQLite en archivo.
> El cliente necesita operar módulos del POS desde dispositivos Android (smartphone
> o tableta) cuando la PC no está disponible — particularmente para consultar saldos
> y cambiar `estatus_articulo` de `vigente` a `en_almacen` al recibir mercancía.
> La solución debe contemplar al menos **2 equipos Android** operando simultáneamente.

---

## 1. Decisión de arquitectura

### Problema

La PC no siempre está disponible al momento de recibir mercancía (`vigente` →
`en_almacen`). Se necesita un segundo punto de acceso al sistema desde Android,
sin duplicar la base de datos ni introducir conflictos de escritura.

### Opciones evaluadas

| Opción | Stack | Pros | Contras |
|---|---|---|---|
| **A. PWA sobre LAN** | React + Vite (misma app web), FastAPI expuesto en red local | Cero código nativo Android. Una sola base de código frontend. Instalable como app desde el navegador. | Requiere WiFi. Sin acceso offline real. |
| B. App nativa (Kotlin) | Android Studio + Kotlin + Retrofit | Acceso a APIs nativas. | Stack nuevo, curva de aprendizaje alta, doble mantenimiento. |
| C. React Native / Expo | TypeScript + Expo | Comparte lenguaje con el frontend web. | Proyecto separado, dependencias nativas, setup complejo. |
| D. Offline-first con sync | SQLite local por dispositivo + sync bidireccional | Opera sin red. | Complejidad de resolución de conflictos, overhead de sincronización. |

### Decisión: **Opción A — PWA sobre LAN**

La app web de React (planificada pero no construida todavía) se diseña como
**Progressive Web App (PWA)** desde el inicio. El backend FastAPI se expone en la
red local (WiFi del negocio) y los dispositivos Android acceden a la misma URL que
la PC — es el mismo frontend, la misma base de datos, las mismas APIs.

**Justificación:**

1. **Cero código nativo Android.** Elimina la curva de aprendizaje y el mantenimiento
   paralelo de un proyecto Android separado.
2. **Una sola base de código.** Toda mejora al frontend web se refleja automáticamente
   en los dispositivos Android.
3. **Instalable.** Las PWA se instalan como app desde Chrome en Android — icono en
   pantalla de inicio, pantalla completa, sin barra del navegador.
4. **Consistente con el stack existente.** React + TypeScript + Vite ya es la decisión
   del proyecto. Solo se agrega la configuración de PWA (`manifest.json` + Service Worker).
5. **Suficiente para el caso de uso.** El negocio opera con WiFi local. La operación
   crítica (cambio de estatus) es una escritura puntual que no requiere modo offline.

---

## 2. Cambios técnicos requeridos

### 2.1 Backend — Exponer FastAPI en red local

**Estado actual:** `uvicorn` corre en `localhost:8000` — solo accesible desde la PC.

**Cambio:** bind a `0.0.0.0` para que cualquier dispositivo en la misma red pueda
conectarse.

```bash
# Antes
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Después
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**CORS:** actualizar `app/main.py` para aceptar orígenes de la red local:

```python
# Antes
origins = ["http://localhost:5173"]

# Después
origins = [
    "http://localhost:5173",
    "http://192.168.*.*:5173",   # o usar regex / wildcard para la subred local
]
```

> La IP de la PC en la red local se obtiene con `ip addr` (Linux). Los dispositivos
> Android accederán a `http://<IP_PC>:5173` (frontend) y `http://<IP_PC>:8000` (API).

### 2.2 SQLite — Modo WAL para concurrencia

**Problema:** SQLite serializa las escrituras. Con 2-3 clientes escribiendo
simultáneamente (PC + Android), pueden ocurrir errores `SQLITE_BUSY`.

**Solución:** activar **WAL (Write-Ahead Logging)**. WAL permite lecturas concurrentes
y serializa escrituras sin bloquear lectores — suficiente para 2-3 dispositivos en un
negocio pequeño.

```python
# backend/app/db/database.py
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")  # 5 segundos de espera antes de fallar
    cursor.close()
```

> No es necesario migrar a PostgreSQL para el volumen de operación de este negocio.
> WAL + `busy_timeout` de 5 s son suficientes. Si en el futuro se escala a más
> dispositivos o se necesita acceso remoto fuera de la LAN, la migración a PostgreSQL
> es una opción sin cambio en el código de servicios (solo `DATABASE_URL`).

### 2.3 Frontend — Configuración PWA

El frontend React + Vite (pendiente de construir) debe incluir desde su creación:

**`manifest.json`:**

```json
{
  "name": "POS Boutique",
  "short_name": "POS",
  "description": "Sistema punto de venta",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#1a1a2e",
  "theme_color": "#16213e",
  "orientation": "portrait",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

**Service Worker:** registro básico para que Chrome permita la instalación como app.
No se implementa cache offline completo en esta versión — el dispositivo requiere
conexión WiFi para operar.

```typescript
// src/service-worker.ts (mínimo para instalabilidad)
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
```

**Plugin Vite:** usar `vite-plugin-pwa` para automatizar la generación del manifest
y el registro del Service Worker.

```bash
npm install -D vite-plugin-pwa
```

```typescript
// vite.config.ts
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: { /* ...manifest.json de arriba */ }
    })
  ]
});
```

### 2.4 Red local — Requisitos mínimos

| Requisito | Detalle |
|---|---|
| WiFi | Red local del negocio. Todos los dispositivos en la misma subred. |
| PC encendida | El backend corre en la PC. Si la PC está apagada, los Android no tienen acceso. |
| IP fija de la PC | Recomendado: asignar IP estática a la PC en el router, o usar hostname local (e.g. `pos-pc.local` vía mDNS/Avahi). |
| Puerto abierto | `8000` (API) y `5173` (frontend dev) o el puerto de producción. Sin firewall bloqueando en la LAN. |

---

## 3. Alcance funcional del espejo

### 3.1 Versión mínima (release 1)

La versión mínima cubre el caso de uso que motivó la implementación: **recibir
mercancía sin PC**.

| Funcionalidad | Módulo | Operaciones |
|---|---|---|
| Consulta de saldo | Clientes | Ver `no_cliente`, `nombre`, `saldo`, `estatus`, banderas |
| Cambio de estatus | Pedidos | `vigente` → `en_almacen` (carga saldo al cliente) |
| Consulta de saldo Shein | Shein | Ver `nombre`, `saldo`, `estatus` del `shein_cliente` |

> Es un subconjunto del frontend web. No se desarrolla ninguna pantalla nueva ni
> ninguna API nueva — se reutilizan los endpoints existentes. La diferencia es que
> el frontend se diseña responsive (mobile-first en estas vistas específicas).

### 3.2 Versión integral (release 2+)

Espejo completo de todos los módulos: Clientes, Pedidos, Inventario, Movimientos,
Shein, Recargas, Consulta Finanzas. Es la misma app web completa, adaptada para
pantallas Android.

> No hay diferencia técnica entre release 1 y release 2: ambos son la misma PWA. La
> diferencia es de priorización — en release 1 se construyen las vistas móviles
> mínimas; en release 2 se completa la responsive de todas las pantallas.

---

## 4. Flujo de instalación en Android

```
1. Conectar el dispositivo Android a la misma red WiFi del negocio.
2. Abrir Chrome y navegar a http://<IP_PC>:5173 (o el puerto de producción).
3. Chrome muestra el banner "Agregar a pantalla de inicio" (o acceder desde
   el menú ⋮ > "Instalar aplicación").
4. La app queda instalada como icono en pantalla de inicio.
5. Al abrir, se muestra en pantalla completa sin barra del navegador.
```

No requiere Play Store, cuenta de desarrollador de Google, ni APK.

---

## 5. Lo que NO incluye esta solución

| Exclusión | Razón |
|---|---|
| Modo offline | El caso de uso requiere datos en tiempo real (saldo actual, estatus). Cache offline introduciría riesgo de inconsistencia. Si en el futuro se necesita, se implementa con IndexedDB + cola de sincronización. |
| Acceso fuera de la LAN | No hay caso de uso. Si aparece, se resuelve con VPN o con migración a un backend en la nube. |
| App nativa en Play Store | Costo y complejidad innecesarios. La PWA cubre el caso de uso sin publicación en tienda. |
| Notificaciones push | No hay caso de uso actual. Las banderas son visuales al consultar, no alertas proactivas. |
| Autenticación biométrica | El sistema usa JWT con usuario/password. Suficiente para el contexto operativo. |

---

## 6. Diagrama de red

```
┌──────────────────────────────────────────────────┐
│                    Red WiFi local                │
│                                                  │
│   ┌──────────┐     ┌──────────┐    ┌──────────┐  │
│   │    PC    │     │ Android  │    │ Android  │  │
│   │ (server) │     │   #1     │    │   #2     │  │
│   │          │     │          │    │          │  │
│   │ FastAPI  │◄────│ Chrome   │    │ Chrome   │  │
│   │ :8000    │     │  PWA     │────►  PWA     │  │
│   │          │     │          │    │          │  │
│   │ Vite     │◄────│ :5173    │    │ :5173    │  │
│   │ :5173    │     └──────────┘    └──────────┘  │
│   │          │                                   │
│   │ pos.db   │  ← única fuente de verdad         │
│   │ (SQLite  │                                   │
│   │  WAL)    │                                   │
│   └──────────┘                                   │
└──────────────────────────────────────────────────┘
```

Todos los dispositivos consumen la misma API. No hay base de datos local en
los Android — todo pasa por el backend en la PC vía HTTP sobre la LAN.

---

## 7. Impacto en documentación existente

| Documento | Cambio necesario |
|---|---|
| `docs/ARQUITECTURA.md` | Agregar sección de acceso multi-dispositivo. Actualizar la afirmación de "sistema local, single-device". Documentar el bind a `0.0.0.0`, WAL mode, y la topología LAN. |
| `docs/REPORT.md` | Ya registrado en §5 Bloque F (tareas 31-33). |
| `docs/spec/README.md` | Agregar este documento al mapa de specs. |
| Frontend (por construir) | Diseñar responsive / mobile-first. Incluir configuración PWA desde el inicio. |
