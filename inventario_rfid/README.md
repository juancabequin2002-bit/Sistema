# TRAZIA RFID

Aplicacion web completa en Flask para gestionar inventario, custodia y trazabilidad inteligente con RFID 125 kHz, NFC, codigo de barras, hoja de vida de activos, expedientes, carpetas, archivos fisicos, asignaciones, mantenimientos, documentos, reportes, bitacora e integracion opcional con GPT4All local.

## Caracteristicas

- Login con `Flask-Login` y contrasenas con hash `scrypt`.
- Cifrado en reposo de campos sensibles con `Fernet`.
- Roles: `administrador`, `tecnico`, `consulta`, `auditor`.
- CRUD base de usuarios y activos.
- Cambio centralizado de roles para cualquier usuario.
- Recuperacion de contrasena por correo con token firmado.
- Verificacion de cuenta por correo con enlaces temporales.
- Envio de acceso temporal por Gmail con cambio obligatorio de contrasena.
- Verificacion de correo para nuevos usuarios.
- Pantalla `/rfid` optimizada para lector USB tipo teclado.
- Hoja de vida del activo con pestanas.
- Mantenimientos, documentos y bajas.
- Bitacora del sistema.
- Reportes con exportacion inicial a CSV.
- UI tech premium con identidad visual TRAZIA RFID.
- Integracion opcional con GPT4All local.
- App movil base para iOS y Android con Expo.

## Estructura

```text
inventario_rfid/
├── app.py
├── config.py
├── models.py
├── forms.py
├── decorators.py
├── requirements.txt
├── README.md
├── static/
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   └── main.js
│   └── uploads/
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── activos/
    ├── usuarios/
    ├── mantenimientos/
    ├── documentos/
    ├── reportes/
    └── errores/
```

## Instalacion

1. Crear y activar entorno virtual:

```powershell
cd C:\Users\garci\Documents\Codex\2026-05-03\quiero-construir-una-aplicaci-n-web\inventario_rfid
python -m venv .venv
.venv\Scripts\activate
```

2. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

3. Inicializar base de datos:

```powershell
flask --app app.py init-db
```

4. Ejecutar el proyecto:

```powershell
python app.py
```

5. Abrir en el navegador:

```text
http://127.0.0.1:5000
```

## Usuario administrador inicial

- Usuario: `admin`
- Contrasena: `admin123`
- Correo: `admin@example.com`
- Rol: `administrador`

La funcion `seed_admin()` crea tambien estas ubicaciones iniciales:

- Oficina Sistemas
- Sala de Servidores
- Archivo Central
- Administracion
- Bodega

## Base de datos

- Desarrollo: SQLite
- Produccion: PostgreSQL por variable `DATABASE_URL`

Ejemplo:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://usuario:clave@localhost/inventario_rfid"
python app.py
```

## Lectura RFID USB 125 kHz

El lector funciona como teclado USB:

1. Inicia sesion.
2. Abre `http://127.0.0.1:5000/rfid`
3. Haz clic una vez si el cursor no esta activo.
4. Escanea la etiqueta.
5. El sistema captura el codigo en el input autofocus.
6. Si el RFID existe, abre la hoja de vida del activo.
7. Si no existe, redirige al formulario de creacion con `rfid_code` precargado.

## Integracion GPT4All

La app queda preparada para dos modos:

### 1. Servidor local GPT4All recomendado

Segun la documentacion oficial de GPT4All, el servidor local se activa desde la app de escritorio en `Settings > Application > Advanced > Enable Local API Server` y escucha por defecto en `http://localhost:4891/v1`.

Variables opcionales:

```powershell
$env:GPT4ALL_ENABLED="true"
$env:GPT4ALL_MODE="server"
$env:GPT4ALL_SERVER_URL="http://127.0.0.1:4891/v1"
$env:GPT4ALL_MODEL="Phi-3 Mini Instruct"
```

### 2. SDK de Python

```powershell
$env:GPT4ALL_MODE="sdk"
$env:GPT4ALL_SDK_MODEL="Phi-3-mini-4k-instruct.Q4_0.gguf"
```

En la hoja de vida del activo aparece una seccion de IA para pedir resumen tecnico, riesgos o recomendaciones.

## Seguridad

- CSRF con `Flask-WTF`
- Hash de contrasenas con Werkzeug usando `scrypt`
- Cifrado de campos sensibles con `cryptography.Fernet`
- Restriccion de extensiones en archivos
- Proteccion de rutas por login y rol
- Bitacora con usuario, modulo, accion, fecha e IP

## Configuracion de correos

```powershell
$env:MAIL_ENABLED="true"
$env:MAIL_SERVER="smtp.gmail.com"
$env:MAIL_PORT="587"
$env:MAIL_USE_TLS="true"
$env:MAIL_USE_SSL="false"
$env:MAIL_USERNAME="tu_correo@dominio.com"
$env:MAIL_PASSWORD="tu_clave_o_app_password"
$env:MAIL_DEFAULT_SENDER="tu_correo@dominio.com"
$env:MAIL_SUPPRESS_SEND="false"
$env:SECURITY_PASSWORD_SALT="cambia-este-salt"
$env:EMAIL_TOKEN_EXPIRATION_HOURS="24"
$env:PASSWORD_RESET_EXPIRATION_HOURS="2"
$env:APP_NAME="RFID 125 kHz - Sistema de Inventario"
$env:APP_BASE_URL="http://127.0.0.1:5000"
```

Variables principales:

- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USE_TLS`
- `MAIL_USE_SSL`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_DEFAULT_SENDER`
- `MAIL_SUPPRESS_SEND`
- `SECURITY_PASSWORD_SALT`
- `EMAIL_TOKEN_EXPIRATION_HOURS`
- `PASSWORD_RESET_EXPIRATION_HOURS`
- `APP_NAME`
- `APP_BASE_URL`

El sistema usa `Flask-Mail` para enviar:

- verificacion de cuenta al crear usuarios
- reenvio de verificacion
- recuperacion de contrasena por enlace temporal

Si `MAIL_SUPPRESS_SEND=true`, Flask-Mail no hara envio real y sirve para pruebas controladas en desarrollo.

### Gmail importante

Para Gmail o Google Workspace, normalmente no funciona la contrasena normal de la cuenta. Lo recomendado es:

1. Activar verificacion en dos pasos en Google.
2. Crear una `App Password`.
3. Usar esa `App Password` en `MAIL_PASSWORD`.

Si Gmail rechaza el acceso SMTP, ese suele ser el motivo principal.

Tambien puedes usar el archivo local `.env` del proyecto como fuente de configuracion. Hay un ejemplo actualizado en `.env.example`.

## Branding y logos

La plataforma incluye la identidad TRAZIA RFID basada en:

- hexagono tecnologico
- chip RFID estilizado
- ondas inalambricas
- paleta azul electrico + morado tecnologico

Activos incluidos:

- `logo-horizontal-light.svg`
- `logo-horizontal-dark.svg`
- `logo-icon-light.svg`
- `logo-icon-dark.svg`
- `logo-mono-light.svg`
- `favicon.svg`
- `app-icon.png`
- `adaptive-icon.png`
- `splash-icon.png`

La plataforma usa estos activos en:

- sidebar
- login
- favicon
- correos transaccionales
- app movil base iOS/Android

Si deseas cambiar rutas:

```powershell
$env:BRAND_LOGO_PATH="img/brand/logo-horizontal-light.svg"
$env:BRAND_MARK_PATH="img/brand/logo-icon-light.svg"
$env:BRAND_EMAIL_LOGO_PATH="img/brand/logo-horizontal-dark.svg"
$env:BRAND_FAVICON_PATH="img/brand/favicon.svg"
```

Si esos archivos no existen, el sistema usa un fallback visual con iconografia para no romper la interfaz.

## App movil iOS y Android

Se incluye una app base Expo en:

`C:\Users\garci\Documents\Codex\2026-05-03\quiero-construir-una-aplicaci-n-web\trazia_mobile_app`

Caracteristicas actuales:

- branding TRAZIA RFID
- icono y splash propios
- shell movil para dashboard, activos, barras, NFC y cuenta
- uso del backend Flask actual mediante `WebView`

Consulta mas detalle en:

`C:\Users\garci\Documents\Codex\2026-05-03\quiero-construir-una-aplicaci-n-web\trazia_mobile_app\README.md`

## Importante si ya ejecutaste la version anterior

Esta version cambia el esquema para cifrado de datos sensibles. Si ya existe `inventario.db` de una prueba previa, elimina ese archivo y vuelve a inicializar:

```powershell
flask --app app.py init-db
```

## Criterios principales ya cubiertos

- Iniciar sesion como administrador
- Crear usuarios con roles
- Crear activos con RFID
- Escanear RFID y abrir detalle
- Redirigir a creacion si RFID no existe
- Asignar responsables
- Registrar mantenimientos
- Subir documentos
- Ver hoja de vida completa
- Dar de baja como administrador
- Ver dashboard y bitacora
- Exportar CSV

## Notas

- La carpeta de archivos adjuntos es `static/uploads/`.
- Si se va a desplegar en produccion, se recomienda mover archivos adjuntos a almacenamiento externo o protegido.
- La exportacion a Excel/PDF queda preparada a nivel de estructura, pero la salida implementada en esta version es CSV.
