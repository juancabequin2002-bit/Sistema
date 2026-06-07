import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import api from "../api";

export default function AssetDetailScreen({ route }) {
  const { assetId } = route.params;
  const [asset, setAsset] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAsset = useCallback(async () => {
    try {
      setError(null);
      const data = await api.getAssetById(assetId);
      setAsset(data);
    } catch (err) {
      setError(err.message || "Error al cargar activo");
    } finally {
      setLoading(false);
    }
  }, [assetId]);

  useEffect(() => {
    fetchAsset();
  }, [fetchAsset]);

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case "activo":
      case "active":
        return "#10B981";
      case "mantenimiento":
      case "maintenance":
        return "#F59E0B";
      case "baja":
      case "disposed":
        return "#EF4444";
      default:
        return "#6B7280";
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#146CFF" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  if (!asset) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Activo no encontrado</Text>
      </View>
    );
  }

  const status = asset.status || asset.estado || "Desconocido";

  const fields = [
    { label: "Codigo interno", value: asset.internal_code || asset.code || asset.codigo },
    { label: "Nombre", value: asset.name || asset.nombre },
    { label: "Tipo", value: asset.asset_type || asset.tipo },
    { label: "Categoria", value: asset.category || asset.categoria },
    { label: "Marca", value: asset.brand },
    { label: "Modelo", value: asset.model },
    { label: "Ubicacion", value: asset.location || asset.ubicacion },
    { label: "Estado", value: status },
    { label: "Responsable", value: asset.responsible_name || asset.assigned_to || asset.responsable },
    { label: "RFID", value: asset.rfid_code || asset.rfid_tag || asset.tag_rfid },
    { label: "NFC", value: asset.nfc_code },
    { label: "Codigo de barras", value: asset.barcode_code },
    { label: "Serial", value: asset.serial_number },
    { label: "Fecha alta", value: asset.created_at || asset.fecha_alta },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Status badge */}
      <View style={styles.statusRow}>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(status) + "22", borderColor: getStatusColor(status) }]}>
          <View style={[styles.statusDot, { backgroundColor: getStatusColor(status) }]} />
          <Text style={[styles.statusText, { color: getStatusColor(status) }]}>{status}</Text>
        </View>
      </View>

      {/* Title */}
      <Text style={styles.title}>{asset.name || asset.nombre || "Sin nombre"}</Text>

      {/* Fields */}
      <View style={styles.fieldsCard}>
        {fields.map((field) =>
          field.value ? (
            <View key={field.label} style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>{field.label}</Text>
              <Text style={styles.fieldValue}>{field.value}</Text>
            </View>
          ) : null
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B111A",
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  center: {
    flex: 1,
    backgroundColor: "#0B111A",
    justifyContent: "center",
    alignItems: "center",
  },
  statusRow: {
    flexDirection: "row",
    marginBottom: 12,
  },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    fontSize: 13,
    fontWeight: "700",
  },
  title: {
    color: "#FFFFFF",
    fontSize: 24,
    fontWeight: "800",
    marginBottom: 20,
  },
  fieldsCard: {
    backgroundColor: "#121C2C",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#233650",
    overflow: "hidden",
  },
  fieldRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#1E2D42",
  },
  fieldLabel: {
    color: "#7EA3D4",
    fontSize: 13,
    fontWeight: "600",
    flex: 1,
  },
  fieldValue: {
    color: "#FFFFFF",
    fontSize: 13,
    flex: 2,
    textAlign: "right",
  },
  errorText: {
    color: "#FCA5A5",
    fontSize: 14,
  },
});
