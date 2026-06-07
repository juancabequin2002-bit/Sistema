import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useAuth } from "../context/AuthContext";

export default function LoginScreen({ onSwitchToRegister, onSwitchToForgotPassword }) {
  const { login, loading, error, clearError } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) return;
    await login(username.trim(), password);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.inner}>
        {/* Brand */}
        <View style={styles.brandSection}>
          <View style={styles.brandBadge}>
            <Text style={styles.brandBadgeText}>T</Text>
          </View>
          <Text style={styles.brandTitle}>TRAZIA RFID</Text>
          <Text style={styles.brandSubtitle}>
            Inventario {"·"} Custodia {"·"} Trazabilidad
          </Text>
        </View>

        {/* Form */}
        <View style={styles.form}>
          {error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <Text style={styles.label}>Usuario</Text>
          <TextInput
            style={styles.input}
            value={username}
            onChangeText={(text) => {
              clearError();
              setUsername(text);
            }}
            placeholder="Introduce tu usuario"
            placeholderTextColor="#6B7A8F"
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="next"
          />

          <Text style={styles.label}>Contraseña</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={(text) => {
              clearError();
              setPassword(text);
            }}
            placeholder="Introduce tu contraseña"
            placeholderTextColor="#6B7A8F"
            secureTextEntry
            returnKeyType="go"
            onSubmitEditing={handleLogin}
          />

          <Pressable
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.buttonText}>Iniciar Sesion</Text>
            )}
          </Pressable>

          <Pressable style={styles.linkButton} onPress={onSwitchToRegister}>
            <Text style={styles.linkText}>Crear una cuenta nueva</Text>
          </Pressable>

          <Pressable style={styles.linkButton} onPress={onSwitchToForgotPassword}>
            <Text style={styles.secondaryLinkText}>Olvide mi contrasena</Text>
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B111A",
  },
  inner: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 28,
  },
  brandSection: {
    alignItems: "center",
    marginBottom: 40,
  },
  brandBadge: {
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: "#111D2D",
    borderWidth: 2,
    borderColor: "#2A4C85",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  brandBadgeText: {
    color: "#FFFFFF",
    fontSize: 28,
    fontWeight: "800",
  },
  brandTitle: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "800",
    letterSpacing: 2,
  },
  brandSubtitle: {
    color: "#A9B8D0",
    fontSize: 12,
    marginTop: 4,
  },
  form: {
    width: "100%",
  },
  label: {
    color: "#A9B8D0",
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 6,
    marginTop: 16,
  },
  input: {
    backgroundColor: "#121C2C",
    borderWidth: 1,
    borderColor: "#233650",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    color: "#FFFFFF",
    fontSize: 15,
  },
  button: {
    backgroundColor: "#146CFF",
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 28,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
  errorBox: {
    backgroundColor: "#2D1111",
    borderWidth: 1,
    borderColor: "#DC2626",
    borderRadius: 10,
    padding: 12,
  },
  errorText: {
    color: "#FCA5A5",
    fontSize: 13,
    textAlign: "center",
  },
  linkButton: {
    marginTop: 16,
    alignItems: "center",
  },
  linkText: {
    color: "#146CFF",
    fontSize: 14,
    fontWeight: "600",
  },
  secondaryLinkText: {
    color: "#A9B8D0",
    fontSize: 13,
    fontWeight: "600",
  },
});
