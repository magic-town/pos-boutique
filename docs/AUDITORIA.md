# AUDITORÍA DE ESTADO REAL DEL PROYECTO
Fecha: 2026-06-28
Fuente de verdad: docs/00_FULLSTACK_DEVELOPMENT.md

## 1. Resumen ejecutivo
El proyecto presenta un avance real funcional estimado en un **10%** respecto a la especificación maestra de la boutique local y un **0%** de cobertura de pruebas automatizadas. La brecha principal radica en que el backend fue construido sobre un diseño obsoleto de base de datos plana (derivado de `REGLAS_NEGOCIO.md`), omitiendo la relación cabecera-detalle de pedidos, la separación de clientes Shein, la lógica de recargas y la configuración de métodos de pago. Además, el frontend se encuentra completamente sin inicializar (0% de avance).

## 2. Consistencia documental (README / ARQUITECTURA / REGLAS_NEGOCIO vs spec maestra)

| Documento | Afirmación | Coincide con spec maestra | Contradice / Obsoleto / Falta |
| :--- | :--- | :--- | :--- |
| **README.md** | El modelo de datos consta de 11 tablas con campos y relaciones descritas. | Parcialmente. Los nombres de las tablas coinciden en su mayoría. | **Contradice**: Especifica tipos y nulabilidades incorrectas (ej. `ref_telefono` como TEXT en lugar de INTEGER, y `frecuencia_pago` nullable). Describe campos de `inventario` y `movimientos` obsoletos. |
| **README.md** | El frontend tiene una estructura ya definida de layouts, componentes base, hooks, store y services en el árbol del proyecto. | No. El frontend en disco está completamente vacío. | **Obsoleto/Falso**: El frontend no se ha inicializado ni contiene código alguno. |
| **README.md** | Pydantic schemas, configuración centralizada, CORS y Alembic están listos y completados (✅). | N/A (Estado de avance). | **Obsoleto**: Las estructuras reales en código están basadas en el diseño viejo, no en el de la especificación maestra. |
| **ARQUITECTURA.md** | El sistema tiene 11 tablas con relaciones como `Empresa 1->N Sucursal`, `Empresa 1->N Usuario` y roles corporativos (`GERENTE`, `CAJERO`). | **No coincide en absoluto**. La spec maestra no tiene conceptos multi-empresa ni multi-sucursal. | **Contradice radicalmente**: Introduce un alcance corporativo (tablas `empresas`, `sucursales`, `impuestos` y FKs `empresa_id`) ajeno al diseño local de la spec maestra. |
| **ARQUITECTURA.md** | SQLite se accede de forma asíncrona mediante `aiosqlite`. | No. | **Contradice**: El código en [database.py](file:///home/gabriel/pos-boutique/backend/app/db/database.py#L5-L8) usa SQLAlchemy síncrono. |
| **REGLAS_NEGOCIO.md** | La tabla `pedidos` es una estructura plana donde cada fila es un producto con columnas opcionales. | No. | **Contradice/Obsoleto**: La spec maestra exige una estructura cabecera-detalle (`pedidos` y `pedidos_articulos`) para permitir múltiples artículos. |
| **REGLAS_NEGOCIO.md** | El módulo Shein vincula los pedidos al cliente general de la boutique. | No. | **Contradice/Obsoleto**: La spec maestra exige una tabla separada `shein_clientes` para no mezclar saldos de crédito con compras al contado de Shein. |
| **REGLAS_NEGOCIO.md** | El estatus de los clientes maneja tres estados: `activo`, `liquidado`, `rehabilitar`. | No. | **Contradice/Obsoleto**: La spec maestra simplifica los estados a `activo` e `inactivo`, y aclara que `saldo = 0` no provoca baja automática del cliente. |
| **REGLAS_NEGOCIO.md** | El módulo de Piso de Venta / Inventario no está activo en el MVP (v0.1) y se difiere a la v0.2. | No. | **Contradice**: La spec maestra incluye el módulo de Inventario y el cambio de estatus de productos como alcance mandatorio del MVP. |
| **REGLAS_NEGOCIO.md** | Muestra en su tabla de avances que Pydantic schemas, servicios, CORS y Alembic están pendientes (🔲). | N/A (Estado de avance). | **Contradice**: Contradice a `README.md` que afirma que ya están completados. |

## 3. Tabla de entidades/tablas

| Entidad | En spec maestra | Modelo | Migración | Schema | Endpoint | Test | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **clientes** | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L77`) | Sí, [models.py:L28](file:///home/gabriel/pos-boutique/backend/app/models/models.py#L28) | Sí, [38241ae2061c_esquema_inicial0.py#L28](file:///home/gabriel/pos-boutique/backend/alembic/versions/38241ae2061c_esquema_inicial0.py) | Sí, [cliente.py:L4](file:///home/gabriel/pos-boutique/backend/app/schemas/cliente.py#L4) | Sí, [clientes.py:L11](file:///home/gabriel/pos-boutique/backend/app/api/v1/endpoints/clientes.py#L11) | No | 🟡 PARCIAL (Faltan columnas `frecuencia_pago` y `fecha_pago_programada` en modelo, base de datos y esquemas, y no tiene pruebas) |
| **pedidos** (Cabecera) | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L521`) | No | No | No | No | No | 🔴 NO IMPLEMENTADO (La estructura real en base de datos es plana/obsoleta) |
| **pedidos_articulos** (Líneas) | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L534`) | No | No | No | No | No | 🔴 NO IMPLEMENTADO |
| **inventario** | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L334`) | Sí, [models.py:L48](file:///home/gabriel/pos-boutique/backend/app/models/models.py#L48) | Sí, [38241ae2061c_esquema_inicial0.py#L40](file:///home/gabriel/pos-boutique/backend/alembic/versions/38241ae2061c_esquema_inicial0.py) | No | No | No | 🔴 NO IMPLEMENTADO (Falta toda la lógica de negocio, esquemas y endpoints, y el modelo está desalineado) |
| **movimientos** | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L1552`) | Sí, [models.py:L97](file:///home/gabriel/pos-boutique/backend/app/models/models.py#L97) | Sí, [38241ae2061c_esquema_inicial0.py#L76](file:///home/gabriel/pos-boutique/backend/alembic/versions/38241ae2061c_esquema_inicial0.py) | Sí, [movimiento.py:L8](file:///home/gabriel/pos-boutique/backend/app/schemas/movimiento.py#L8) | Sí, [movimientos.py:L11](file:///home/gabriel/pos-boutique/backend/app/api/v1/endpoints/movimientos.py#L11) | No | 🟡 PARCIAL (Usa columna `notas` en lugar de `descripcion` y no tiene pruebas) |
| **shein_clientes** | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L1734`) | No | No | No | No | No | 🔴 NO IMPLEMENTADO |
| **shein_pedidos** | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L1746`) | No | No | No | No | No | 🔴 NO IMPLEMENTADO (El modelo `PedidoShein` en [models.py:L85](file:///home/gabriel/pos-boutique/backend/app/models/models.py#L85) es obsoleto y apunta a `clientes` general) |
| **shein_cortes** | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L1764`) | No | No | No | No | No | 🔴 NO IMPLEMENTADO |
| **recargas** | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L1982`) | No | No | No | No | No | 🔴 NO IMPLEMENTADO |
| **usuarios** | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L2090`) | Sí, [models.py:L114](file:///home/gabriel/pos-boutique/backend/app/models/models.py#L114) | Sí, [97592862ac88_agregar_tabla_usuarios.py#L10](file:///home/gabriel/pos-boutique/backend/alembic/versions/97592862ac88_agregar_tabla_usuarios.py) | Sí, [usuario.py:L14](file:///home/gabriel/pos-boutique/backend/app/schemas/usuario.py#L14) | Parcial | No | 🟡 PARCIAL (Solo implementa login en [auth.py:L11](file:///home/gabriel/pos-boutique/backend/app/api/v1/endpoints/auth.py#L11), faltan endpoints CRUD y no tiene pruebas) |
| **configuracion** | Sí (`docs/00_FULLSTACK_DEVELOPMENT.md#L2132`) | No | No | No | No | No | 🔴 NO IMPLEMENTADO |

## 4. Tabla de endpoints / casos de uso

| Endpoint o caso de uso | En spec maestra | Implementado | Cumple regla de negocio | Test | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Registrar Cliente** | Sí | Sí, [clientes.py:L11](file:///home/gabriel/pos-boutique/backend/app/api/v1/endpoints/clientes.py#L11) | Parcialmente (Genera `no_cliente` automático en [cliente_service.py:L7](file:///home/gabriel/pos-boutique/backend/app/services/cliente_service.py#L7), pero no guarda `frecuencia_pago` ni `fecha_pago_programada`) | No | 🟡 PARCIAL |
| **Editar Cliente** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Consulta Cliente** | Sí | Sí, [clientes.py:L22](file:///home/gabriel/pos-boutique/backend/app/api/v1/endpoints/clientes.py#L22) | Sí | No | 🟡 PARCIAL |
| **Consulta Historial (Clientes)** | Sí | No | No | No | 🔴 NO IMPLEMENTADO (No existe un endpoint que consolide pedidos y movimientos de forma cronológica descendente) |
| **Registrar Pedido (Múltiples artículos)** | Sí | No | No. El endpoint actual [pedidos.py:L11](file:///home/gabriel/pos-boutique/backend/app/api/v1/endpoints/pedidos.py#L11) es plano (modelo obsoleto) y no soporta de 1 a 4 artículos, principal/alternativa ni estatus `vigente`. | No | 🔴 NO IMPLEMENTADO |
| **Registrar Devolución (Pedidos)** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Cancelar Artículo (Pedidos)** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Lista de Surtido** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Agregar Producto (Inventario)** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Cambiar Estatus (Inventario)** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Consulta Inventario** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Contado - Catálogo (Panel Principal)** | Sí | Sí, [movimientos.py:L11](file:///home/gabriel/pos-boutique/backend/app/api/v1/endpoints/movimientos.py#L11) | Sí (vía [movimiento_service.py:L7](file:///home/gabriel/pos-boutique/backend/app/services/movimiento_service.py#L7)) | No | 🟡 PARCIAL |
| **Contado - Inventario (Panel Principal)** | Sí | No | No (el servicio no descuenta stock ni actualiza estatus en la tabla `inventario`) | No | 🔴 NO IMPLEMENTADO |
| **Apartado (Panel Principal)** | Sí | Parcial | No. [movimiento_service.py:L28](file:///home/gabriel/pos-boutique/backend/app/services/movimiento_service.py#L28) sobrescribe el saldo (`cliente.saldo = saldo_resultante`) en lugar de sumarlo (`cliente.saldo += monto`), no valida el pago mínimo de $100 y no altera el estatus en `inventario`. | No | 🔴 NO IMPLEMENTADO |
| **Abono (Panel Principal)** | Sí | Parcial | No. El servicio actualiza el estado a `"liquidado"` (obsoleto en la spec maestra) y no recalcula `fecha_pago_programada` al no existir la columna. | No | 🟡 PARCIAL |
| **Gasto (Panel Principal)** | Sí | Parcial | No (la descripción no se valida como obligatoria y el modelo usa el nombre de columna `notas`) | No | 🟡 PARCIAL |
| **Registrar Cliente Shein** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Registrar Pedido Shein** | Sí | No | No (el endpoint actual [pedidos_shein.py:L11](file:///home/gabriel/pos-boutique/backend/app/api/v1/endpoints/pedidos_shein.py#L11) usa el cliente general de boutique) | No | 🔴 NO IMPLEMENTADO |
| **Lista de Pedidos Shein** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Registrar Corte Shein** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Registro de Recarga Telefónica** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Consulta Totales (Recargas)** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Ventas Totales por Período** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Ventas por Segmento** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Cartera de Clientes** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Login (Autenticación)** | Sí | Sí, [auth.py:L11](file:///home/gabriel/pos-boutique/backend/app/api/v1/endpoints/auth.py#L11) | Sí | No | 🟡 PARCIAL |
| **Me (Autenticación)** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |
| **Configurar Métodos de Pago** | Sí | No | No | No | 🔴 NO IMPLEMENTADO |

## 5. Reglas de negocio

| Regla (según spec maestra) | Implementada | Archivo/función evidencia | Test | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Generación de `no_cliente`** | Sí | [cliente_service.py:L7](file:///home/gabriel/pos-boutique/backend/app/services/cliente_service.py#L7) (`generar_no_cliente`) | No | 🟡 PARCIAL (Riesgo de colisión si se elimina un cliente ya que usa un `COUNT` por colonia) |
| **Ciclo de `fecha_pago_programada`** | No | N/A (Falta columna en el modelo `Cliente`) | No | 🔴 NO IMPLEMENTADO |
| **Banderas de alerta de crédito (🔴/🟡)** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Corte en Lista de Surtido** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Carga de saldo al marcar `en_almacen`** | No | N/A (El saldo se carga erróneamente al crear apartados o pedidos planos) | No | 🔴 NO IMPLEMENTADO |
| **Lookup de precios en `tabla_precios`** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Reglas de Devolución de Pedido** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Reglas de Cancelación de Artículo** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Transiciones válidas en Inventario** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Pago mínimo de $100 en apartado** | No | N/A (No existe validación en [movimiento_service.py:L28](file:///home/gabriel/pos-boutique/backend/app/services/movimiento_service.py#L28)) | No | 🔴 NO IMPLEMENTADO |
| **Cambio a 'apartado' en layaway** | No | N/A (No se actualiza la tabla `inventario` en la transacción) | No | 🔴 NO IMPLEMENTADO |
| **Cancelación de Apartado** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Venta al contado de Inventario** | No | N/A (No decrementa stock ni actualiza estado) | No | 🔴 NO IMPLEMENTADO |
| **Validación de abono <= saldo** | Sí | [movimiento_service.py:L40](file:///home/gabriel/pos-boutique/backend/app/services/movimiento_service.py#L40) (`registrar_movimiento`) | No | 🟡 PARCIAL |
| **Simplificación de estatus cliente** | No | N/A (El servicio cambia el estatus a `"liquidado"`, estado obsoleto en la maestra) | No | 🔴 NO IMPLEMENTADO |
| **Solo cancelar el último movimiento** | Sí | [movimiento_service.py:L90](file:///home/gabriel/pos-boutique/backend/app/services/movimiento_service.py#L90) (`cancelar_movimiento`) | No | 🟡 PARCIAL |
| **Clientes de Shein independientes** | No | N/A (Se asocian a la tabla de clientes generales) | No | 🔴 NO IMPLEMENTADO |
| **Bono y diferencias Shein** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Recargas sin impacto en saldos** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Configuración dinámica de pagos** | No | N/A | No | 🔴 NO IMPLEMENTADO |
| **Script `importar_clientes.py`** | No | N/A (El archivo no existe en el directorio `scripts/`) | No | 🔴 NO IMPLEMENTADO |

## 6. Frontend

| Página/componente esperado en spec maestra | Existe | Conectado a backend | Estado |
| :--- | :--- | :--- | :--- |
| **Panel Principal (Layout / Caja)** | No | No | 🔴 NO IMPLEMENTADO |
| **Formulario Registrar Cliente** | No | No | 🔴 NO IMPLEMENTADO |
| **Formulario Editar Cliente** | No | No | 🔴 NO IMPLEMENTADO |
| **Consulta Cliente (Tabla)** | No | No | 🔴 NO IMPLEMENTADO |
| **Consulta Historial (Cronológico)** | No | No | 🔴 NO IMPLEMENTADO |
| **Registrar Pedido (1-4 artículos)** | No | No | 🔴 NO IMPLEMENTADO |
| **Registrar Devolución (2 pasos)** | No | No | 🔴 NO IMPLEMENTADO |
| **Cancelar Artículo (2 pasos)** | No | No | 🔴 NO IMPLEMENTADO |
| **Lista de Surtido (Corte)** | No | No | 🔴 NO IMPLEMENTADO |
| **Agregar Producto (Inventario)** | No | No | 🔴 NO IMPLEMENTADO |
| **Cambiar Estatus (Inventario)** | No | No | 🔴 NO IMPLEMENTADO |
| **Consulta Inventario (Filtros)** | No | No | 🔴 NO IMPLEMENTADO |
| **Registrar Cliente Shein** | No | No | 🔴 NO IMPLEMENTADO |
| **Registrar Pedido Shein** | No | No | 🔴 NO IMPLEMENTADO |
| **Lista de Pedidos Shein** | No | No | 🔴 NO IMPLEMENTADO |
| **Registrar Corte Shein** | No | No | 🔴 NO IMPLEMENTADO |
| **Registro de Recargas** | No | No | 🔴 NO IMPLEMENTADO |
| **Consultas Globales (3 pestañas)** | No | No | 🔴 NO IMPLEMENTADO |
| **Configuración (Settings)** | No | No | 🔴 NO IMPLEMENTADO |
| **Pantalla de Login** | No | No | 🔴 NO IMPLEMENTADO |

## 7. Brechas críticas (gap report)

### a) Brechas de código (falta implementar)
- **Base de Datos (Alembic)**:
  - Crear tabla `pedidos_articulos` e implementar relación cabecera-detalle con `pedidos` (descartando el esquema plano).
  - Agregar `frecuencia_pago` y `fecha_pago_programada` a la tabla `clientes`.
  - Crear tablas `shein_clientes`, `shein_pedidos` (modificando la vieja `pedidos_shein`), `shein_cortes`, `recargas` y `configuracion`.
  - Actualizar `inventario` con los campos `precio_descuento`, `tipo_producto`, `descripcion_ruta` y `changed_status`.
  - Renombrar campos para ajustarse a la spec maestra (ej. `notas` -> `descripcion` en `movimientos`, `username` -> `usuario` en `usuarios`).
- **Servicios Backend (Lógica de Negocio)**:
  - Implementar la lógica del ciclo de pagos y recalculación de `fecha_pago_programada` en cada abono.
  - Implementar la regla de carga de saldo al marcar como `en_almacen` en el surtido, y no al crear el pedido.
  - Validar el pago mínimo de $100.00 en layaway/apartados.
  - Sincronizar el estatus de `inventario` con las operaciones de apartado (layaway) y ventas al contado.
  - Implementar lógica de lookup de precios locales en `tabla_precios` para Price Shoes, Pakar, Cklass.
  - Implementar la lógica de cortes Shein y bonos por volumen de venta.
  - Desarrollar la lógica de consulta para las 3 vistas globales de reportes.
  - Crear el script de importación inicial `scripts/importar_clientes.py` con validaciones de unicidad de `no_cliente`.
- **API REST**:
  - Implementar endpoints para todas las operaciones de inventario, Shein, recargas, configuración, consultas globales y CRUD completo de usuarios.
- **Frontend**:
  - Inicializar el proyecto con Vite + React + TypeScript en el directorio `frontend/`.
  - Construir todo el Panel Principal multi-ventana y las 20 pantallas de la especificación.
- **Pruebas unitarias**:
  - Escribir todo el suite de pruebas en `backend/tests/` (actualmente vacío).

### b) Brechas documentales (README/ARQUITECTURA/REGLAS_NEGOCIO a corregir)
- **ARQUITECTURA.md**: Eliminar toda referencia multi-empresa/multi-sucursal (tablas `empresas`, `sucursales`, `impuestos` y FKs `empresa_id`). Corregir la referencia de SQLite asíncrono a síncrono.
- **REGLAS_NEGOCIO.md**: Descartar el modelo de base de datos plana para pedidos. Eliminar la vinculación de pedidos Shein a clientes generales. Simplificar el estatus de clientes a `activo/inactivo` (eliminando el estado `"liquidado"`).
- **README.md**: Actualizar el estado del checklist para reflejar que la API, schemas y servicios deben reestructurarse bajo el nuevo modelo.

## 8. Recomendación de orden de desarrollo

Para retomar el proyecto de forma segura, se aconseja seguir el orden lógico de dependencias de abajo hacia arriba:

1. **Reestructuración de Base de Datos y Modelos (Backend)**:
   - Crear y aplicar una nueva migración de Alembic que alinee las tablas (`clientes`, `pedidos`, `inventario`, `movimientos`, `usuarios`) con la especificación maestra y cree las 5 tablas faltantes (`pedidos_articulos`, `shein_clientes`, `shein_pedidos`, `shein_cortes`, `recargas`, `configuracion`).
2. **Servicios y Lógica de Negocio (Backend)**:
   - Modificar `cliente_service.py` y `movimiento_service.py` para corregir la sobrescritura del saldo en apartados, eliminar el estado obsoleto `"liquidado"`, validar el pago mínimo de $100 y calcular la `fecha_pago_programada` rodante.
   - Desarrollar `pedido_service.py` y la lógica de cabecera-detalle, devoluciones, cancelaciones y carga de saldo diferida al estado `en_almacen`.
   - Implementar los servicios de Shein (cortes/bonos), Inventario (cambio de estados controlados) y Recargas.
   - Desarrollar el script de importación `scripts/importar_clientes.py` y correr la migración inicial de la cartera de clientes.
3. **Endpoints y API REST (Backend)**:
   - Reemplazar los routers viejos por los correspondientes a la especificación maestra.
   - Configurar la autenticación JWT protegiendo los endpoints específicos.
   - Sembrar (seed) los dos usuarios iniciales requeridos (`sonia` y `operador2`).
4. **Implementación de Tests (Backend)**:
   - Crear el suite de pruebas en `backend/tests/` cubriendo los casos de cobros diferidos, cancelación de movimientos, límites de abonos, y validaciones de Shein.
5. **Inicialización y Desarrollo del Frontend**:
   - Inicializar el frontend con React + TypeScript y Vite. Servir como proxy local hacia el puerto 8000.
   - Diseñar y codificar las interfaces en orden:
     1. Login y Configuración.
     2. Módulo de Clientes e historial cronológico.
     3. Módulo de Inventario.
     4. Panel Principal (Caja) integrando Clientes e Inventario.
     5. Módulo de Pedidos (y su lista de surtido).
     6. Módulo de Shein (cortes) y Recargas.
6. **Pruebas de Integración y Despliegue**:
   - Validar de extremo a extremo y desplegar en la máquina local de producción (`sonia@envy`) montando los servicios correspondientes en systemd.

## 9. Documentos a reconciliar después de esta auditoría

- **[README.md](file:///home/gabriel/pos-boutique/README.md)**: Debe reescribirse para corregir el checklist de progreso técnico, eliminar el árbol de carpetas del frontend falso y actualizar la sección del modelo de datos de acuerdo a `docs/00_FULLSTACK_DEVELOPMENT.md`.
- **[ARQUITECTURA.md](file:///home/gabriel/pos-boutique/docs/ARQUITECTURA.md)**: Requiere reescritura total para eliminar la arquitectura multi-empresa/multi-sucursal (limpiar `empresas`, `sucursales`, `impuestos`), reflejar la conexión síncrona real a SQLite, y documentar el flujo cabecera-detalle de los pedidos.
- **[REGLAS_NEGOCIO.md](file:///home/gabriel/pos-boutique/docs/REGLAS_NEGOCIO.md)**: Debe reescribirse para reflejar el esquema cabecera-detalle, el estatus simplificado `activo/inactivo` de clientes, la separación de clientes Shein, la inclusión del inventario en el MVP, y alinear las reglas del apartado (layaway) con las validaciones de pago mínimo de $100.
- **[CHECKLIST.md](file:///home/gabriel/pos-boutique/docs/CHECKLIST.md)** y **[AVANCE_VALIDACION.md](file:///home/gabriel/pos-boutique/docs/AVANCE_VALIDACION.md)**: Quedan completamente obsoletos y se reconstruirán desde cero utilizando esta auditoría como insumo principal.
