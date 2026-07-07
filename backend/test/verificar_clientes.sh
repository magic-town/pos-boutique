#!/usr/bin/env bash
# Verificación manual del módulo Clientes contra un servidor real (paso 3 de
# tu checklist). Requiere:
#   1. Servidor corriendo:  uvicorn app.main:app --reload
#   2. Usuario admin con password conocida (scripts/set_admin_password.py)
#
# ⚠️ Rutas de consulta/rehabilitar INFERIDAS, no confirmadas contra
# app/api/v1/endpoints/clientes.py — ajusta BASE_URL y las rutas si difieren.
#
# Uso:
#   chmod +x verificar_clientes.sh
#   ADMIN_USER=admin ADMIN_PASS='TuPasswordSegura123' ./verificar_clientes.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
ADMIN_USER="${ADMIN_USER:?Falta ADMIN_USER}"
ADMIN_PASS="${ADMIN_PASS:?Falta ADMIN_PASS}"

echo "== Login =="
TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${ADMIN_USER}&password=${ADMIN_PASS}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "No se obtuvo token. Revisa credenciales / que el servidor esté arriba."
  exit 1
fi
AUTH="Authorization: Bearer $TOKEN"
echo "OK, token obtenido."
echo

SUFIJO=$(date +%s)

echo "== 1. Quincenal simple (esperado 201) =="
curl -s -o /tmp/r1.json -w "HTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/clientes" \
  -H "$AUTH" -H "Content-Type: application/json" -d '{
    "nombre": "Prueba Quincenal", "colonia": "VerifQ'"$SUFIJO"'",
    "telefono": 5512345678, "ref_nombre": "Ref Q", "ref_colonia": "Centro",
    "ref_telefono": null, "frecuencia_pago": "quincenal",
    "dia_pago_especifico": null, "frecuencia_pago_detalle": null
  }'
cat /tmp/r1.json; echo; echo

echo "== 2. dia_especifico_mes CON día (esperado 201) =="
curl -s -o /tmp/r2.json -w "HTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/clientes" \
  -H "$AUTH" -H "Content-Type: application/json" -d '{
    "nombre": "Prueba Dia Especifico", "colonia": "VerifD'"$SUFIJO"'",
    "telefono": 5512345679, "ref_nombre": "Ref D", "ref_colonia": "Centro",
    "ref_telefono": null, "frecuencia_pago": "dia_especifico_mes",
    "dia_pago_especifico": 15, "frecuencia_pago_detalle": null
  }'
cat /tmp/r2.json; echo; echo
ID_CLIENTE=$(python3 -c "import json; print(json.load(open('/tmp/r2.json')).get('id_cliente','?'))" 2>/dev/null || echo "?")

echo "== 3. dia_especifico_mes SIN día (esperado 422) =="
curl -s -o /tmp/r3.json -w "HTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/clientes" \
  -H "$AUTH" -H "Content-Type: application/json" -d '{
    "nombre": "Prueba Sin Dia", "colonia": "VerifSD'"$SUFIJO"'",
    "telefono": 5512345680, "ref_nombre": "Ref SD", "ref_colonia": "Centro",
    "ref_telefono": null, "frecuencia_pago": "dia_especifico_mes",
    "dia_pago_especifico": null, "frecuencia_pago_detalle": null
  }'
cat /tmp/r3.json; echo; echo

echo "== 4. Rango de dia_pago_especifico inválido (32) (esperado 422) =="
curl -s -o /tmp/r4.json -w "HTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/clientes" \
  -H "$AUTH" -H "Content-Type: application/json" -d '{
    "nombre": "Prueba Rango Invalido", "colonia": "VerifR'"$SUFIJO"'",
    "telefono": 5512345681, "ref_nombre": "Ref R", "ref_colonia": "Centro",
    "ref_telefono": null, "frecuencia_pago": "dia_especifico_mes",
    "dia_pago_especifico": 32, "frecuencia_pago_detalle": null
  }'
cat /tmp/r4.json; echo; echo

echo "== 5. otro CON detalle (esperado 201) =="
curl -s -o /tmp/r5.json -w "HTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/clientes" \
  -H "$AUTH" -H "Content-Type: application/json" -d '{
    "nombre": "Prueba Otro Con Detalle", "colonia": "VerifOC'"$SUFIJO"'",
    "telefono": 5512345682, "ref_nombre": "Ref OC", "ref_colonia": "Centro",
    "ref_telefono": null, "frecuencia_pago": "otro",
    "dia_pago_especifico": null, "frecuencia_pago_detalle": "Paga cada 10 dias, acuerdo verbal"
  }'
cat /tmp/r5.json; echo; echo

echo "== 6. otro SIN detalle (esperado 422) =="
curl -s -o /tmp/r6.json -w "HTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/clientes" \
  -H "$AUTH" -H "Content-Type: application/json" -d '{
    "nombre": "Prueba Otro Sin Detalle", "colonia": "VerifOS'"$SUFIJO"'",
    "telefono": 5512345683, "ref_nombre": "Ref OS", "ref_colonia": "Centro",
    "ref_telefono": null, "frecuencia_pago": "otro",
    "dia_pago_especifico": null, "frecuencia_pago_detalle": null
  }'
cat /tmp/r6.json; echo; echo

echo "== 7. Longitud excedida: frecuencia_pago_detalle de 61 caracteres (esperado 422, INC-18) =="
DETALLE_61=$(python3 -c "print('a' * 61)")
curl -s -o /tmp/r7.json -w "HTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/clientes" \
  -H "$AUTH" -H "Content-Type: application/json" -d '{
    "nombre": "Prueba Longitud", "colonia": "VerifL'"$SUFIJO"'",
    "telefono": 5512345684, "ref_nombre": "Ref L", "ref_colonia": "Centro",
    "ref_telefono": null, "frecuencia_pago": "otro",
    "dia_pago_especifico": null, "frecuencia_pago_detalle": "'"$DETALLE_61"'"
  }'
cat /tmp/r7.json; echo; echo

if [ "$ID_CLIENTE" != "?" ]; then
  echo "== 8. GET del cliente creado en el paso 2 (esperado 200, campos nuevos visibles) =="
  curl -s -o /tmp/r8.json -w "HTTP %{http_code}\n" "$BASE_URL/api/v1/clientes/$ID_CLIENTE" -H "$AUTH"
  cat /tmp/r8.json; echo; echo

  echo "== 9. Rehabilitar (idempotente sobre cliente activo, esperado 200) =="
  curl -s -o /tmp/r9.json -w "HTTP %{http_code}\n" -X PATCH \
    "$BASE_URL/api/v1/clientes/$ID_CLIENTE/rehabilitar" -H "$AUTH"
  cat /tmp/r9.json; echo; echo
else
  echo "Aviso: no se pudo extraer id_cliente del paso 2, se omiten los pasos 8 y 9."
fi

echo "== Resumen =="
echo "Revisa arriba que: 201 en los casos 1,2,5,8,9 · 422 en los casos 3,4,6,7."
echo "Recuerda rotar la contraseña de admin después de correr esto."
