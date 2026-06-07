# TRAZIA RFID - Host, ESP32 y recuperacion de contrasena

## 1. Backend en un host publico

Publica la app Flask con HTTPS. La URL final debe quedar parecida a:

```text
https://trazia-rfid.tudominio.com
```

Variables importantes en el host:

```env
FLASK_ENV=production
SECRET_KEY=una-clave-larga-y-secreta
DATA_ENCRYPTION_KEY=otra-clave-larga-y-secreta
APP_BASE_URL=https://trazia-rfid.tudominio.com
DEVICE_API_TOKEN=un-token-largo-para-el-esp32

MAIL_ENABLED=true
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=tu-correo@gmail.com
MAIL_PASSWORD=app-password-de-google
MAIL_DEFAULT_SENDER=tu-correo@gmail.com
```

## 2. ESP32 con lector RFID

El ESP32 envia cada lectura al servidor con:

```http
POST /api/device/scan
Header: X-Device-Token: DEVICE_API_TOKEN
Body:
{
  "uid": "CODIGO_RFID",
  "device": "ESP32-OFICINA-1",
  "type": "rfid",
  "read_at": "2026-06-07T02:00:00Z"
}
```

En `arduino/trazia_rfid_esp32/trazia_rfid_esp32.ino`, cambia:

```cpp
const char* TRAZIA_API_URL = "https://trazia-rfid.tudominio.com/api/device/scan";
const char* TRAZIA_PING_URL = "https://trazia-rfid.tudominio.com/api/device/ping";
const char* DEVICE_TOKEN = "el-mismo-token-del-host";
```

## 3. App movil

En la app Expo, apunta al dominio publico:

```powershell
$env:EXPO_PUBLIC_WEB_URL="https://trazia-rfid.tudominio.com"
npx expo start --clear
```

Si compilas una app final, esa variable debe estar definida antes del build.

## 4. Recuperacion de contrasena

Hay dos caminos:

1. El admin entra a Usuarios y usa `Acceso temporal`.
2. El usuario toca `Olvide mi contrasena` en la app movil.

En ambos casos el sistema genera una contrasena temporal, la envia por correo, marca `force_password_change = true` y obliga a cambiarla al iniciar sesion.

La temporal vence en 12 horas.
