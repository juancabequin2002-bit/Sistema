import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import api from "../api";

let NfcManager = null;
let NfcTech = {};
try {
  const nfcModule = require("react-native-nfc-manager");
  NfcManager = nfcModule.default || nfcModule;
  NfcTech = nfcModule.NfcTech || {};
} catch (_) {}

const uriPrefixes = [
  "", "http://www.", "https://www.", "http://", "https://", "tel:", "mailto:",
  "ftp://anonymous:anonymous@", "ftp://ftp.", "ftps://", "sftp://", "smb://",
  "nfs://", "ftp://", "dav://", "news:", "telnet://", "imap:", "rtsp://",
  "urn:", "pop:", "sip:", "sips:", "tftp:", "btspp://", "btl2cap://",
  "btgoep://", "tcpobex://", "irdaobex://", "file://", "urn:epc:id:",
  "urn:epc:tag:", "urn:epc:pat:", "urn:epc:raw:", "urn:epc:", "urn:nfc:",
];

function bytesToString(bytes) {
  return bytes.map((byte) => String.fromCharCode(byte)).join("");
}

function bytesToHex(bytes) {
  return bytes.map((byte) => byte.toString(16).padStart(2, "0")).join("").toUpperCase();
}

function decodeNdefRecord(record) {
  const payload = Array.from(record?.payload || []);
  if (!payload.length) return null;

  const type = bytesToString(Array.from(record?.type || []));
  if (type === "T") {
    const languageLength = payload[0] & 0x3f;
    return bytesToString(payload.slice(1 + languageLength)).trim();
  }
  if (type === "U") {
    const prefix = uriPrefixes[payload[0]] || "";
    return `${prefix}${bytesToString(payload.slice(1))}`.trim();
  }
  return bytesToString(payload).trim();
}

function getCodeFromTag(tag) {
  const records = tag?.ndefMessage || [];
  for (const record of records) {
    const decoded = decodeNdefRecord(record);
    if (decoded) return decoded;
  }
  if (tag?.id) return String(tag.id).toUpperCase();
  if (tag?.identifier) return bytesToHex(Array.from(tag.identifier));
  return "";
}

export default function NfcScreen({ navigation }) {
  const [manualCode, setManualCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [nfcReady, setNfcReady] = useState(false);
  const [nfcReading, setNfcReading] = useState(false);
  const [nfcStatus, setNfcStatus] = useState("Inicializando NFC...");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const searchCode = useCallback(async (rawCode, preferredType = "nfc") => {
    const code = String(rawCode || "").trim();
    if (!code) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await api.getAssetByCode(code, preferredType);
      setResult(data);
    } catch (err) {
      if (err.status === 404) {
        setError("No se encontro un activo con ese codigo");
      } else {
        setError(err.message || "Error de busqueda");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    const initNfc = async () => {
      if (!NfcManager || Platform.OS === "web") {
        if (mounted) {
          setNfcReady(false);
          setNfcStatus("NFC nativo no disponible en este entorno.");
        }
        return;
      }

      try {
        const supported = await NfcManager.isSupported();
        if (!mounted) return;
        if (!supported) {
          setNfcReady(false);
          setNfcStatus("Este dispositivo no reporta soporte NFC.");
          return;
        }
        await NfcManager.start();
        const enabled = await NfcManager.isEnabled();
        if (!mounted) return;
        setNfcReady(enabled);
        setNfcStatus(enabled ? "Listo para leer etiquetas NFC." : "Activa NFC en los ajustes del dispositivo.");
      } catch (err) {
        if (mounted) {
          setNfcReady(false);
          setNfcStatus(err.message || "No fue posible iniciar NFC.");
        }
      }
    };

    initNfc();
    return () => {
      mounted = false;
      if (NfcManager) {
        NfcManager.cancelTechnologyRequest().catch(() => {});
      }
    };
  }, []);

  const handleSearch = () => searchCode(manualCode, "nfc");

  const handleReadNfc = async () => {
    if (!NfcManager || !nfcReady || nfcReading) return;

    setNfcReading(true);
    setError(null);
    setResult(null);
    setNfcStatus("Acerca una etiqueta NFC al telefono...");

    const techs = [NfcTech.Ndef, NfcTech.NfcA, NfcTech.NfcV, NfcTech.IsoDep].filter(Boolean);
    let lastError = null;

    try {
      for (const tech of techs) {
        try {
          await NfcManager.requestTechnology(tech);
          const tag = await NfcManager.getTag();
          const code = getCodeFromTag(tag);
          if (!code) {
            throw new Error("La etiqueta no entrego un codigo legible.");
          }
          setManualCode(code);
          setNfcStatus(`Etiqueta leida: ${code}`);
          await searchCode(code, "nfc");
          return;
        } catch (err) {
          lastError = err;
        } finally {
          await NfcManager.cancelTechnologyRequest().catch(() => {});
        }
      }
      throw lastError || new Error("No fue posible leer la etiqueta NFC.");
    } catch (err) {
      setNfcStatus("Lectura NFC detenida.");
      setError(err.message || "No fue posible leer la etiqueta NFC.");
    } finally {
      setNfcReading(false);
    }
  };

  const cancelRead = async () => {
    if (NfcManager) {
      await NfcManager.cancelTechnologyRequest().catch(() => {});
    }
    setNfcReading(false);
    setNfcStatus("Lectura cancelada.");
  };

  const handleViewAsset = () => {
    if (result && result.id) {
      navigation.navigate("Assets", {
        screen: "AssetDetail",
        params: { assetId: result.id },
      });
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.nfcSection}>
        <View style={styles.nfcIcon}>
          <Text style={styles.nfcIconText}>NFC</Text>
        </View>
        <Text style={styles.nfcTitle}>Lectura NFC</Text>
        <Text style={styles.nfcDescription}>
          Lee etiquetas NFC reales y busca el activo por codigo NFC. Si la etiqueta
          tiene texto NDEF se usa ese valor; si no, se usa el UID.
        </Text>
        <View style={styles.nfcStatus}>
          <View style={[styles.statusIndicator, nfcReady && styles.statusReady, nfcReading && styles.statusReading]} />
          <Text style={[styles.statusLabel, nfcReady && styles.statusReadyText]}>{nfcStatus}</Text>
        </View>
        <View style={styles.nfcActions}>
          <Pressable
            style={[styles.nfcBtn, (!nfcReady || nfcReading) && styles.searchBtnDisabled]}
            onPress={handleReadNfc}
            disabled={!nfcReady || nfcReading}
          >
            {nfcReading ? (
              <ActivityIndicator color="#FFFFFF" size="small" />
            ) : (
              <Text style={styles.nfcBtnText}>Leer NFC</Text>
            )}
          </Pressable>
          {nfcReading ? (
            <Pressable style={styles.cancelBtn} onPress={cancelRead}>
              <Text style={styles.cancelBtnText}>Cancelar</Text>
            </Pressable>
          ) : null}
        </View>
      </View>

      <View style={styles.manualSection}>
        <Text style={styles.sectionTitle}>Busqueda manual por codigo</Text>
        <Text style={styles.sectionDescription}>
          Introduce el codigo RFID, NFC o identificador del activo manualmente:
        </Text>

        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={manualCode}
            onChangeText={(text) => {
              setManualCode(text);
              setError(null);
              setResult(null);
            }}
            placeholder="Ej: 04A1B2C3D4"
            placeholderTextColor="#6B7A8F"
            autoCapitalize="characters"
            autoCorrect={false}
            returnKeyType="search"
            onSubmitEditing={handleSearch}
          />
          <Pressable
            style={[styles.searchBtn, loading && styles.searchBtnDisabled]}
            onPress={handleSearch}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" size="small" />
            ) : (
              <Text style={styles.searchBtnText}>Buscar</Text>
            )}
          </Pressable>
        </View>

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        {result ? (
          <Pressable style={styles.resultCard} onPress={handleViewAsset}>
            <Text style={styles.resultName}>{result.name || result.nombre || "Sin nombre"}</Text>
            <Text style={styles.resultCode}>
              {result.internal_code || result.rfid_code || result.nfc_code || result.barcode_code}
            </Text>
            <Text style={styles.resultHint}>Toca para ver detalles</Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B111A",
    padding: 20,
  },
  nfcSection: {
    backgroundColor: "#121C2C",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#233650",
    padding: 24,
    alignItems: "center",
    marginBottom: 24,
  },
  nfcIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#1A2D4A",
    borderWidth: 2,
    borderColor: "#355F9E",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 14,
  },
  nfcIconText: {
    color: "#146CFF",
    fontSize: 16,
    fontWeight: "800",
  },
  nfcTitle: {
    color: "#FFFFFF",
    fontSize: 18,
    fontWeight: "800",
    marginBottom: 8,
  },
  nfcDescription: {
    color: "#A9B8D0",
    fontSize: 13,
    textAlign: "center",
    lineHeight: 19,
    marginBottom: 14,
  },
  nfcStatus: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  statusIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#F59E0B",
  },
  statusReady: {
    backgroundColor: "#10B981",
  },
  statusReading: {
    backgroundColor: "#146CFF",
  },
  statusLabel: {
    color: "#F59E0B",
    fontSize: 12,
    fontWeight: "600",
    flexShrink: 1,
  },
  statusReadyText: {
    color: "#A7F3D0",
  },
  nfcActions: {
    flexDirection: "row",
    gap: 10,
    marginTop: 16,
  },
  nfcBtn: {
    minWidth: 126,
    backgroundColor: "#146CFF",
    borderRadius: 12,
    paddingHorizontal: 18,
    paddingVertical: 12,
    alignItems: "center",
  },
  nfcBtnText: {
    color: "#FFFFFF",
    fontWeight: "800",
  },
  cancelBtn: {
    backgroundColor: "#1E293B",
    borderWidth: 1,
    borderColor: "#334155",
    borderRadius: 12,
    paddingHorizontal: 18,
    paddingVertical: 12,
  },
  cancelBtnText: {
    color: "#FFFFFF",
    fontWeight: "700",
  },
  manualSection: {
    flex: 1,
  },
  sectionTitle: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 6,
  },
  sectionDescription: {
    color: "#A9B8D0",
    fontSize: 13,
    marginBottom: 14,
  },
  inputRow: {
    flexDirection: "row",
    gap: 10,
  },
  input: {
    flex: 1,
    backgroundColor: "#121C2C",
    borderWidth: 1,
    borderColor: "#233650",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: "#FFFFFF",
    fontSize: 14,
  },
  searchBtn: {
    backgroundColor: "#146CFF",
    borderRadius: 12,
    paddingHorizontal: 18,
    justifyContent: "center",
    alignItems: "center",
  },
  searchBtnDisabled: {
    opacity: 0.6,
  },
  searchBtnText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 14,
  },
  errorBox: {
    marginTop: 14,
    backgroundColor: "#2D1111",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#DC2626",
    padding: 12,
  },
  errorText: {
    color: "#FCA5A5",
    fontSize: 13,
    textAlign: "center",
  },
  resultCard: {
    marginTop: 14,
    backgroundColor: "#121C2C",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#146CFF",
    padding: 16,
  },
  resultName: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
  resultCode: {
    color: "#7EA3D4",
    fontSize: 13,
    marginTop: 4,
  },
  resultHint: {
    color: "#146CFF",
    fontSize: 12,
    marginTop: 8,
    fontWeight: "600",
  },
});
