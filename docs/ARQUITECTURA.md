# ARQUITECTURA.md
## Guía de tripulación — pos-boutique

Este documento no es documentación técnica formal.
Es una guía escrita para alguien que sabe operar el negocio,
entiende SQL a nivel de queries, y necesita sostener este sistema
sin depender de nadie cuando algo falle o necesite crecer.

---

## 1. La pregunta más importante: ¿qué pasa cuando alguien registra un abono?

Antes de hablar de capas y tecnologías, entiende el flujo completo
de una operación real. Toma este ejemplo:

> La ejecutiva selecciona "Abono", elige a la clienta Sonia,
> escribe $200, selecciona "Efectivo" y presiona Guardar.

Esto es lo que ocurre por debajo:

```
1. El navegador (React) construye un mensaje:
   "Registra un abono de $200 en efectivo para la clienta con id 7"

2. Ese mensaje viaja por HTTP al backend (FastAPI):
   POST http://localhost:8000/api/v1/movimientos

3. FastAPI recibe el mensaje, valida que los datos estén completos
   y correctos (Pydantic), y ejecuta la lógica de negocio:
   - ¿Existe la clienta con id 7? → consulta Clientes
   - ¿El monto es positivo? → validación
   - Calcula el saldo resultante

4. SQLAlchemy traduce la operación a SQL y escribe en SQLite:
   INSERT INTO movimientos (operacion, id_cliente, monto, ...) VALUES (...)
   UPDATE clientes SET saldo = saldo - 200 WHERE id_cliente = 7

5. SQLite confirma que escribió sin errores.

6. FastAPI responde al navegador:
   "Operación registrada. Saldo actual: $1,450"

7. React actualiza la pantalla con el nuevo saldo.
```

Todo eso ocurre en menos de un segundo.
Si algo falla, ocurre en uno de esos 7 pasos — y cada uno tiene síntomas distintos.

---

## 2. Las tres capas del sistema

Piensa en el sistema como una tienda con tres áreas:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    MOSTRADOR    │     │   BODEGA/CAJA   │     │    ARCHIVO      │
│                 │     │                 │     │                 │
│  React + Vite   │────▶│    FastAPI      │────▶│    SQLite       │
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

*Este documento crece con el proyecto.
Cada vez que resuelvas un problema que no estaba documentado aquí, agrégalo.*
