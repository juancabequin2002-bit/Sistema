import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useAuth } from "../context/AuthContext";
import api from "../api";

export default function DashboardScreen() {
  const { user, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchDashboard = useCallback(async () => {
    try {
      setError(null);
      const response = await api.getDashboard();
      setStats(response.data || response);
    } catch (err) {
      setError(err.message || "Error al cargar datos");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchDashboard();
  };

  const kpis = stats
    ? [
        { label: "Total Activos", value: stats.total_assets ?? 0, color: "#146CFF" },
        { label: "Activos", value: stats.active_assets ?? 0, color: "#10B981" },
        { label: "Mantenimiento", value: stats.maintenance_assets ?? 0, color: "#F59E0B" },
        { label: "Dados de baja", value: stats.disposed_assets ?? 0, color: "#EF4444" },
      ]
    : [];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#146CFF" />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Hola, {user?.username || "Usuario"}</Text>
          <Text style={styles.subtitle}>Panel de control</Text>
        </View>
        <Pressable style={styles.logoutBtn} onPress={logout}>
          <Text style={styles.logoutText}>Salir</Text>
        </Pressable>
      </View>

      {/* Content */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#146CFF" />
        </View>
      ) : error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retryBtn} onPress={fetchDashboard}>
            <Text style={styles.retryText}>Reintentar</Text>
          </Pressable>
        </View>
      ) : (
        <View style={styles.grid}>
          {kpis.map((kpi) => (
            <View key={kpi.label} style={styles.card}>
              <View style={[styles.indicator, { backgroundColor: kpi.color }]} />
              <Text style={styles.cardValue}>{kpi.value}</Text>
              <Text style={styles.cardLabel}>{kpi.label}</Text>
            </View>
          ))}
        </View>
      )}
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
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 28,
  },
  greeting: {
    color: "#FFFFFF",
    fontSize: 20,
    fontWeight: "800",
  },
  subtitle: {
    color: "#A9B8D0",
    fontSize: 13,
    marginTop: 2,
  },
  logoutBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: "#1E293B",
    borderWidth: 1,
    borderColor: "#334155",
  },
  logoutText: {
    color: "#EF4444",
    fontWeight: "700",
    fontSize: 13,
  },
  center: {
    paddingTop: 60,
    alignItems: "center",
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 14,
  },
  card: {
    width: "47%",
    backgroundColor: "#121C2C",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#233650",
    padding: 18,
  },
  indicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginBottom: 12,
  },
  cardValue: {
    color: "#FFFFFF",
    fontSize: 28,
    fontWeight: "800",
  },
  cardLabel: {
    color: "#A9B8D0",
    fontSize: 12,
    marginTop: 4,
  },
  errorBox: {
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
