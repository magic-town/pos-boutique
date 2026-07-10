# Casos de prueba — Autenticación

> Qué es esto: una descripción en lenguaje humano de qué verifica
> `test_autenticacion.py`, para que cualquiera (no solo quien lea código)
> entienda qué comportamiento del módulo de Auth está garantizado por los
> tests. No sustituye al `REPORT.md` ni reemplaza su función — este archivo
> vive fuera de esa jerarquía y solo documenta el detalle de los 44 casos.

---

## 1. Contraseñas

- Al guardar una contraseña, nunca se guarda tal cual — se guarda cifrada,
  y es imposible reconstruir la contraseña original a partir de lo
  guardado.
- Un usuario puede iniciar sesión si escribe su contraseña correcta.
- Un usuario NO puede iniciar sesión si escribe una contraseña distinta a
  la que registró.
- Aunque dos usuarios tengan exactamente la misma contraseña, lo que se
  guarda en la base de datos es distinto para cada uno (protección extra
  contra ataques si alguien roba la base de datos).

## 2. Token de sesión (lo que recibe el usuario al iniciar sesión)

- El token que se entrega al iniciar sesión identifica correctamente a
  quién pertenece y con qué rol (estándar o admin).
- El token deja de ser válido automáticamente después de una jornada
  laboral (8 horas), sin que nadie tenga que revocarlo a mano.
- Se puede pedir un token con una duración distinta a la default si el
  caso lo requiere.
- Un token no se puede falsificar: si alguien arma uno "a mano" sin la
  clave secreta del sistema, el sistema lo rechaza.

## 3. Validaciones a nivel de base de datos

- El sistema puede encontrar a un usuario por su nombre de usuario.
- El sistema reconoce correctamente cuando un usuario no existe.
- Iniciar sesión funciona solo con la combinación correcta de
  usuario + contraseña.
- Un usuario que fue dado de baja (desactivado) no puede iniciar sesión
  aunque su contraseña sea correcta.

## 4. Alta de usuarios nuevos

- Al crear un usuario, su contraseña queda cifrada automáticamente — nunca
  se guarda en texto plano.
- Un usuario nuevo queda activo por defecto.
- Un usuario nuevo queda con rol "estándar" si no se especifica otro rol.
- El sistema no permite crear dos usuarios con el mismo nombre de usuario
  (evita duplicados/confusión de identidad).

## 5. Iniciar sesión (`POST /auth/login`) — de punta a punta

- Con usuario y contraseña correctos: el login funciona y entrega un
  token utilizable.
- Con contraseña incorrecta: el login es rechazado.
- Con un usuario que no existe: el login es rechazado.
- Con un usuario desactivado: el login es rechazado, aunque la contraseña
  sea la correcta.
- **Buena práctica de seguridad verificada:** si el usuario no existe o si
  la contraseña es incorrecta, el sistema responde exactamente igual en
  ambos casos. Así nadie puede usar el mensaje de error para averiguar
  qué nombres de usuario existen en el sistema.
- Si falta el usuario o la contraseña en el formulario de login, el
  sistema lo señala como una solicitud incompleta, no como una falla
  general.

## 6. Acceso a rutas protegidas (todo lo que requiere estar logueado)

- Sin enviar ningún token: acceso denegado.
- Enviando un token válido: acceso permitido, y el sistema identifica
  correctamente a la persona.
- Enviando un token corrupto o inventado: acceso denegado.
- Enviando un token vencido: acceso denegado, aunque en su momento haya
  sido válido.
- Enviando un token que fue firmado con una clave distinta a la del
  sistema (intento de falsificación): acceso denegado.
- Enviando un token técnicamente válido pero sin la información de a
  quién pertenece: acceso denegado.
- Si el usuario del token fue eliminado de la base de datos después de
  emitirse el token: acceso denegado (el token por sí solo no basta,
  siempre se revalida contra la base de datos actual).
- Si el usuario del token fue desactivado después de emitirse el token:
  acceso denegado (mismo principio — la sesión no sobrevive a una baja).
- Si el token se envía sin el formato esperado ("Bearer ..."): acceso
  denegado.

## 7. Datos de entrada al crear un usuario

- Se acepta la creación de un usuario con datos válidos.
- Si no se indica un rol, se asigna "estándar" automáticamente.
- Se acepta explícitamente el rol "admin".
- Se rechaza un nombre de usuario vacío o compuesto solo por espacios.
- Se rechaza una contraseña vacía.
- Los espacios sobrantes al inicio o final del usuario/contraseña se
  recortan automáticamente.
- Se rechaza cualquier rol que no sea "estándar" o "admin".

## 8. Qué información se muestra de un usuario ya autenticado

- Los datos de un usuario se pueden mostrar correctamente a partir de lo
  que hay en la base de datos.
- El campo "activo" se entrega como número (1 o 0), no como texto —
  importante para que el frontend no tenga que interpretar cadenas como
  `"true"`/`"false"`.
- Ya no existe el campo antiguo `username` en la respuesta — el campo
  correcto y único es `usuario`.
- Se incluye la fecha de registro del usuario.

## 9. Estructura del token (formato interno)

- Si no se especifica, el tipo de token entregado es siempre "bearer"
  (estándar de la industria).
- Los datos internos del token (usuario, rol) son opcionales a nivel de
  estructura — el sistema no truena si llegan vacíos, solo los valida en
  otro punto del flujo.

---

**Resultado de la corrida:** 44/44 casos en verde.
