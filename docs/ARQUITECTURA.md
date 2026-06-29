# ARQUITECTURA.md
## Guía de tripulación — pos-boutique

Este documento no es documentación técnica formal. Es una guía para alguien que sabe operar el negocio, entiende SQL a nivel de queries, y necesita sostener este sistema sin depender de alguien cuando algo falle o necesite crecer.

---

## 1. La pregunta más importante: ¿qué pasa cuando alguien registra un abono?

Antes de hablar de capas y tecnologías, entiende el flujo completo de una operación real. Toma este ejemplo:

> La ejecutiva selecciona `abono` seguido del respectivo `cliente`,
> Captura  `monto` seguido por `forma de pago` y da `Guardar`.

Esto es lo que ocurre por debajo:

1. El navegador (React) construye un mensaje:
   "Registra un abono `$X` en `forma de pago` para la clienta `ID-XX"

2. Ese mensaje viaja por HTTP al backend (FastAPI):
   POST http://localhost:8000/api/v1/movimientos

3. FastAPI recibe el mensaje, valida que los datos estén completos
   y correctos (Pydantic), y ejecuta la lógica de negocio:
   - ¿Existe la clienta con `ID-XX`? → consulta `Clientes`
   - ¿El monto es positivo? → validación
   - Calcula el saldo resultante

4. SQLAlchemy traduce la operación a SQL y escribe en SQLite:
   INSERT INTO movimientos (operacion, id_cliente, monto, ...) VALUES (...)
   UPDATE clientes SET saldo = saldo - `$X` WHERE id_cliente = `ID-XX`

5. SQLite confirma que escribió sin errores.

6. FastAPI responde al navegador:
   "Operación registrada. Saldo actual: `$Y`"

7. React actualiza la pantalla con el nuevo `saldo`.


Todo eso ocurre en menos de un segundo.
Si algo falla, ocurre en uno de esos 7 pasos — y cada uno tiene síntomas distintos.

---

## 2. Las tres capas del sistema

Piensa en el sistema como una tienda con tres áreas:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    MOSTRADOR    │     │   BODEGA/CAJA   │     │    ARCHIVO      │
│                 │     │                 │     │                 │
│  React + Vite   │───▶│    FastAPI      │───▶│    SQLite       │
│                 │     │                 │     │                 │
│  Lo que ve y    │     │  Lógica y       │     │  Donde viven    │
│  toca la        │     │  reglas del     │     │  los datos      │
│  ejecutiva      │     │  negocio        │     │  permanentes    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
   Puerto 5173              Puerto 8000            archivo pos.db
```

### El Mostrador (React + Vite)
- Vive en el navegador. No tiene datos propios — los pide al backend.
- Su único trabajo: mostrar información y capturar lo que escribe la ejecutiva.
- Si el backend está caído, el mostrador se ve pero no funciona.
- Los archivos que lo componen están en `frontend/src/`.

### La Bodega/Caja (FastAPI)
- Es el cerebro. Aquí viven las reglas de negocio.
- Nunca habla directamente con el navegador sobre datos crudos —
  siempre valida primero.
- Si un dato llega mal formado (monto negativo, cliente inexistente),
  FastAPI lo rechaza antes de tocar la base de datos.
- Los archivos que lo componen están en `backend/app/`.

### El Archivo (SQLite)
- Es un solo archivo en disco: `pos.db`.
- No es un servidor — es un archivo que SQLAlchemy abre y cierra.
- Toda la historia del negocio vive aquí: clientes, movimientos, pedidos.
- Si este archivo se corrompe o se borra, se pierden los datos.
  **Respáldalo con frecuencia — es copiar y pegar un archivo.**

### El Panel Principal — la pantalla de operación diaria

El Panel Principal es la pantalla que la ejecutiva ve todo el día. Funciona
como caja registradora: siempre visible, siempre disponible.

Cada operación que se registra aquí escribe en la tabla `movimientos`
y, dependiendo del tipo, dispara actualizaciones en otras tablas:

- **Contado** → registra venta de contado. Si el artículo viene de inventario,
  actualiza `inventario.estatus`.
- **Apartado** → registra apartado para una clienta. Actualiza `clientes.saldo`
  y, si aplica, `inventario.estatus`.
- **Abono** → registra pago parcial. Actualiza `clientes.saldo`.
- **Gasto** → registra salida de efectivo (no afecta clientes ni inventario).

Todo lo que pasa por el Panel Principal queda en `movimientos` — es el
registro central de operaciones del negocio.

---

## 3. Por qué dos puertos (5173 y 8000)

Cuando abres el sistema en el navegador, en realidad hay dos servidores
corriendo al mismo tiempo en la misma PC:

```
http://localhost:5173  →  servidor del frontend (Vite)
http://localhost:8000  →  servidor del backend (Uvicorn + FastAPI)
```

El frontend corre en 5173 porque Vite lo levanta ahí por defecto.
El backend corre en 8000 porque Uvicorn lo levanta ahí por defecto.

Cuando React necesita datos, hace una petición de 5173 → 8000.
Eso se llama CORS (Cross-Origin Resource Sharing) y es la razón por la
que en el backend hay una configuración que dice explícitamente:
"acepto peticiones que vengan del puerto 5173".

Si ves un error que dice "CORS" o "blocked by CORS policy",
significa que el frontend y el backend no se están reconociendo entre sí.
La solución siempre está en la configuración CORS del backend.

---

## 4. SQLAlchemy: por qué no escribimos SQL directo

Ya sabes escribir queries SQL. Entonces ¿por qué usar SQLAlchemy?

Tres razones concretas para este proyecto:

**a) Las tablas son clases Python**
En lugar de recordar la estructura exacta de cada tabla,
defines una clase y SQLAlchemy se encarga del resto:

```python
# Esto en Python:
class Cliente(Base):
    id_cliente = Column(Integer, primary_key=True)
    nombre     = Column(String, nullable=False)
    colonia    = Column(String)
    telefono   = Column(String)

# Genera esto en SQL:
# CREATE TABLE clientes (
#   id_cliente INTEGER PRIMARY KEY,
#   nombre     TEXT NOT NULL,
#   colonia    TEXT,
#   telefono   TEXT
# )
```

Si cambias la clase, cambias la tabla. Un solo lugar de verdad.

**b) Las relaciones se declaran una vez**
Cuando quieres todos los movimientos de una clienta:

```python
# Sin SQLAlchemy (SQL directo):
SELECT * FROM movimientos WHERE id_cliente = 7

# Con SQLAlchemy (desde el objeto):
cliente.movimientos   # ← ya están ahí, sin escribir el query
```

**c) Te protege de errores comunes**
SQLAlchemy escapa automáticamente los valores para prevenir
inyección SQL — algo crítico cuando los datos vienen de un formulario.

---

## 5. Alembic: el control de versiones de tu base de datos

Imagina que el sistema ya está corriendo en la PC de la ejecutiva
y decides agregar un campo nuevo a la tabla Clientes: `fecha_registro`.

Si solo cambias el modelo Python, la base de datos real no sabe nada.
El sistema rompe porque el código espera una columna que no existe.

Alembic resuelve esto. Funciona así:

```
1. Modificas el modelo Python (agregas el campo)
2. Ejecutas: alembic revision --autogenerate -m "agrega fecha_registro"
3. Alembic detecta la diferencia y genera un script SQL automáticamente
4. Ejecutas: alembic upgrade head
5. La base de datos se actualiza sin perder datos
```

Regla práctica:
- Cada vez que cambies un modelo → genera una migración con Alembic.
- Nunca modifiques `pos.db` directamente con SQL para cambiar estructura.
- Las migraciones son el historial de cómo evolucionó tu base de datos.

---

## 6. Dónde buscar cuando algo no funciona

### La pantalla se ve rara o un botón no responde
→ Problema en el frontend.
→ Abre el navegador, presiona F12, ve a la pestaña "Console".
→ Los errores en rojo te dicen exactamente qué componente falló.

### La pantalla carga pero los datos no aparecen o aparecen vacíos
→ El frontend no está recibiendo respuesta del backend.
→ F12 → pestaña "Network" → busca la petición en rojo.
→ El código de error te orienta:
   - 404: la ruta no existe en FastAPI
   - 422: los datos que mandó el frontend no pasaron validación
   - 500: el backend tiene un error interno (revisa la terminal donde corre uvicorn)
   - "Failed to fetch": el backend no está corriendo

### El backend arranca y luego se cae
→ Lee el error en la terminal donde ejecutaste `uvicorn`.
→ Si dice "no such table": falta correr las migraciones (`alembic upgrade head`).
→ Si dice "cannot import": falta instalar una dependencia (`pip install X`).

### Los datos se guardan pero están mal
→ Problema en la lógica de negocio dentro de FastAPI (`backend/app/services/`).
→ Revisa la función que maneja esa operación.
→ La documentación automática de FastAPI (`http://localhost:8000/docs`)
   te permite probar cada endpoint directamente sin tocar el frontend.

---

## 7. La herramienta que más vas a usar para diagnosticar

FastAPI genera documentación interactiva automáticamente:

```
http://localhost:8000/docs
```

Desde ahí puedes ejecutar cualquier operación de la API directamente
en el navegador, sin que el frontend esté involucrado. Si una operación
funciona en `/docs` pero no en la interfaz, el problema es del frontend.
Si no funciona ni en `/docs`, el problema es del backend o la base de datos.

Es tu primer punto de diagnóstico siempre.

---

## 8. Cómo escala este sistema

El MVP corre todo en una sola PC. Si en el futuro necesitas que
el sistema sea accesible desde otro dispositivo o desde internet,
los cambios son mínimos porque la arquitectura ya está separada:

```
MVP (todo local):
  PC ejecutiva corre frontend + backend + SQLite

v2 (red local, otra PC):
  PC ejecutiva corre backend + SQLite
  Cualquier PC en la misma red accede al frontend por IP local

v3 (nube):
  Backend sube a un servidor (Railway, Render, DigitalOcean)
  SQLite migra a PostgreSQL (el código cambia mínimo — solo la conexión)
  Frontend sube a Vercel o Netlify
  Accesible desde cualquier dispositivo con internet
```

Los cambios de MVP a v3 no requieren reescribir el sistema.
Requieren cambiar configuración y una cadena de conexión.
Eso es exactamente lo que significa "escalable" en este contexto.

---

## 9. Los tres comandos que más vas a usar

```bash
# Levantar el backend
cd ~/pos-boutique/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Levantar el frontend
cd ~/pos-boutique/frontend
npm run dev

# Aplicar cambios a la base de datos
cd ~/pos-boutique/backend
alembic upgrade head
```

Si el sistema no responde, estos tres comandos y sus outputs
son el primer lugar donde buscar.

---

## 10. Lo que no necesitas saber para sostener este proyecto

- Triggers y stored procedures → la lógica vive en Python, no en la base de datos.
- Configuración avanzada de PostgreSQL → SQLite no tiene servidor que configurar.
- DevOps y contenedores (Docker) → el despliegue es directo, sin capas adicionales.
- Webpack o configuración de bundlers → Vite maneja todo esto por defecto.

Si en algún momento necesitas alguno de estos temas,
es porque el sistema creció y ese es el momento correcto para aprenderlo.

---

## 11. Acceso al sistema — login y usuarios

El sistema incluye autenticación con usuario y contraseña.
En el MVP la autenticación está **deshabilitada por defecto** para agilizar
el desarrollo. Se controla con la variable `AUTH_ENABLED` en
`backend/core/config.py` (`False` en desarrollo, `True` en producción).

Cuando está habilitada, así funciona por dentro:

1. La ejecutiva escribe su usuario y contraseña en la pantalla de login.
2. El backend verifica que el usuario existe y que la contraseña es correcta.
3. Si todo está bien, el backend genera un **token** — un pase temporal
   que dura 8 horas (una jornada laboral).
4. El frontend guarda ese token y lo adjunta a cada operación que realiza.
5. Si el token expira o es inválido, el sistema pide login de nuevo.

El sistema nace con dos usuarios: `sonia` y `operador2`.
Ambos tienen rol `estandar`. En versiones futuras existirá un rol `admin`
con permisos adicionales (cancelar movimientos históricos, gestionar usuarios).

Si necesitas cambiar una contraseña o agregar un usuario, se hace
directamente desde la terminal — no hay interfaz de administración en el MVP.

> Corregido: usuarios iniciales actualizados a `sonia` y `operador2` según FULL_STACK_DEVELOPMENT.md.

---

## 12. Las tablas del sistema

El sistema utiliza 11 tablas en SQLite:

| Tabla | Módulo | Qué guarda |
|---|---|---|
| `clientes` | Clientes | Cartera de clientes de crédito con saldo y frecuencia de pago |
| `pedidos` | Pedidos | Cabecera de pedidos de catálogo (formal e informal) |
| `pedidos_articulos` | Pedidos | Artículos por pedido (1–4), con principal y alternativa |
| `inventario` | Inventario | Stock físico en piso de venta con estatus y precios |
| `movimientos` | Panel Principal | Registro de todas las operaciones de caja |
| `shein_clientes` | Shein | Clientes transaccionales de Shein (independiente de `clientes`) |
| `shein_pedidos` | Shein | Pedidos vía app Shein con monto y corte |
| `shein_cortes` | Shein | Cortes periódicos con bono por volumen |
| `recargas` | Recargas | Registro de recargas telefónicas |
| `usuarios` | Autenticación | Usuarios del sistema con hash bcrypt |
| `configuracion` | Setting | Configuración clave-valor del sistema |

> Nuevo: resumen de tablas del sistema según FULL_STACK_DEVELOPMENT.md.

---

*Este documento crece con el proyecto.
Cada vez que resuelvas un problema que no estaba documentado aquí, agrégalo.*

