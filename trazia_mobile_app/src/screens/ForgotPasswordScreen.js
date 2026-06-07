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

export default function ForgotPasswordScreen({ onSwitchToLogin }) {
  const { forgotPassword, loading, error, clearError } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [message, setMessage] = useState(null);

  const handleRecover = async () => {
    if (!identifier.trim()) return;
    const result = await forgotPassword(identifier.trim());
    if (result) {
      setMessage(result.message || "Si la cuenta existe, enviaremos una contrasena temporal.");
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.inner}>
        <View style={styles.brandBadge}>
          <Text style={styles.brandBadgeText}>T</Text>
        </View>
        <Text style={styles.title}>Recuperar acceso</Text>
        <Text style={styles.subtitle}>
          Ingresa tu usuario o correo registrado. Recibiras una contrasena temporal y deberas cambiarla al iniciar sesion.
        </Text>

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        {message ? (
          <View style={styles.successBox}>
            <Text style={styles.successText}>{message}</Text>
          </View>
        ) : null}

        <Text style={styles.label}>Usuario o correo</Text>
        <TextInput
          style={styles.input}
          value={identifier}
          onChangeText={(text) => {
            clearError();
            setMessage(null);
            setIdentifier(text);
          }}
          placeholder="sara15 o sara@empresa.com"
          placeholderTextColor="#6B7A8F"
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          returnKeyType="send"
          onSubmitEditing={handleRecover}
        />

        <Pressable
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleRecover}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.buttonText}>Enviar temporal</Text>
          )}
        </Pressable>

        <Pressable style={styles.linkButton} onPress={onSwitchToLogin}>
          <Text style={styles.linkText}>Volver a iniciar sesion</Text>
        </Pressable>
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
  brandBadge: {
    alignSelf: "center",
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: "#111D2D",
    borderWidth: 2,
    borderColor: "#2A4C85",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 18,
  },
  brandBadgeText: {
    color: "#FFFFFF",
    fontSize: 28,
    fontWeight: "800",
  },
  title: {
    color: "#FFFFFF",
    fontSize: 24,
    fontWeight: "800",
    textAlign: "center",
  },
  subtitle: {
    color: "#A9B8D0",
    fontSize: 14,
    lineHeight: 20,
    marginTop: 10,
    marginBottom: 24,
    textAlign: "center",
  },
  label: {
    color: "#A9B8D0",
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 6,
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
    marginTop: 24,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
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
  errorBox: {
    backgroundColor: "#2D1111",
    borderWidth: 1,
    borderColor: "#DC2626",
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  errorText: {
    color: "#FCA5A5",
    fontSize: 13,
    textAlign: "center",
  },
  successBox: {
    backgroundColor: "#0F2A1B",
    borderWidth: 1,
    borderColor: "#10B981",
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  successText: {
    color: "#86EFAC",
    fontSize: 13,
    textAlign: "center",
  },
});
