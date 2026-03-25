export const MOCK_USERS = [
  { id: 1, username: "admin_user", lastActivity: "2023-10-25T14:32:00Z", riskScore: 12, status: "Safe" },
  { id: 2, username: "john_doe", lastActivity: "2023-10-25T14:30:00Z", riskScore: 45, status: "Moderate" },
  { id: 3, username: "suspicious_ip", lastActivity: "2023-10-25T14:28:00Z", riskScore: 89, status: "High Risk" },
  { id: 4, username: "alice_smith", lastActivity: "2023-10-25T14:20:00Z", riskScore: 5, status: "Safe" },
  { id: 5, username: "bob_jones", lastActivity: "2023-10-25T14:15:00Z", riskScore: 65, status: "Moderate" },
];

export const MOCK_ALERTS = [
  { id: 101, type: "Multiple Failed Logins", severity: "High", timestamp: "2023-10-25T14:28:00Z", userId: 3 },
  { id: 102, type: "Unusual Download Volume", severity: "Medium", timestamp: "2023-10-25T14:30:00Z", userId: 2 },
  { id: 103, type: "Access from New IP", severity: "Low", timestamp: "2023-10-25T14:20:00Z", userId: 4 },
];

export const MOCK_RISK_HISTORY = [
  { time: "00:00", score: 20 },
  { time: "04:00", score: 25 },
  { time: "08:00", score: 40 },
  { time: "12:00", score: 35 },
  { time: "16:00", score: 65 },
  { time: "20:00", score: 50 },
  { time: "24:00", score: 45 },
];

export const MOCK_ACTIVITY_DISTRIBUTION = [
  { name: "Logins", count: 400 },
  { name: "Downloads", count: 300 },
  { name: "Settings Changed", count: 50 },
  { name: "API Requests", count: 800 },
];
