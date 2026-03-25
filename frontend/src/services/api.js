import axios from 'axios';
import { MOCK_USERS, MOCK_ALERTS, MOCK_RISK_HISTORY, MOCK_ACTIVITY_DISTRIBUTION } from './mockData';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const backendClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Mock delay to simulate network request
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export const getDashboardMetrics = async () => {
  await delay(800);
  return {
    totalUsers: MOCK_USERS.length,
    activeSessions: 3,
    riskAlerts: MOCK_ALERTS.length,
    averageRiskScore: Math.round(MOCK_USERS.reduce((acc, u) => acc + u.riskScore, 0) / MOCK_USERS.length),
    riskHistory: MOCK_RISK_HISTORY,
    activityDistribution: MOCK_ACTIVITY_DISTRIBUTION,
  };
};

export const getUsers = async () => {
  await delay(800);
  return MOCK_USERS;
};

export const getUserDetails = async (id) => {
  await delay(800);
  return {
    user: MOCK_USERS.find(u => u.id === parseInt(id)),
    alerts: MOCK_ALERTS.filter(a => a.userId === parseInt(id)),
    timeline: [
      { id: 1, action: "Logged in", timestamp: "2023-10-25T14:32:00Z" },
      { id: 2, action: "Downloaded file", timestamp: "2023-10-25T14:35:00Z" }
    ]
  };
};

export const getAlerts = async () => {
  await delay(800);
  return MOCK_ALERTS;
};

// ==========================================
// REAL STRICT BACKEND INTEGRATION
// ==========================================
export const postAnalyzedEvent = async (payload) => {
  const response = await backendClient.post('/event', payload);
  return response.data;
};
