# Debugging y Recuperación
## pos-boutique — Guía de diagnóstico y control de daños

> Cuando algo se rompe, no hay que adivinar.
> Hay que leer el error, ubicarlo en una capa y seguir el procedimiento.
> Este documento cubre los escenarios más comunes de este proyecto.

---

## Tabla de contenidos

- [Principio fundamental](#principio-fundamental)
- [Git como red de seguridad](#git-como-red-de-seguridad)
- [Mapa de capas y síntomas](#mapa-de-capas-y-síntomas)
- [Base de datos](#base-de-datos)
- [Backend FastAPI](#backend-fastapi)
- [Frontend React](#frontend-react)
- [Conexión frontend ↔ backend](#conexión-frontend--backend)
- [SSH y Tailscale](#ssh-y-tailscale)
- [Comandos de emergencia](#comandos-de-emergencia)

---

## Principio fundamental

Antes de tocar cualquier cosa que funciona:

```bash
git add .
git commit -m "checkpoint: antes de modificar X"
```

Un commit tarda 10 segundos. Revertir un error sin commit puede tardar horas.

---

## Git como red de seguridad

### Ver el historial de commits

```bash
git log --oneline
```

Ejemplo de output:
```
a3f2c1b feat: panel principal operaciones
9e1d4a2 chore: agrega alembic
3b7f8c0 chore: dependencias iniciales del backend
```

### Deshacer el último commit manteniendo los cambios

```bash
git reset --soft HEAD~1
```

> Útil cuando commiteaste algo incompleto. Los archivos quedan intactos.

### Revertir un commit sin borrar el historial

```bash
git revert HEAD
```

> Crea un commit nuevo que deshace el anterior. Es la forma segura en producción.

### Regresar exactamente a un commit específico

```bash
git checkout <hash_del_commit>
```

> Ejemplo: `git checkout a3f2c1b`
> Úsalo para inspeccionar. Para quedarte ahí permanentemente usa `git switch`.

### Sincronizar @envy después de un fix en @actuary

```bash
# En @envy vía SSH:
cd ~/pos-boutique
git pull https://magic-town@github.com/magic-town/pos-boutique.git main
sudo systemctl restart pos-boutique
```

---

## Mapa de capas y síntomas

Cuando algo falla, el error pertenece a una de estas tres capas:

```
┌─────────────────────────────────────────────────────────┐
│  SÍNTOMA                        CAPA                    │
├─────────────────────────────────────────────────────────┤
│  Pantalla rota, botón no responde   →  Frontend         │
│  Datos no cargan o aparecen vacíos  →  Conexión API     │
│  Error en terminal de uvicorn       →  Backend          │
│  Datos guardados incorrectamente    →  Lógica/Servicios │
│  "no such table" o datos perdidos   →  Base de datos    │
│  SSH no conecta                     →  Tailscale/Red    │
└─────────────────────────────────────────────────────────┘
```

---

## Base de datos

### Síntoma: "no such table"
La base de datos no tiene la tabla que el código espera.
Casi siempre es una migración sin aplicar.

```bash
cd ~/pos-boutique/backend
source venv/bin/activate
alembic upgrade head
```

### Síntoma: datos incorrectos o columna faltante
Se modificó un modelo pero no se generó la migración.

```bash
# Generar migración por el cambio detectado
alembic revision --autogenerate -m "describe el cambio"

# Aplicarla
alembic upgrade head
```

### Ver el historial de migraciones aplicadas

```bash
alembic history
alembic current
```

### Revertir la última migración

```bash
alembic downgrade -1
```

### Respaldar la base de datos manualmente

```bash
cp ~/pos-boutique/backend/pos.db ~/pos-boutique/backend/pos_backup_$(date +%Y%m%d).db
```

> Hazlo antes de cualquier migración en producción (@envy).
> El archivo `pos.db` contiene toda la historia del negocio.

---

## Backend FastAPI

### Levantar el servidor en modo desarrollo

```bash
cd ~/pos-boutique/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Ver logs en tiempo real (producción en @envy)

```bash
sudo journalctl -fu pos-boutique
```

### Síntoma: el servidor no arranca

Lee el error completo en la terminal. Los más comunes:

| Error | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError` | Falta una dependencia | `pip install -r requirements.txt` |
| `no such table` | Migración sin aplicar | `alembic upgrade head` |
| `Address already in use` | El puerto 8000 está ocupado | `sudo lsof -i :8000` y mata el proceso |
| `ImportError` | Error en un archivo Python | Lee la línea exacta del error |

### Probar la API sin el frontend

Abre en el navegador:
```
http://localhost:8000/docs
```

Desde ahí puedes ejecutar cualquier endpoint directamente.
Si funciona en `/docs` pero no en la interfaz → el problema es del frontend.
Si no funciona ni en `/docs` → el problema es del backend o la base de datos.

---

## Frontend React

### Levantar el servidor en desarrollo

```bash
cd ~/pos-boutique/frontend
npm run dev
```

### Síntoma: pantalla rota o componente no responde

1. Abre el navegador.
2. Presiona `F12` → pestaña **Console**.
3. Lee el error en rojo — te dice el archivo y la línea exacta.

### Síntoma: página en blanco después de un cambio

```bash
# Limpiar caché de Vite
cd ~/pos-boutique/frontend
rm -rf node_modules/.vite
npm run dev
```

### Síntoma: `npm: command not found`

```bash
# Verificar instalación de Node
node --version
npm --version

# Si no está instalado en @envy:
sudo apt install nodejs npm
```

---

## Conexión frontend ↔ backend

### Síntoma: datos no cargan, spinner infinito

1. Verifica que el backend está corriendo:
```bash
curl http://localhost:8000/docs
```

2. Abre `F12` → pestaña **Network** → busca la petición fallida.
3. Lee el código de error:

| Código | Significado | Dónde buscar |
|---|---|---|
| `404` | La ruta no existe en FastAPI | `backend/app/api/v1/endpoints/` |
| `422` | Datos inválidos enviados por el frontend | Revisa el formulario |
| `500` | Error interno del backend | Terminal de uvicorn |
| `CORS` | Frontend y backend no se reconocen | `backend/app/core/config.py` |
| `Failed to fetch` | El backend no está corriendo | Levanta uvicorn |

---

## SSH y Tailscale

### Verificar que Tailscale está activo

```bash
sudo tailscale status
```

### Reconectar Tailscale

```bash
sudo tailscale up
```

### SSH no conecta a @envy

```bash
# 1. Verificar que Tailscale corre en @envy
sudo tailscale status

# 2. Verificar que SSH está activo en @envy
sudo systemctl status ssh

# 3. Verificar que el firewall permite la conexión
sudo ufw status verbose

# 4. Intentar conexión con verbose para ver dónde falla
ssh -v gabriel@100.112.41.4
```

---

## Comandos de emergencia

### El sistema en @envy no responde y necesito reiniciarlo todo

```bash
# Vía SSH desde @actuary:
ssh gabriel@100.112.41.4

# Reiniciar el servicio del POS
sudo systemctl restart pos-boutique

# Si el servicio no existe aún, levantar manualmente:
cd ~/pos-boutique/backend
source venv/bin/activate
uvicorn app.main:app --port 8000 &

cd ~/pos-boutique/frontend
npm run preview &
```

### Respaldar todo antes de una actualización mayor

```bash
# En @envy vía SSH:
cp ~/pos-boutique/backend/pos.db ~/Dropbox/respaldos/pos_$(date +%Y%m%d).db
cd ~/pos-boutique && git log --oneline -5
```

### Revertir el sistema al último estado estable

```bash
# Ver commits disponibles
git log --oneline

# Regresar al commit que funcionaba
git revert HEAD

# Aplicar en base de datos si hubo migraciones
alembic downgrade -1

# Reiniciar
sudo systemctl restart pos-boutique
```

---

*Actualiza este documento cada vez que resuelvas un problema nuevo.*
*El mejor momento para documentar es inmediatamente después de resolver.*
