# Casos de prueba — Setting/Configuración

> Espejo en lenguaje humano de `test/test_setting.py`. Cada caso de abajo
> corresponde 1:1 a una función de test (el nombre entre paréntesis). Si
> cambia el comportamiento del módulo, este documento y el test deben
> actualizarse juntos — si no coinciden, el test manda.
>
> Fuera del alcance de `REPORT.md`.

---

## Usuarios

### Agregar usuario

| # | Caso | Resultado esperado |
|---|------|---------------------|
| 1 | Se agrega un usuario nuevo con datos válidos. | `201 Created`. La respuesta trae el nombre de usuario, y nunca la contraseña ni su hash. (`test_agregar_usuario_ok`) |
| 2 | Se intenta agregar un usuario con un nombre que ya existe. | `409 Conflict`. (`test_agregar_usuario_duplicado_409`) |
| 3 | Se intenta agregar un usuario con contraseña inválida: muy corta (`abc`), muy larga (11+ caracteres), sin mayúscula (`clave123`), o vacía. | `422` en los cuatro casos. (`test_agregar_usuario_password_invalido_422`) |
| 4 | Se intenta agregar un usuario con un rol que no existe (`superadmin`). | `422`. Solo se aceptan `estandar` y `admin`. (`test_agregar_usuario_rol_invalido_422`) |

### Cambiar contraseña

| # | Caso | Resultado esperado |
|---|------|---------------------|
| 5 | Se cambia la contraseña de un usuario existente. | `200 OK`. Con la contraseña nueva el login funciona (`200`); con la contraseña vieja, ya no (`401`). (`test_cambiar_password_ok_y_permite_login`) |
| 6 | Se intenta cambiar la contraseña de un usuario que no existe (`id_usuario = 999999`). | `404 Not Found`. (`test_cambiar_password_usuario_inexistente_404`) |
| 7 | Se intenta poner una contraseña que no cumple las reglas (sin mayúscula). | `422`. (`test_cambiar_password_invalido_422`) |

### Cambiar rol

| # | Caso | Resultado esperado |
|---|------|---------------------|
| 8 | Se cambia el rol de un usuario de `estandar` a `admin`. | `200 OK`, y el cambio queda reflejado directo en la base de datos. (`test_cambiar_rol_ok`) |
| 9 | Se intenta poner un rol que no existe (`superadmin`). | `422`. (`test_cambiar_rol_invalido_422`) |
| 10 | Se intenta cambiar el rol de un usuario que no existe. | `404`. (`test_cambiar_rol_usuario_inexistente_404`) |

> **No se prueba** lógica de permisos diferenciada entre `estandar` y
> `admin` (por ejemplo, que solo un `admin` pueda cambiar roles) porque el
> spec (`module_setting.md`) la marca explícitamente como "sin lógica de
> permisos diferenciada en MVP".

---

## Información del sistema

### Zona horaria

| # | Caso | Resultado esperado |
|---|------|---------------------|
| 11 | Se consulta la zona horaria del sistema. | `200 OK`, valor `America/Mexico_City` (el sembrado por default). Es de solo lectura — no hay endpoint para cambiarla. (`test_zona_horaria_lectura`) |

---

## Configuración (métodos de pago, CLABEs)

| # | Caso | Resultado esperado |
|---|------|---------------------|
| 12 | Se listan todas las claves de configuración. | `200 OK`. Incluye, como mínimo, las 6 claves de métodos de pago (`pago_efectivo_activo`, `pago_transferencia_activo`, `pago_tarjeta_debito_activo`, `pago_tarjeta_credito_activo`, `pago_msi_activo`, `pago_vales_activo`) y `zona_horaria`. (`test_listar_configuracion`) |
| 13 | Se intenta desactivar el método de pago Efectivo (`valor: "0"`). | `409 Conflict` — Efectivo nunca se puede desactivar. (`test_efectivo_no_se_puede_desactivar`) |
| 14 | Se activa "Meses sin intereses" (bloqueado por defecto) y luego se vuelve a desactivar. | `200 OK` en ambos pasos, el valor queda en `"1"` y después en `"0"`. (`test_activar_y_revertir_msi`) |
| 15 | Se intenta poner un valor que no es `"0"` ni `"1"` en un método de pago (ej. `"activo"`). | `422`. (`test_metodo_pago_valor_invalido_422`) |
| 16 | Se actualiza una CLABE (`clabe_1`) con un valor de texto libre. | `200 OK`, se guarda tal cual — sin validación de formato en MVP. (`test_clabe_acepta_texto_libre`) |
| 17 | Se intenta actualizar una clave de configuración que no existe. | `404 Not Found`. (`test_clave_inexistente_404`) |

---

## Autorización

Todos los endpoints de Setting requieren sesión iniciada. Sin token
(`Authorization` ausente), cualquiera de estos devuelve `401`:

| # | Endpoint |
|---|----------|
| 18 | `GET /setting/zona-horaria` |
| 19 | `GET /setting/configuracion` |
| 20 | `POST /setting/usuarios` |
| 21 | `PATCH /setting/usuarios/{id}/password` |
| 22 | `PATCH /setting/usuarios/{id}/rol` |
| 23 | `PATCH /setting/configuracion/{clave}` |

(`test_endpoint_sin_token_401`, parametrizado — 6 casos en una sola función de test)

---

**Total: 26 casos** (algunos empaquetados en funciones parametrizadas de
pytest — de ahí que el conteo de casos no sea 1:1 con el número de
funciones del archivo).
