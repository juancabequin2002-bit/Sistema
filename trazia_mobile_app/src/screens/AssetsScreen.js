import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Platform,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import api from "../api";

export default function AssetsScreen({ navigation }) {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [query, setQuery] = useState("");
  const [error, setError] = useState(null);

  const fetchAssets = useCallback(async (searchQuery = "") => {
    try {
      setError(null);
      const data = await api.getAssets(searchQuery);
      setAssets(data || []);
    } catch (err) {
      setError(err.message || "Error al cargar activos");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchAssets(query);
    }, 400);
    return () => clearTimeout(timer);
  }, [query, fetchAssets]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchAssets(query);
  };

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

  const renderItem = ({ item }) => (
    <Pressable
      style={styles.assetCard}
      onPress={() => navigation.navigate("AssetDetail", { assetId: item.id })}
    >
      <View style={styles.assetHeader}>
        <Text style={styles.assetName} numberOfLines={1}>
          {item.name || item.nombre || "Sin nombre"}
        </Text>
        <View style={[styles.statusDot, { backgroundColor: getStatusColor(item.status || item.estado) }]} />
      </View>
      <Text style={styles.assetCode}>
        {item.internal_code || item.code || item.codigo || item.rfid_code || "-"}
      </Text>
      {(item.location || item.ubicacion) ? (
        <Text style={styles.assetLocation}>{item.location || item.ubicacion}</Text>
      ) : null}
    </Pressable>
  );

  return (
    <View style={styles.container}>
      {/* Search bar */}
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          value={query}
          onChangeText={setQuery}
          placeholder="Buscar activos..."
          placeholderTextColor="#6B7A8F"
          autoCapitalize="none"
          autoCorrect={false}
          clearButtonMode="while-editing"
        />
      </View>

      {/* Content */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#146CFF" />
        </View>
      ) : error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retryBtn} onPress={() => fetchAssets(query)}>
            <Text style={styles.retryText}>Reintentar</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={assets}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#146CFF" />
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyText}>No se encontraron activos</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B111A",
  },
  searchContainer: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  searchInput: {
    backgroundColor: "#121C2C",
    borderWidth: 1,
    borderColor: "#233650",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    color: "#FFFFFF",
    fontSize: 15,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 20,
  },
  assetCard: {
    backgroundColor: "#121C2C",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#233650",
    padding: 16,
    marginBottom: 10,
  },
  assetHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  assetName: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
    flex: 1,
    marginRight: 8,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  assetCode: {
    color: "#7EA3D4",
    fontSize: 13,
    marginTop: 4,
    fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
  },
  assetLocation: {
    color: "#6B7A8F",
    fontSize: 12,
    marginTop: 4,
  },
  empty: {
    paddingTop: 60,
    alignItems: "center",
  },
  emptyText: {
    color: "#6B7A8F",
    fontSize: 14,
  },
  errorBox: {
    margin: 20,
    backgroundColor: "#1E1111",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#7F1D1D",
    padding: 20,
    alignItems: "center",
  },
  errorText: {
    color: "#FCA5A5",
    fontSize: 14,
    textAlign: "center",
    marginBottom: 12,
  },
  retryBtn: {
    backgroundColor: "#146CFF",
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  retryText: {
    color: "#FFFFFF",
    fontWeight: "700",
  },
});
