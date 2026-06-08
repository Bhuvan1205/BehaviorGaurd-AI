import axios from "axios";
import { API_BASE_URL } from "../config/env";

const STORAGE_KEY = "behaviorguard.session";

export function getStoredSession() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredSession(session) {
  if (!session) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

apiClient.interceptors.request.use((config) => {
  const session = getStoredSession();
  if (session?.token) {
    config.headers.Authorization = `Bearer ${session.token}`;
  }
  return config;
});

function unwrapResponse(response) {
  if (response?.data?.detail) {
    throw new Error(response.data.detail);
  }

  if (response?.data?.error) {
    throw new Error(response.data.error);
  }

  return response.data;
}

export async function loginAdmin(payload) {
  const response = await apiClient.post("/auth/login", payload);
  return unwrapResponse(response);
}

export async function registerAdmin(payload) {
  const response = await apiClient.post("/auth/register", payload);
  return unwrapResponse(response);
}

export async function logoutAdmin() {
  const response = await apiClient.post("/auth/logout");
  return unwrapResponse(response);
}

export async function getCurrentAdmin() {
  const response = await apiClient.get("/auth/me");
  return unwrapResponse(response);
}



export async function getHistory(userId) {
  const response = await apiClient.get("/history", {
    params: { user_id: userId },
  });
  return unwrapResponse(response);
}

export async function getAlerts(userId = null, batchDate = null, status = null, latestOnly = true) {
  const params = {};
  if (userId) params.user_id = userId;
  if (batchDate) params.batch_date = batchDate;
  if (status) params.status = status;
  if (!userId) params.latest_only = latestOnly;
  const response = await apiClient.get("/alerts", { params });
  return unwrapResponse(response);
}

export async function updateAlertStatus(alertId, status) {
  const response = await apiClient.patch(`/alerts/${alertId}`, { status });
  return unwrapResponse(response);
}

export async function getUsers() {
  const response = await apiClient.get("/users");
  return unwrapResponse(response);
}

export async function getAnomalies(userId = null) {
  const params = {};
  if (userId) params.user_id = userId;
  const response = await apiClient.get("/anomalies", { params });
  return unwrapResponse(response);
}

export async function getUserDetail(userId) {
  const response = await apiClient.get(`/users/${userId}`);
  return unwrapResponse(response);
}

export async function getDashboardSummary() {
  const response = await apiClient.get("/dashboard/summary");
  return unwrapResponse(response);
}

export async function uploadLog(file, batchDate) {
  const formData = new FormData();
  formData.append("file", file);
  
  let url = "/pipeline/upload-log";
  if (batchDate) {
    url += `?batch_date=${encodeURIComponent(batchDate)}`;
  }
  
  const response = await apiClient.post(url, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return unwrapResponse(response);
}

export async function getJobStatus(jobId) {
  const response = await apiClient.get(`/pipeline/status/${jobId}`);
  return unwrapResponse(response);
}

export async function getStreamStatus() {
  const response = await apiClient.get("/stream/status");
  return unwrapResponse(response);
}

export async function setStreamScenario(scenario) {
  const response = await apiClient.post("/stream/scenario", { scenario });
  return unwrapResponse(response);
}

export async function ingestSingleEvent(payload) {
  const response = await apiClient.post("/stream/ingest", payload);
  return unwrapResponse(response);
}

/**
 * Open a persistent SSE connection to /stream/live.
 *
 * @param {(event: object) => void} onEvent   Called for every scored event
 * @param {(error: Event) => void}  onError   Called on connection error
 * @returns {{ close: () => void }}           Call close() to disconnect
 */
export function openLiveStream(onEvent, onError) {
  const session = getStoredSession();
  const token = session?.token ?? "";
  const url = `${API_BASE_URL}/stream/live${token ? `?token=${encodeURIComponent(token)}` : ""}`;

  const source = new EventSource(url);

  source.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
    } catch {
      // Skip malformed frames (keep-alive comments, etc.)
    }
  };

  source.onerror = (e) => {
    if (onError) onError(e);
  };

  return {
    close: () => source.close(),
  };
}
