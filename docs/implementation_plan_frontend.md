# Plan de Implementación: Fase 0 - Scaffolding del Frontend

Basado en el `ROADMAP_FRONTEND.md`, el siguiente paso es inicializar el proyecto frontend. Antes de proceder con la ejecución técnica, necesitamos resolver algunos huecos de especificación para asegurar que la implementación vaya en la dirección correcta.

## User Review Required

Se requiere aprobación para ejecutar los siguientes comandos y configurar la base del proyecto en la carpeta `frontend/`:
- Inicializar el proyecto con Vite (`React` + `TypeScript`).
- Instalar dependencias base: `react-router-dom`, `react-hook-form`, `zod`, `@tanstack/react-query`, `@hookform/resolvers`, `lucide-react` (para íconos).
- Configurar la estructura de carpetas sugerida (`src/api`, `src/components`, `src/pages`, `src/hooks`, `src/utils`).
- Configurar el cliente API base (wrapper sobre `fetch`) y el contexto de autenticación (`AuthContext`).

> [!CAUTION]
> El scaffolding creará la carpeta `frontend/` en la raíz del proyecto e instalará múltiples dependencias de Node.js.

## Open Questions

Por favor, ayúdame a resolver las siguientes dudas identificadas en el análisis previo antes o durante esta fase:

> [!IMPORTANT]
> **1. Especificación de Consulta Global (`module_consulta.md`):** El reporte dice que la especificación está completa, pero el archivo no existe. ¿Nos basamos únicamente en lo descrito en `REGLAS_NEGOCIO.md` §10 para construir esta vista, o existe un archivo faltante que deba revisar?

> [!IMPORTANT]
> **2. Identidad Visual:** No hay mención sobre colores de marca, logo o tipografía en la documentación. Para configurar el sistema de diseño (CSS / tokens) desde el principio, ¿qué paleta de colores (ej. tonos oscuros/claros, color principal) y tipografía deberíamos usar? Si no hay una definida, ¿puedo proponer una estética moderna y profesional?

> [!WARNING]
> **3. Endpoints faltantes (Apartado y Consulta Global):** El backend actual no expone el endpoint para registrar un apartado (solo existe en la capa de servicio) ni los de Consulta Global. ¿Prefieres que desarrolle y exponga estos endpoints en el backend primero, o avanzamos armando el frontend con mock data / dejando pendiente la integración de esas vistas?

## Proposed Changes

### frontend/

#### [NEW] [package.json](file:///home/gabriel/pos-boutique/frontend/package.json)
Configuración del proyecto Vite con React, TypeScript y dependencias transversales.

#### [NEW] [src/styles/index.css](file:///home/gabriel/pos-boutique/frontend/src/styles/index.css)
Archivo CSS global con variables de diseño (colores, tipografía, espaciado) derivadas de la identidad visual acordada.

#### [NEW] [src/api/client.ts](file:///home/gabriel/pos-boutique/frontend/src/api/client.ts)
Wrapper de fetch que inyecta el JWT y maneja redirecciones automáticas ante errores 401.

#### [NEW] [src/context/AuthContext.tsx](file:///home/gabriel/pos-boutique/frontend/src/context/AuthContext.tsx)
Contexto de React para manejar el estado global de la sesión del usuario (token, login, logout).

#### [NEW] [src/App.tsx](file:///home/gabriel/pos-boutique/frontend/src/App.tsx)
Configuración de `react-router-dom` con las rutas protegidas y la ruta pública de `/login`.

#### [NEW] [src/pages/Login.tsx](file:///home/gabriel/pos-boutique/frontend/src/pages/Login.tsx)
Pantalla de inicio de sesión inicial que se comunicará con `POST /api/v1/auth/login`.

## Verification Plan

### Manual Verification
- Iniciar el servidor de desarrollo (`npm run dev`) dentro de `frontend/`.
- Verificar que la ruta raíz (`/`) redirige a `/login` si no hay sesión.
- Validar el flujo de autenticación introduciendo credenciales correctas (de los seeders) y verificando que el token se guarda en el contexto y se redirige al panel principal (que por ahora estará vacío).
