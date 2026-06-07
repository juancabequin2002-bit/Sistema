# TRAZIA RFID Mobile

Base movil para iOS y Android construida con Expo y `react-native-webview`.

SDK objetivo actual:

- Expo SDK `54`
- React Native `0.81`
- React `19.1`

## Objetivo

- reutilizar el backend Flask existente
- empaquetar el sistema como app movil real
- dejar lista la base para evolucionar despues a capacidades nativas mas profundas

## Requisitos

- Node.js
- Expo CLI mediante `npx`

## Configuracion

Define la URL del backend Flask antes de iniciar:

### Android emulador

```powershell
$env:EXPO_PUBLIC_WEB_URL="http://10.0.2.2:5000"
```

### iOS simulador

```powershell
$env:EXPO_PUBLIC_WEB_URL="http://127.0.0.1:5000"
```

### Dispositivo fisico

```powershell
$env:EXPO_PUBLIC_WEB_URL="http://TU_IP_LOCAL:5000"
```

## Instalacion

```powershell
cd C:\Users\garci\Documents\Codex\2026-05-03\quiero-construir-una-aplicaci-n-web\trazia_mobile_app
npm install
```

## Ejecucion

```powershell
npm run start
```

Luego puedes abrir:

- `npm run android`
- `npm run ios`
- o escanear el QR con Expo Go compatible con SDK 54

## Si Expo Go muestra incompatibilidad

Haz un arranque limpio:

```powershell
cd C:\Users\garci\Documents\Codex\2026-05-03\quiero-construir-una-aplicaci-n-web\trazia_mobile_app
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json -ErrorAction SilentlyContinue
npm install
npx expo start --clear
```

## Alcance actual

- app movil con identidad TRAZIA RFID
- icono y splash propios
- acceso a dashboard, activos, barras, NFC y cuenta
- contenedor nativo para el sistema Flask existente

## Siguiente fase recomendada

- autenticacion movil por token/API
- escaneo nativo con `expo-camera`
- NFC nativo con modulo dedicado en dev build
- notificaciones push
- cache offline de inventario critico
