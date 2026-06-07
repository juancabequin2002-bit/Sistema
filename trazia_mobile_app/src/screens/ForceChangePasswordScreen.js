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

export default function ForceChangePasswordScreen() {
  const { changePassword, logout, loading, error, clearError } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleChange = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) return;
    await changePassword(currentPassword, newPassword, confirmPassword);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.inner}>
        <Text style={styles.title}>Cambio obligatorio</Text>
        <Text style={styles.subtitle}>
          Ingresaste con una contrasena temporal. Crea una nueva clave para continuar.
        </Text>

        {error ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        <Text style={styles.label}>Contrasena temporal</Text>
        <TextInput
          style={styles.input}
          value={currentPassword}
          onChangeText={(text) => {
            clearError();
            setCurrentPassword(text);
          }}
          placeholder="Temporal recibida"
          placeholderTextColor="#6B7A8F"
          secureTextEntry
          returnKeyType="next"
        />

        <Text style={styles.label}>Nueva contrasena</Text>
        <TextInput
          style={styles.input}
          value={newPassword}
          onChangeText={(text) => {
            clearError();
            setNewPassword(text);
          }}
          placeholder="Minimo 8 caracteres"
          placeholderTextColor="#6B7A8F"
          secureTextEntry
          returnKeyType="next"
        />

        <Text style={styles.label}>Confirmar nueva contrasena</Text>
        <TextInput
          style={styles.input}
          value={confirmPassword}
          onChangeText={(text) => {
            clearError();
            setConfirmPassword(text);
          }}
          placeholder="Repite la nueva contrasena"
          placeholderTextColor="#6B7A8F"
          secureTextEntry
          returnKeyType="go"
          onSubmitEditing={handleChange}
        />

        {newPassword && confirmPassword && newPassword !== confirmPassword ? (
          <Text style={styles.mismatchText}>Las contrasenas no coinciden</Text>
        ) : null}

        <Pressable
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleChange}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.buttonText}>Cambiar y continuar</Text>
          )}
        </Pressable>

        <Pressable style={styles.linkButton} onPress={logout}>
          <Text style={styles.linkText}>Salir</Text>
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
    marginTop: 14,
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
    color: "#FCA5A5",
    fontSize: 14,
    fontWeight: "600",
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
  mismatchText: {
    color: "#FCA5A5",
    fontSize: 12,
    marginTop: 6,
  },
});
