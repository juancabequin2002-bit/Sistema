import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import api from "../api";

export default function ScannerScreen({ navigation }) {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const [scannedData, setScannedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleBarCodeScanned = ({ type, data }) => {
    if (scanned) return;
    setScanned(true);
    setScannedData({ type, data });
    setError(null);
  };

  const handleUseCode = async () => {
    if (scannedData) {
      setLoading(true);
      setError(null);
      try {
        const asset = await api.getAssetFromScan(scannedData.data, scannedData.type);
        navigation.navigate("Assets", {
          screen: "AssetDetail",
          params: { assetId: asset.id },
        });
      } catch (err) {
        setError(err.message || "No se encontro un activo con ese codigo");
      } finally {
        setLoading(false);
      }
    }
  };

  const handleScanAgain = () => {
    setScanned(false);
    setScannedData(null);
    setError(null);
  };

  if (!permission) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#146CFF" />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text style={styles.message}>
          Se necesita acceso a la cámara para escanear códigos
        </Text>
        <Pressable style={styles.button} onPress={requestPermission}>
          <Text style={styles.buttonText}>Permitir Cámara</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView
        style={styles.camera}
        barcodeScannerSettings={{
          barcodeTypes: [
            "qr",
            "ean13",
            "ean8",
            "code128",
            "code39",
            "code93",
            "datamatrix",
          ],
        }}
        onBarcodeScanned={scanned ? undefined : handleBarCodeScanned}
      >
        {/* Overlay */}
        <View style={styles.overlay}>
          <View style={styles.scanFrame} />
          <Text style={styles.instruction}>
            {scanned ? "Código detectado" : "Apunta al código de barras o QR"}
          </Text>
        </View>
      </CameraView>

      {/* Result panel */}
      {scanned && scannedData && (
        <View style={styles.resultPanel}>
          <Text style={styles.resultLabel}>Código escaneado:</Text>
          <Text style={styles.resultValue}>{scannedData.data}</Text>
          <Text style={styles.resultType}>Tipo: {scannedData.type}</Text>
          {error ? <Text style={styles.errorText}>{error}</Text> : null}
          <View style={styles.resultActions}>
            <Pressable
              style={[styles.actionBtn, loading && styles.actionBtnDisabled]}
              onPress={handleUseCode}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#FFFFFF" size="small" />
              ) : (
                <Text style={styles.actionBtnText}>Buscar activo</Text>
              )}
            </Pressable>
            <Pressable style={[styles.actionBtn, styles.actionBtnSecondary]} onPress={handleScanAgain}>
              <Text style={styles.actionBtnTextSecondary}>Escanear otro</Text>
            </Pressable>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B111A",
  },
  center: {
    flex: 1,
    backgroundColor: "#0B111A",
    justifyContent: "center",
    alignItems: "center",
    padding: 30,
  },
  message: {
    color: "#A9B8D0",
    fontSize: 15,
    textAlign: "center",
    marginBottom: 20,
  },
  button: {
    backgroundColor: "#146CFF",
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 12,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
  },
  camera: {
    flex: 1,
  },
  overlay: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.3)",
  },
  scanFrame: {
    width: 250,
    height: 250,
    borderWidth: 3,
    borderColor: "#146CFF",
    borderRadius: 20,
    backgroundColor: "transparent",
  },
  instruction: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
    marginTop: 20,
    textAlign: "center",
  },
  resultPanel: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: "#121C2C",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    borderTopWidth: 1,
    borderColor: "#233650",
  },
  resultLabel: {
    color: "#7EA3D4",
    fontSize: 12,
    fontWeight: "600",
  },
  resultValue: {
    color: "#FFFFFF",
    fontSize: 18,
    fontWeight: "700",
    marginTop: 4,
  },
  resultType: {
    color: "#6B7A8F",
    fontSize: 12,
    marginTop: 4,
  },
  resultActions: {
    flexDirection: "row",
    gap: 12,
    marginTop: 16,
  },
  actionBtn: {
    flex: 1,
    backgroundColor: "#146CFF",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },
  actionBtnDisabled: {
    opacity: 0.6,
  },
  actionBtnText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 14,
  },
  actionBtnSecondary: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "#355F9E",
  },
  actionBtnTextSecondary: {
    color: "#7EA3D4",
    fontWeight: "700",
    fontSize: 14,
  },
  errorText: {
    color: "#FCA5A5",
    fontSize: 13,
    marginTop: 10,
  },
});
