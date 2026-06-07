#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>

// ============================================================
// TRAZIA RFID - Firmware ESP32 para lector RFID 125 kHz
// ============================================================
// Conecta un lector RFID serial (RDM6300 o similar) al ESP32
// y envia las lecturas al servidor TRAZIA RFID via API REST.
//
// Funcionalidades:
// - Lectura RFID 125 kHz por serial
// - Cola offline persistente (NVS flash)
// - Reconexion WiFi automatica
// - Indicadores LED + buzzer
// - Soporte NTP para timestamps
// ============================================================

// --- PINES LECTOR RFID (Serial2) ---
// GPIO 16/17 no funcionan en muchos ESP32 DevKit (usados por flash SPI)
// Conecta TX del RDM6300 a GPIO 4
#define RXD2 4
#define TXD2 5

// --- LEDS Y BUZZER ---
#define LED_VERDE 25
#define LED_ROJO 26
#define LED_AZUL 33
#define BUZZER 27

// --- CONFIGURACION WIFI ---
const char* WIFI_SSID = "CLOES0622";
const char* WIFI_PASSWORD = "NaNis1824@";

// --- API TRAZIA RFID ---
// En produccion usa tu dominio HTTPS, por ejemplo:
// https://trazia-rfid.tudominio.com/api/device/scan
const char* TRAZIA_API_URL = "http://192.168.1.10:5000/api/device/scan";
const char* TRAZIA_PING_URL = "http://192.168.1.10:5000/api/device/ping";

// --- TOKEN DE DISPOSITIVO ---
// Debe coincidir con DEVICE_API_TOKEN en la config del servidor
const char* DEVICE_TOKEN = "trazia-device-secret-token";
const char* TOKEN_HEADER = "X-Device-Token";

// --- NOMBRE DEL DISPOSITIVO ---
const char* DEVICE_NAME = "ESP32-OFICINA-1";

// --- TIPO DE ESCANEO: "rfid", "nfc", "barcode" ---
const char* SCAN_TYPE = "rfid";

// --- NTP (hora Colombia UTC-5) ---
const char* NTP_TZ = "COT5";
const char* NTP_PRIMARY = "pool.ntp.org";
const char* NTP_SECONDARY = "time.nist.gov";

// --- TIEMPOS ---
const unsigned long WIFI_RETRY_MS = 10000;
const unsigned long QUEUE_RETRY_MS = 4000;
const unsigned long DUPLICATE_WINDOW_MS = 5000;
const unsigned long HTTP_TIMEOUT_MS = 5000;

// --- COLA OFFLINE ---
const size_t MAX_QUEUE_ITEMS = 50;

struct PendingRead {
  String uid;
  String readAt;
};

Preferences preferences;
PendingRead pendingReads[MAX_QUEUE_ITEMS];
size_t pendingCount = 0;

String serialFrame = "";
String lastUid = "";
unsigned long lastUidAtMs = 0;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastQueueAttemptMs = 0;
bool clockReady = false;

//////////////////////////////////////////////////////
// INDICADORES
//////////////////////////////////////////////////////

void beepOk() {
  digitalWrite(LED_VERDE, HIGH);
  tone(BUZZER, 2000, 150);
  delay(150);
  noTone(BUZZER);
  delay(850);
  digitalWrite(LED_VERDE, LOW);
}

void beepFound() {
  digitalWrite(LED_AZUL, HIGH);
  tone(BUZZER, 1500, 100);
  delay(100);
  tone(BUZZER, 2500, 100);
  delay(100);
  noTone(BUZZER);
  delay(800);
  digitalWrite(LED_AZUL, LOW);
}

void beepNotFound() {
  digitalWrite(LED_ROJO, HIGH);
  tone(BUZZER, 400, 300);
  delay(300);
  tone(BUZZER, 300, 300);
  delay(300);
  noTone(BUZZER);
  delay(400);
  digitalWrite(LED_ROJO, LOW);
}

void beepError() {
  digitalWrite(LED_ROJO, HIGH);
  tone(BUZZER, 200, 800);
  delay(800);
  noTone(BUZZER);
  delay(200);
  digitalWrite(LED_ROJO, LOW);
}

void beepQueued() {
  tone(BUZZER, 1000, 50);
  delay(50);
  noTone(BUZZER);
  digitalWrite(LED_ROJO, HIGH);
  delay(100);
  digitalWrite(LED_ROJO, LOW);
}

//////////////////////////////////////////////////////
// RELOJ NTP
//////////////////////////////////////////////////////

void setupClock() {
  configTzTime(NTP_TZ, NTP_PRIMARY, NTP_SECONDARY);
  struct tm timeInfo;
  clockReady = getLocalTime(&timeInfo, 3000);
  Serial.print("[NTP] Reloj sincronizado: ");
  Serial.println(clockReady ? "SI" : "NO");
}

String isoTimestampNow() {
  if (!clockReady) return "";
  time_t now;
  time(&now);
  struct tm utcTime;
  gmtime_r(&now, &utcTime);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &utcTime);
  return String(buffer);
}

//////////////////////////////////////////////////////
// WIFI
//////////////////////////////////////////////////////

bool connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;

  Serial.print("[WIFI] Conectando a ");
  Serial.print(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startedAt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startedAt < 15000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WIFI] Conectado - IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WIFI] RSSI: ");
    Serial.println(WiFi.RSSI());
    setupClock();
    return true;
  }

  Serial.println("[WIFI] No se pudo conectar");
  return false;
}

//////////////////////////////////////////////////////
// COLA PERSISTENTE (NVS Flash)
//////////////////////////////////////////////////////

void saveQueue() {
  String serialized = "";
  for (size_t i = 0; i < pendingCount; i++) {
    serialized += pendingReads[i].uid + "|" + pendingReads[i].readAt + "\n";
  }
  preferences.putString("pending", serialized);
}

void loadQueue() {
  preferences.begin("trazia-rfid", false);
  String serialized = preferences.getString("pending", "");
  pendingCount = 0;
  int start = 0;
  while (start < (int)serialized.length() && pendingCount < MAX_QUEUE_ITEMS) {
    int end = serialized.indexOf('\n', start);
    if (end < 0) end = serialized.length();
    String line = serialized.substring(start, end);
    int sep = line.indexOf('|');
    if (sep > 0) {
      pendingReads[pendingCount].uid = line.substring(0, sep);
      pendingReads[pendingCount].readAt = line.substring(sep + 1);
      pendingCount++;
    }
    start = end + 1;
  }
  Serial.print("[COLA] Pendientes cargados: ");
  Serial.println(pendingCount);
}

bool enqueueRead(const String& uid, const String& readAt) {
  if (pendingCount >= MAX_QUEUE_ITEMS) {
    for (size_t i = 1; i < pendingCount; i++) {
      pendingReads[i - 1] = pendingReads[i];
    }
    pendingCount--;
  }
  pendingReads[pendingCount].uid = uid;
  pendingReads[pendingCount].readAt = readAt;
  pendingCount++;
  saveQueue();
  return true;
}

void popQueue() {
  if (pendingCount == 0) return;
  for (size_t i = 1; i < pendingCount; i++) {
    pendingReads[i - 1] = pendingReads[i];
  }
  pendingCount--;
  saveQueue();
}

//////////////////////////////////////////////////////
// NORMALIZAR UID
//////////////////////////////////////////////////////

String normalizeUid(String raw) {
  raw.replace(String((char)0x02), "");
  raw.replace(String((char)0x03), "");
  raw.replace("\r", "");
  raw.replace("\n", "");
  raw.trim();
  raw.toUpperCase();
  if (raw.length() >= 10) {
    return raw.substring(0, 10);
  }
  return "";
}

//////////////////////////////////////////////////////
// ENVIAR AL SERVIDOR TRAZIA
//////////////////////////////////////////////////////

bool postRead(const PendingRead& item) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  WiFiClientSecure secureClient;
  secureClient.setInsecure();
  http.setTimeout(HTTP_TIMEOUT_MS);
  if (String(TRAZIA_API_URL).startsWith("https://")) {
    http.begin(secureClient, TRAZIA_API_URL);
  } else {
    http.begin(TRAZIA_API_URL);
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader(TOKEN_HEADER, DEVICE_TOKEN);

  String payload = "{\"uid\":\"" + item.uid + "\","
                   "\"device\":\"" + String(DEVICE_NAME) + "\","
                   "\"type\":\"" + String(SCAN_TYPE) + "\"";
  if (item.readAt.length() > 0) {
    payload += ",\"read_at\":\"" + item.readAt + "\"";
  }
  payload += "}";

  Serial.println("========================================");
  Serial.print("[TX] UID: ");
  Serial.println(item.uid);

  int httpCode = http.POST(payload);

  Serial.print("[TX] HTTP: ");
  Serial.println(httpCode);

  if (httpCode > 0) {
    String response = http.getString();
    Serial.print("[RX] ");
    Serial.println(response);

    if (httpCode >= 200 && httpCode < 300) {
      // Activo encontrado
      if (response.indexOf("\"ok\":true") >= 0) {
        Serial.println("[OK] Activo encontrado en TRAZIA");
        beepFound();
      }
    } else if (httpCode == 404) {
      // UID no registrado en el sistema
      Serial.println("[!] UID no registrado en inventario");
      beepNotFound();
    } else if (httpCode == 401) {
      Serial.println("[!] Token de dispositivo invalido");
      beepError();
    } else {
      Serial.println("[!] Error del servidor");
      beepError();
    }
  } else {
    Serial.print("[ERR] ");
    Serial.println(http.errorToString(httpCode));
    beepError();
  }

  http.end();

  // Consideramos exitoso si el servidor respondio (incluso 404)
  return httpCode >= 200 && httpCode < 500;
}

//////////////////////////////////////////////////////
// PROCESAR COLA
//////////////////////////////////////////////////////

void flushQueue() {
  if (pendingCount == 0 || WiFi.status() != WL_CONNECTED) return;

  while (pendingCount > 0) {
    if (!postRead(pendingReads[0])) break;
    popQueue();
  }
}

//////////////////////////////////////////////////////
// PROCESAR LECTURA RFID
//////////////////////////////////////////////////////

void processCompletedFrame() {
  String uid = normalizeUid(serialFrame);
  serialFrame = "";

  if (uid.length() < 8) return;

  unsigned long nowMs = millis();

  // Evitar duplicados rapidos
  if (uid == lastUid && (nowMs - lastUidAtMs) < DUPLICATE_WINDOW_MS) {
    return;
  }

  lastUid = uid;
  lastUidAtMs = nowMs;

  Serial.println();
  Serial.println("========== RFID DETECTADO ==========");
  Serial.print("[RFID] UID: ");
  Serial.println(uid);

  // Encolar lectura
  String readAt = isoTimestampNow();
  enqueueRead(uid, readAt);

  // Beep de confirmacion de lectura
  beepOk();

  // Intentar enviar
  flushQueue();
}

//////////////////////////////////////////////////////
// LEER DATOS DEL LECTOR RFID (Serial2)
//////////////////////////////////////////////////////

void readRfidFrame() {
  while (Serial2.available()) {
    char c = Serial2.read();
    // Debug: imprime cada byte recibido
    Serial.print("[RAW] 0x");
    Serial.print((uint8_t)c, HEX);
    Serial.print(" '");
    Serial.print(c >= 32 ? c : '.');
    Serial.println("'");

    if (c == 0x02) {
      serialFrame = "";
      continue;
    }
    if (c == 0x03 || c == '\n') {
      processCompletedFrame();
      continue;
    }
    serialFrame += c;
  }
}

//////////////////////////////////////////////////////
// SETUP
//////////////////////////////////////////////////////

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);

  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);
  pinMode(LED_AZUL, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_ROJO, LOW);
  digitalWrite(LED_AZUL, LOW);

  Serial.println();
  Serial.println("============================================");
  Serial.println("     TRAZIA RFID - Sistema de Inventario    ");
  Serial.println("============================================");
  Serial.print("  Dispositivo: ");
  Serial.println(DEVICE_NAME);
  Serial.print("  Tipo scan:   ");
  Serial.println(SCAN_TYPE);
  Serial.print("  Servidor:    ");
  Serial.println(TRAZIA_API_URL);
  Serial.println("============================================");

  loadQueue();
  connectWifi();
  flushQueue();

  // Indicar que el sistema esta listo
  digitalWrite(LED_VERDE, HIGH);
  tone(BUZZER, 1000, 100);
  delay(100);
  tone(BUZZER, 1500, 100);
  delay(100);
  tone(BUZZER, 2000, 100);
  delay(100);
  noTone(BUZZER);
  delay(500);
  digitalWrite(LED_VERDE, LOW);

  Serial.println();
  Serial.println("[LISTO] Acerque una tarjeta RFID...");
  Serial.println();
}

//////////////////////////////////////////////////////
// LOOP
//////////////////////////////////////////////////////

void loop() {
  // Leer datos RFID
  readRfidFrame();

  // Reconexion WiFi automatica
  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiAttemptMs >= WIFI_RETRY_MS) {
    lastWifiAttemptMs = millis();
    connectWifi();
  }

  // Reintentar cola pendiente
  if (millis() - lastQueueAttemptMs >= QUEUE_RETRY_MS) {
    lastQueueAttemptMs = millis();
    flushQueue();
  }
}
