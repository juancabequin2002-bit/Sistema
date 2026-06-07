import React, { createContext, useContext, useState, useCallback } from "react";
import api from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mustChangePassword, setMustChangePassword] = useState(false);

  const login = useCallback(async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.login(username, password);
      const userData = result.data || { username };
      setUser(userData);
      setMustChangePassword(!!userData.must_change_password);
      return true;
    } catch (err) {
      setError(err.message || "Error de autenticacion");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (full_name, username, email, password, confirm_password) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.register(full_name, username, email, password, confirm_password);
      setUser(data.data || { username });
      setMustChangePassword(!!data.data?.must_change_password);
      return true;
    } catch (err) {
      setError(err.message || "Error al registrar");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch (_) {
      // Ignore logout errors
    }
    setUser(null);
    setMustChangePassword(false);
  }, []);

  const forgotPassword = useCallback(async (identifier) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.forgotPassword(identifier);
      return result.data || result;
    } catch (err) {
      setError(err.message || "Error de recuperacion");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const changePassword = useCallback(async (currentPassword, newPassword, confirmPassword) => {
    setLoading(true);
    setError(null);
    try {
      const userData = await api.changePassword(currentPassword, newPassword, confirmPassword);
      setUser((prev) => ({ ...(prev || {}), ...(userData || {}), must_change_password: false }));
      setMustChangePassword(false);
      return true;
    } catch (err) {
      setError(err.message || "Error al cambiar contrasena");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    mustChangePassword,
    login,
    register,
    forgotPassword,
    changePassword,
    logout,
    clearError: () => setError(null),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
