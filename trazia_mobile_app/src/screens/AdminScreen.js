import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import api from "../api";

const initialAsset = {
  internal_code: "",
  name: "",
  asset_type: "Equipo de computo",
  identification_technology: "nfc",
  status: "activo",
  rfid_code: "",
  nfc_code: "",
  barcode_code: "",
  category: "",
  brand: "",
  model: "",
  responsible_name: "",
  location_id: "",
  observations: "",
};

const initialUser = {
  full_name: "",
  username: "",
  email: "",
  password: "",
  role: "consulta",
  is_active_user: true,
};

const initialLocation = {
  name: "",
  description: "",
};

const initialMaintenance = {
  asset_id: "",
  maintenance_type: "preventivo",
  maintenance_date: new Date().toISOString().slice(0, 10),
  technician_name: "",
  description: "",
  cost: "",
  next_maintenance_date: "",
};

function Field({ label, value, onChangeText, placeholder, secureTextEntry, keyboardType, multiline }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && styles.textArea]}
        value={String(value ?? "")}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#6B7A8F"
        secureTextEntry={secureTextEntry}
        keyboardType={keyboardType}
        multiline={multiline}
        autoCapitalize="none"
      />
    </View>
  );
}

function ChoiceGroup({ label, value, options, onChange, display = (item) => item }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.choices}>
        {options.map((option) => {
          const optionValue = typeof option === "object" ? option.value : option;
          const selected = String(value) === String(optionValue);
          return (
            <Pressable
              key={String(optionValue)}
              style={[styles.choice, selected && styles.choiceSelected]}
              onPress={() => onChange(optionValue)}
            >
              <Text style={[styles.choiceText, selected && styles.choiceTextSelected]}>
                {display(option)}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

function SectionTabs({ active, onChange }) {
  const tabs = [
    ["asset", "Activo"],
    ["user", "Usuario"],
    ["maintenance", "Mantenimiento"],
    ["location", "Ubicacion"],
  ];
  return (
    <View style={styles.tabs}>
      {tabs.map(([key, label]) => (
        <Pressable
          key={key}
          style={[styles.tab, active === key && styles.tabActive]}
          onPress={() => onChange(key)}
        >
          <Text style={[styles.tabText, active === key && styles.tabTextActive]}>{label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export default function AdminScreen() {
  const [active, setActive] = useState("asset");
  const [options, setOptions] = useState(null);
  const [users, setUsers] = useState([]);
  const [maintenances, setMaintenances] = useState([]);
  const [asset, setAsset] = useState(initialAsset);
  const [user, setUser] = useState(initialUser);
  const [location, setLocation] = useState(initialLocation);
  const [maintenance, setMaintenance] = useState(initialMaintenance);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const loadAdminData = useCallback(async () => {
    try {
      setError(null);
      const [nextOptions, nextUsers, nextMaintenances] = await Promise.all([
        api.getAdminOptions(),
        api.getUsers(),
        api.getMaintenances(),
      ]);
      setOptions(nextOptions);
      setUsers(nextUsers);
      setMaintenances(nextMaintenances);
      setAsset((prev) => ({
        ...prev,
        asset_type: prev.asset_type || nextOptions.asset_types?.[0] || "Equipo de computo",
        status: prev.status || nextOptions.asset_statuses?.[0] || "activo",
        identification_technology:
          prev.identification_technology || nextOptions.identification_technologies?.[0] || "nfc",
      }));
      setMaintenance((prev) => ({
        ...prev,
        asset_id: prev.asset_id || nextOptions.assets?.[0]?.id || "",
        maintenance_type: prev.maintenance_type || nextOptions.maintenance_types?.[0] || "preventivo",
      }));
    } catch (err) {
      setError(err.message || "No se pudo cargar administracion");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAdminData();
  }, [loadAdminData]);

  const locationChoices = useMemo(() => {
    const list = options?.locations || [];
    return [{ value: "", label: "Sin ubicacion" }, ...list.map((item) => ({ value: item.id, label: item.name }))];
  }, [options]);

  const assetChoices = useMemo(() => {
    return (options?.assets || []).map((item) => ({
      value: item.id,
      label: `${item.internal_code || item.id} - ${item.name}`,
    }));
  }, [options]);

  const submit = async (kind) => {
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      if (kind === "asset") {
        const payload = { ...asset, location_id: asset.location_id || null };
        const created = await api.createAsset(payload);
        setMessage(`Activo creado: ${created.internal_code}`);
        setAsset(initialAsset);
      }
      if (kind === "user") {
        const created = await api.createUser(user);
        setMessage(`Usuario creado: ${created.username}`);
        setUser(initialUser);
      }
      if (kind === "location") {
        const created = await api.createLocation(location);
        setMessage(`Ubicacion creada: ${created.name}`);
        setLocation(initialLocation);
      }
      if (kind === "maintenance") {
        const created = await api.createMaintenance({
          ...maintenance,
          asset_id: Number(maintenance.asset_id),
          cost: maintenance.cost || null,
          next_maintenance_date: maintenance.next_maintenance_date || null,
        });
        setMessage(`Mantenimiento registrado: ${created.asset_code || created.asset_name}`);
        setMaintenance(initialMaintenance);
      }
      await loadAdminData();
    } catch (err) {
      setError(err.message || "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#146CFF" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Administracion</Text>
      <SectionTabs active={active} onChange={setActive} />

      {message ? <Text style={styles.success}>{message}</Text> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      {active === "asset" ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Crear activo</Text>
          <Field label="Codigo interno" value={asset.internal_code} onChangeText={(v) => setAsset({ ...asset, internal_code: v })} placeholder="ACT-001" />
          <Field label="Nombre" value={asset.name} onChangeText={(v) => setAsset({ ...asset, name: v })} placeholder="Portatil Dell" />
          <ChoiceGroup label="Tipo" value={asset.asset_type} options={options?.asset_types || []} onChange={(v) => setAsset({ ...asset, asset_type: v })} />
          <ChoiceGroup label="Tecnologia" value={asset.identification_technology} options={options?.identification_technologies || []} onChange={(v) => setAsset({ ...asset, identification_technology: v })} />
          <ChoiceGroup label="Estado" value={asset.status} options={options?.asset_statuses || []} onChange={(v) => setAsset({ ...asset, status: v })} />
          <ChoiceGroup label="Ubicacion" value={asset.location_id} options={locationChoices} onChange={(v) => setAsset({ ...asset, location_id: v })} display={(item) => item.label} />
          <Field label="RFID" value={asset.rfid_code} onChangeText={(v) => setAsset({ ...asset, rfid_code: v })} placeholder="Opcional; se genera virtual si queda vacio" />
          <Field label="NFC" value={asset.nfc_code} onChangeText={(v) => setAsset({ ...asset, nfc_code: v })} placeholder="UID NFC o texto del tag" />
          <Field label="Codigo de barras" value={asset.barcode_code} onChangeText={(v) => setAsset({ ...asset, barcode_code: v })} placeholder="Opcional" />
          <Field label="Marca" value={asset.brand} onChangeText={(v) => setAsset({ ...asset, brand: v })} placeholder="Marca" />
          <Field label="Modelo" value={asset.model} onChangeText={(v) => setAsset({ ...asset, model: v })} placeholder="Modelo" />
          <Field label="Responsable" value={asset.responsible_name} onChangeText={(v) => setAsset({ ...asset, responsible_name: v })} placeholder="Nombre responsable" />
          <Field label="Observaciones" value={asset.observations} onChangeText={(v) => setAsset({ ...asset, observations: v })} multiline />
          <Pressable style={[styles.primaryBtn, saving && styles.disabled]} onPress={() => submit("asset")} disabled={saving}>
            <Text style={styles.primaryText}>{saving ? "Guardando..." : "Crear activo"}</Text>
          </Pressable>
        </View>
      ) : null}

      {active === "user" ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Crear usuario</Text>
          <Field label="Nombre completo" value={user.full_name} onChangeText={(v) => setUser({ ...user, full_name: v })} />
          <Field label="Usuario" value={user.username} onChangeText={(v) => setUser({ ...user, username: v })} />
          <Field label="Correo" value={user.email} onChangeText={(v) => setUser({ ...user, email: v })} keyboardType="email-address" />
          <Field label="Contrasena temporal" value={user.password} onChangeText={(v) => setUser({ ...user, password: v })} secureTextEntry />
          <ChoiceGroup label="Rol" value={user.role} options={options?.roles || []} onChange={(v) => setUser({ ...user, role: v })} />
          <ChoiceGroup
            label="Estado"
            value={user.is_active_user ? "true" : "false"}
            options={[{ value: "true", label: "Activo" }, { value: "false", label: "Inactivo" }]}
            onChange={(v) => setUser({ ...user, is_active_user: v === "true" })}
            display={(item) => item.label}
          />
          <Pressable style={[styles.primaryBtn, saving && styles.disabled]} onPress={() => submit("user")} disabled={saving}>
            <Text style={styles.primaryText}>{saving ? "Guardando..." : "Crear usuario"}</Text>
          </Pressable>
          <Text style={styles.listTitle}>Usuarios recientes</Text>
          {users.slice(0, 5).map((item) => (
            <Text key={item.id} style={styles.listItem}>{item.username} - {item.role}</Text>
          ))}
        </View>
      ) : null}

      {active === "maintenance" ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Registrar mantenimiento</Text>
          <ChoiceGroup label="Activo" value={maintenance.asset_id} options={assetChoices} onChange={(v) => setMaintenance({ ...maintenance, asset_id: v })} display={(item) => item.label} />
          <ChoiceGroup label="Tipo" value={maintenance.maintenance_type} options={options?.maintenance_types || []} onChange={(v) => setMaintenance({ ...maintenance, maintenance_type: v })} />
          <Field label="Fecha" value={maintenance.maintenance_date} onChangeText={(v) => setMaintenance({ ...maintenance, maintenance_date: v })} placeholder="YYYY-MM-DD" />
          <Field label="Tecnico" value={maintenance.technician_name} onChangeText={(v) => setMaintenance({ ...maintenance, technician_name: v })} />
          <Field label="Descripcion" value={maintenance.description} onChangeText={(v) => setMaintenance({ ...maintenance, description: v })} multiline />
          <Field label="Costo" value={maintenance.cost} onChangeText={(v) => setMaintenance({ ...maintenance, cost: v })} keyboardType="decimal-pad" />
          <Field label="Proximo mantenimiento" value={maintenance.next_maintenance_date} onChangeText={(v) => setMaintenance({ ...maintenance, next_maintenance_date: v })} placeholder="YYYY-MM-DD" />
          <Pressable style={[styles.primaryBtn, saving && styles.disabled]} onPress={() => submit("maintenance")} disabled={saving || !maintenance.asset_id}>
            <Text style={styles.primaryText}>{saving ? "Guardando..." : "Registrar mantenimiento"}</Text>
          </Pressable>
          <Text style={styles.listTitle}>Ultimos mantenimientos</Text>
          {maintenances.slice(0, 5).map((item) => (
            <Text key={item.id} style={styles.listItem}>{item.asset_code || item.asset_name} - {item.maintenance_type}</Text>
          ))}
        </View>
      ) : null}

      {active === "location" ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Crear ubicacion</Text>
          <Field label="Nombre" value={location.name} onChangeText={(v) => setLocation({ ...location, name: v })} />
          <Field label="Descripcion" value={location.description} onChangeText={(v) => setLocation({ ...location, description: v })} multiline />
          <Pressable style={[styles.primaryBtn, saving && styles.disabled]} onPress={() => submit("location")} disabled={saving}>
            <Text style={styles.primaryText}>{saving ? "Guardando..." : "Crear ubicacion"}</Text>
          </Pressable>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0B111A",
  },
  content: {
    padding: 16,
    paddingBottom: 36,
  },
  center: {
    flex: 1,
    backgroundColor: "#0B111A",
    justifyContent: "center",
    alignItems: "center",
  },
  title: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "800",
    marginBottom: 14,
  },
  tabs: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 14,
  },
  tab: {
    backgroundColor: "#121C2C",
    borderColor: "#233650",
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  tabActive: {
    backgroundColor: "#146CFF",
    borderColor: "#146CFF",
  },
  tabText: {
    color: "#A9B8D0",
    fontWeight: "700",
    fontSize: 12,
  },
  tabTextActive: {
    color: "#FFFFFF",
  },
  card: {
    backgroundColor: "#121C2C",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#233650",
    padding: 14,
  },
  cardTitle: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "800",
    marginBottom: 12,
  },
  field: {
    marginBottom: 12,
  },
  label: {
    color: "#7EA3D4",
    fontSize: 12,
    fontWeight: "700",
    marginBottom: 6,
  },
  input: {
    backgroundColor: "#0B111A",
    borderWidth: 1,
    borderColor: "#233650",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 11,
    color: "#FFFFFF",
    fontSize: 14,
  },
  textArea: {
    minHeight: 82,
    textAlignVertical: "top",
  },
  choices: {
    gap: 8,
  },
  choice: {
    backgroundColor: "#0B111A",
    borderColor: "#233650",
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  choiceSelected: {
    backgroundColor: "#163B73",
    borderColor: "#146CFF",
  },
  choiceText: {
    color: "#A9B8D0",
    fontSize: 12,
    fontWeight: "700",
  },
  choiceTextSelected: {
    color: "#FFFFFF",
  },
  primaryBtn: {
    backgroundColor: "#146CFF",
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: "center",
    marginTop: 4,
  },
  disabled: {
    opacity: 0.6,
  },
  primaryText: {
    color: "#FFFFFF",
    fontWeight: "800",
  },
  success: {
    color: "#A7F3D0",
    backgroundColor: "#0F2A1F",
    borderColor: "#14532D",
    borderWidth: 1,
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
  },
  error: {
    color: "#FCA5A5",
    backgroundColor: "#2D1111",
    borderColor: "#7F1D1D",
    borderWidth: 1,
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
  },
  listTitle: {
    color: "#FFFFFF",
    fontWeight: "800",
    marginTop: 18,
    marginBottom: 8,
  },
  listItem: {
    color: "#A9B8D0",
    fontSize: 13,
    paddingVertical: 5,
  },
});
