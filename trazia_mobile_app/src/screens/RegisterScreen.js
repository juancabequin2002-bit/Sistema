import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useAuth } from "../context/AuthContext";

export default function RegisterScreen({ onSwitchToLogin }) {
  const { register, loading, error, clearError } = useAuth();
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleRegister = async () => {
    if (!fullName.trim() || !username.trim() || !email.trim() || !password || !confirmPassword) return;
    if (password !== confirmPassword) return;
    await register(fullName.trim(), username.trim(), email.trim(), password, confirmPassword);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView contentContainerStyle={styles.inner} keyboardShouldPersistTaps="handled">
        <View style={styles.brandSection}>
          <View style={styles.brandBadge}>
            <Text style={styles.brandBadgeText}>T</Text>
          </View>
          <Text style={styles.brandTitle}>TRAZIA RFID</Text>
          <Text style={styles.brandSubtitle}>Crear cuenta nueva</Text>
        </View>

        <View style={styles.form}>
          {error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <Text style={styles.label}>Nombre completo</Text>
          <TextInput
            style={styles.input}
            value={fullName}
            onChangeText={(text) => { clearError(); setFullName(text); }}
            placeholder="Tu nombre completo"
            placeholderTextColor="#6B7A8F"
            autoCapitalize="words"
            returnKeyType="next"
          />

          <Text style={styles.label}>Usuario</Text>
          <TextInput
            style={styles.input}
            value={username}
            onChangeText={(text) => { clearError(); setUsername(text); }}
            placeholder="nombre.usuario"
            placeholderTextColor="#6B7A8F"
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="next"
          />

          <Text style={styles.label}>Correo electronico</Text>
          <TextInput
            style={styles.input}
            value={email}
            onChangeText={(text) => { clearError(); setEmail(text); }}
            placeholder="tu@correo.com"
            placeholderTextColor="#6B7A8F"
            autoCapitalize="none"
            keyboardType="email-address"
            returnKeyType="next"
          />

          <Text style={styles.label}>Contrasena</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={(text) => { clearError(); setPassword(text); }}
            placeholder="Minimo 8 caracteres"
            placeholderTextColor="#6B7A8F"
            secureTextEntry
            returnKeyType="next"
          />

          <Text style={styles.label}>Confirmar contrasena</Text>
          <TextInput
            style={styles.input}
            value={confirmPassword}
            onChangeText={(text) => { clearError(); setConfirmPassword(text); }}
            placeholder="Repite tu contrasena"
            placeholderTextColor="#6B7A8F"
            secureTextEntry
            returnKeyType="go"
            onSubmitEditing={handleRegister}
          />

          {password && confirmPassword && password !== confirmPassword ? (
            <Text style={styles.mismatchText}>Las contrasenas no coinciden</Text>
          ) : null}

          <Pressable
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleRegister}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.buttonText}>Crear cuenta</Text>
            )}
          </Pressable>

          <Pressable style={styles.linkButton} onPress={onSwitchToLogin}>
            <Text style={styles.linkText}>Ya tengo una cuenta - Iniciar sesion</Text>
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B111A",
  },
  inner: {
    flexGrow: 1,
    justifyContent: "center",
    paddingHorizontal: 28,
    paddingVertical: 40,
  },
  brandSection: {
    alignItems: "center",
    marginBottom: 30,
  },
  brandBadge: {
    width: 56,
    height: 56,
    borderRadius: 18,
    backgroundColor: "#111D2D",
    borderWidth: 2,
    borderColor: "#2A4C85",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  brandBadgeText: {
    color: "#FFFFFF",
    fontSize: 24,
    fontWeight: "800",
  },
  brandTitle: {
    color: "#FFFFFF",
    fontSize: 20,
    fontWeight: "800",
    letterSpacing: 2,
  },
  brandSubtitle: {
    color: "#A9B8D0",
    fontSize: 13,
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
