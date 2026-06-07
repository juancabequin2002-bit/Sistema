/**
 * API client for TRAZIA RFID backend.
 * Uses token-based auth for React Native compatibility.
 */

const BASE_URL = process.env.EXPO_PUBLIC_WEB_URL || "http://192.168.1.10:5000";
const REQUEST_TIMEOUT_MS = 10000;

class ApiClient {
  constructor() {
    this.baseUrl = BASE_URL;
    this.authToken = null;
  }

  setToken(token) {
    this.authToken = token;
  }

  clearToken() {
    this.authToken = null;
  }

  _headers() {
    const headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (this.authToken) {
      headers["X-Mobile-Token"] = this.authToken;
    }
    return headers;
  }

  async request(method, path, body = null) {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    const options = {
      method,
      headers: this._headers(),
      signal: controller.signal,
    };
    if (body) {
      options.body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(url, options);
    } catch (err) {
      if (err.name === "AbortError") {
        throw new Error(`No hubo respuesta del servidor (${this.baseUrl}). Revisa la IP y que Flask este encendido.`);
      }
      throw new Error(`No se pudo conectar con el servidor (${this.baseUrl}). Revisa la Wi-Fi, IP y puerto.`);
    } finally {
      clearTimeout(timeoutId);
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error(errorData.message || errorData.error || `HTTP ${response.status}`);
      error.status = response.status;
      error.data = errorData;
      throw error;
    }

    return response.json().catch(() => {
      throw new Error("El servidor respondio, pero no envio JSON valido.");
    });
  }

  // ─── Auth ───────────────────────────────────────────────

  async login(username, password) {
    const result = await this.request("POST", "/api/auth/login", { username, password });
    if (result.ok && result.data && result.data.token) {
      this.setToken(result.data.token);
    }
    return result;
  }

  async register(full_name, username, email, password, confirm_password) {
    const result = await this.request("POST", "/api/auth/register", {
      full_name, username, email, password, confirm_password,
    });
    if (result.ok && result.data && result.data.token) {
      this.setToken(result.data.token);
    }
    return result;
  }

  async forgotPassword(identifier) {
    const value = String(identifier || "").trim();
    const payload = value.includes("@") ? { email: value } : { username: value };
    return this.request("POST", "/api/auth/forgot-password", payload);
  }

  async changePassword(current_password, new_password, confirm_password) {
    const result = await this.request("POST", "/api/auth/change-password", {
      current_password,
      new_password,
      confirm_password,
    });
    return result.data;
  }

  async logout() {
    try {
      await this.request("POST", "/api/auth/logout");
    } catch (_) {}
    this.clearToken();
  }

  // ─── Dashboard ──────────────────────────────────────────

  async getDashboard() {
    const result = await this.request("GET", "/api/dashboard");
    return result.data;
  }

  // ─── Assets ─────────────────────────────────────────────

  async getAssets(query = "") {
    const path = query ? `/api/assets?q=${encodeURIComponent(query)}` : "/api/assets";
    const result = await this.request("GET", path);
    return result.data || [];
  }

  async getAssetById(id) {
    const result = await this.request("GET", `/api/assets/${id}`);
    return result.data;
  }

  async scanCode(type, code) {
    const result = await this.request("POST", "/api/assets/scan", { identifier_type: type, code });
    return result.data;
  }

  async getAssetByCode(code, preferredType = "rfid") {
    const types = [preferredType, "rfid", "nfc", "barcode"].filter(
      (type, index, all) => type && all.indexOf(type) === index
    );
    let lastError = null;

    for (const type of types) {
      try {
        return await this.scanCode(type, code);
      } catch (err) {
        lastError = err;
        if (err.status && err.status !== 404) {
          throw err;
        }
      }
    }

    if (lastError) {
      throw lastError;
    }
    throw new Error("No se encontro un activo con ese codigo.");
  }

  async getAssetFromScan(rawCode, scannerType = "") {
    const code = String(rawCode || "").trim();
    if (!code) {
      throw new Error("Codigo vacio.");
    }

    const assetIdFromUrl = code.match(/\/activos\/(\d+)(?:\D|$)/i)?.[1];
    if (assetIdFromUrl) {
      return this.getAssetById(assetIdFromUrl);
    }

    if (/^\d+$/.test(code)) {
      try {
        return await this.getAssetById(code);
      } catch (err) {
        if (err.status && err.status !== 404) {
          throw err;
        }
      }
    }

    const normalizedType = String(scannerType || "").toLowerCase();
    const preferredType =
      normalizedType.includes("qr") ? "barcode" :
      normalizedType.includes("bar") || normalizedType.includes("ean") || normalizedType.includes("code") ? "barcode" :
      "rfid";

    return this.getAssetByCode(code, preferredType);
  }

  // Admin

  async getAdminOptions() {
    const result = await this.request("GET", "/api/admin/options");
    return result.data;
  }

  async getUsers() {
    const result = await this.request("GET", "/api/admin/users");
    return result.data || [];
  }

  async createUser(payload) {
    const result = await this.request("POST", "/api/admin/users", payload);
    return result.data;
  }

  async updateUser(id, payload) {
    const result = await this.request("PUT", `/api/admin/users/${id}`, payload);
    return result.data;
  }

  async createAsset(payload) {
    const result = await this.request("POST", "/api/admin/assets", payload);
    return result.data;
  }

  async updateAsset(id, payload) {
    const result = await this.request("PUT", `/api/admin/assets/${id}`, payload);
    return result.data;
  }

  async createLocation(payload) {
    const result = await this.request("POST", "/api/admin/locations", payload);
    return result.data;
  }

  async getMaintenances() {
    const result = await this.request("GET", "/api/admin/maintenances");
    return result.data || [];
  }

  async createMaintenance(payload) {
    const result = await this.request("POST", "/api/admin/maintenances", payload);
    return result.data;
  }
}

const api = new ApiClient();
export default api;
