import React, { useState } from "react";
import { Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import { AuthProvider, useAuth } from "./src/context/AuthContext";
import NetworkBanner from "./src/components/NetworkBanner";
import LoginScreen from "./src/screens/LoginScreen";
import RegisterScreen from "./src/screens/RegisterScreen";
import ForgotPasswordScreen from "./src/screens/ForgotPasswordScreen";
import ForceChangePasswordScreen from "./src/screens/ForceChangePasswordScreen";
import DashboardScreen from "./src/screens/DashboardScreen";
import AssetsScreen from "./src/screens/AssetsScreen";
import AssetDetailScreen from "./src/screens/AssetDetailScreen";
import ScannerScreen from "./src/screens/ScannerScreen";
import NfcScreen from "./src/screens/NfcScreen";
import AdminScreen from "./src/screens/AdminScreen";

const Tab = createBottomTabNavigator();
const AssetsStack = createNativeStackNavigator();

const screenHeaderOptions = {
  headerStyle: { backgroundColor: "#0B111A" },
  headerTintColor: "#FFFFFF",
  headerTitleStyle: { fontWeight: "700" },
};

// Stack navigator for Assets -> Asset Detail
function AssetsStackNavigator() {
  return (
    <AssetsStack.Navigator screenOptions={screenHeaderOptions}>
      <AssetsStack.Screen
        name="AssetsList"
        component={AssetsScreen}
        options={{ title: "Activos" }}
      />
      <AssetsStack.Screen
        name="AssetDetail"
        component={AssetDetailScreen}
        options={{ title: "Detalle del Activo" }}
      />
    </AssetsStack.Navigator>
  );
}

// Simple text-based tab icon component
function TabIcon({ emoji }) {
  return <Text style={{ fontSize: 20 }}>{emoji}</Text>;
}

// Main tab navigator (shown when authenticated)
function MainTabs() {
  const { user } = useAuth();
  const isAdmin = user?.role === "administrador";

  return (
    <Tab.Navigator
      screenOptions={{
        tabBarStyle: {
          backgroundColor: "#0B111A",
          borderTopColor: "#1E2D42",
          borderTopWidth: 1,
          height: 60,
          paddingBottom: 8,
          paddingTop: 4,
        },
        tabBarActiveTintColor: "#146CFF",
        tabBarInactiveTintColor: "#6B7A8F",
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
        },
        ...screenHeaderOptions,
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: "Inicio",
          tabBarIcon: () => <TabIcon emoji={"🏠"} />,
        }}
      />
      <Tab.Screen
        name="Assets"
        component={AssetsStackNavigator}
        options={{
          title: "Activos",
          headerShown: false,
          tabBarIcon: () => <TabIcon emoji={"📦"} />,
        }}
      />
      <Tab.Screen
        name="Scanner"
        component={ScannerScreen}
        options={{
          title: "Escáner",
          tabBarIcon: () => <TabIcon emoji={"📷"} />,
        }}
      />
      <Tab.Screen
        name="NFC"
        component={NfcScreen}
        options={{
          title: "NFC",
          tabBarIcon: () => <TabIcon emoji={"📶"} />,
        }}
      />
      {isAdmin ? (
        <Tab.Screen
          name="Admin"
          component={AdminScreen}
          options={{
            title: "Admin",
            tabBarIcon: () => <TabIcon emoji={"ADM"} />,
          }}
        />
      ) : null}
    </Tab.Navigator>
  );
}

// Auth screens: toggle between Login and Register
function AuthScreens() {
  const [mode, setMode] = useState("login");

  if (mode === "register") {
    return <RegisterScreen onSwitchToLogin={() => setMode("login")} />;
  }
  if (mode === "forgot") {
    return <ForgotPasswordScreen onSwitchToLogin={() => setMode("login")} />;
  }
  return (
    <LoginScreen
      onSwitchToRegister={() => setMode("register")}
      onSwitchToForgotPassword={() => setMode("forgot")}
    />
  );
}

// Root component: show Auth or Main based on auth state
function RootNavigator() {
  const { isAuthenticated, mustChangePassword } = useAuth();

  if (isAuthenticated && mustChangePassword) {
    return <ForceChangePasswordScreen />;
  }

  return (
    <NavigationContainer>
      {isAuthenticated ? <MainTabs /> : <AuthScreens />}
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <StatusBar style="light" />
        <NetworkBanner />
        <RootNavigator />
      </AuthProvider>
    </SafeAreaProvider>
  );
}
