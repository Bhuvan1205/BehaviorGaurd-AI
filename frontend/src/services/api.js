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

export async function getAnomalies(userId = null, anomalyOnly = true) {
  const params = { anomaly_only: anomalyOnly };
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

/**
 * Start a client-side polling mechanism to fetch scored anomalies/events.
 *
 * @param {(event: object) => void} onEvent   Called for every new scored event
 * @param {(error: Error) => void}  onError   Called on polling error
 * @returns {{ close: () => void }}           Call close() to stop polling
 */
export function openLiveStream(onEvent, onError) {
  let isClosed = false;
  let maxScoreId = null;
  let timerId = null;

  // Emit "connected" to match EventSource expectations
  setTimeout(() => {
    if (!isClosed) {
      onEvent({ type: "connected" });
    }
  }, 100);

  const poll = async () => {
    if (isClosed) return;
    try {
      // Query recent risk scores (both anomalous and normal)
      const events = await getAnomalies(null, false);
      
      // Sort by score_id ascending so we feed them in chronological order
      const sorted = [...events].sort((a, b) => a.score_id - b.score_id);
      
      if (maxScoreId === null) {
        // On the very first poll, seed maxScoreId with the latest score_id
        // and do not stream historical events to avoid duplicate items on UI pages.
        if (sorted.length > 0) {
          maxScoreId = sorted[sorted.length - 1].score_id;
        } else {
          maxScoreId = 0;
        }
      } else {
        // On subsequent polls, stream any new events
        for (const evt of sorted) {
          if (evt.score_id > maxScoreId) {
            maxScoreId = evt.score_id;
            onEvent(evt);
          }
        }
      }
    } catch (err) {
      if (onError) onError(err);
    } finally {
      if (!isClosed) {
        timerId = setTimeout(poll, 4000); // Poll every 4 seconds
      }
    }
  };

  // Start polling
  poll();

  return {
    close: () => {
      isClosed = true;
      if (timerId) clearTimeout(timerId);
    },
  };
}

export async function uploadEmails(file) {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await apiClient.post("/pipeline/upload-emails", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return unwrapResponse(response);
}

export async function getUserEmailAnalyses(userId) {
  const response = await apiClient.get(`/users/${userId}/email-analyses`);
  return unwrapResponse(response);
}

export async function getUserEmailAnalysisEmails(userId, batchDate) {
  const response = await apiClient.get(`/users/${userId}/email-analyses/${batchDate}/emails`);
  return unwrapResponse(response);
}

export async function getAllEmailAnalyses(batchDate = null, verdict = null) {
  const params = {};
  if (batchDate) params.batch_date = batchDate;
  if (verdict) params.verdict = verdict;
  const response = await apiClient.get("/email-analyses", { params });
  return unwrapResponse(response);
}

export async function getEmailAnalysisBatches() {
  const response = await apiClient.get("/email-analyses/batches");
  return unwrapResponse(response);
}

export async function getEmailPolicy() {
  const response = await apiClient.get("/email-analyses/policy");
  return unwrapResponse(response);
}
