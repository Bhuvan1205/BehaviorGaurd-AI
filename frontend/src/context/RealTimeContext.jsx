import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { MOCK_USERS, MOCK_ALERTS, MOCK_RISK_HISTORY, MOCK_ACTIVITY_DISTRIBUTION } from '@/services/mockData';

const RealTimeContext = createContext(null);

export const useRealTime = () => useContext(RealTimeContext);

const INITIAL_ACTIVITIES = [
  { id: 1001, type: "system", message: "System initialized normally", timestamp: Date.now() - 3600000 },
  { id: 1002, type: "login", message: "Admin user authenticated", timestamp: Date.now() - 1800000 },
];

export const RealTimeProvider = ({ children }) => {
  const [users, setUsers] = useState(MOCK_USERS);
  const [alerts, setAlerts] = useState(MOCK_ALERTS);
  const [riskHistory, setRiskHistory] = useState(MOCK_RISK_HISTORY.map((h, i) => ({ ...h, time: `T-${7-i}h` })));
  const [activityFeed, setActivityFeed] = useState(INITIAL_ACTIVITIES);
  
  // Calculate aggregated dashboard metrics
  const dashboardMetrics = {
    totalUsers: users.length,
    activeSessions: Math.max(1, Math.floor(users.length * 0.4)),
    riskAlerts: alerts.length,
    averageRiskScore: Math.round(users.reduce((acc, u) => acc + u.riskScore, 0) / users.length) || 0,
    riskHistory,
    activityDistribution: MOCK_ACTIVITY_DISTRIBUTION, // Keep static or simulate small changes if desired
  };

  const notifyActivity = useCallback((type, message) => {
    setActivityFeed(prev => [{ id: Date.now(), type, message, timestamp: Date.now() }, ...prev].slice(0, 15));
  }, []);

  useEffect(() => {
    // Score update interval (every 3 seconds)
    const scoreInterval = setInterval(() => {
      setUsers(currentUsers => currentUsers.map(user => {
        // Only update ~30% of users each tick to avoid overwhelming changes
        if (Math.random() > 0.3) return user;

        const change = Math.floor(Math.random() * 21) - 5; // -5 to +15
        let newScore = Math.max(0, Math.min(100, user.riskScore + change));
        
        let status = 'Safe';
        if (newScore > 70) status = 'High Risk';
        else if (newScore > 30) status = 'Moderate';

        // Notify anomaly if score jumped significantly into High Risk
        if (newScore > 70 && user.riskScore <= 70) {
          notifyActivity('anomaly', `Anomalous behavior detected for ${user.username}`);
          setAlerts(prev => [{ 
            id: Date.now(), 
            type: "Behavior Anomaly", 
            severity: "High", 
            timestamp: new Date().toISOString(), 
            userId: user.id 
          }, ...prev].slice(0, 20));
        }

        return { ...user, riskScore: newScore, status, lastActivity: new Date().toISOString() };
      }));
    }, 3000);

    // Chart update interval (every 5 seconds)
    const chartInterval = setInterval(() => {
      setRiskHistory(prev => {
        const newScore = Math.floor(Math.random() * 20) + 40; // 40-60 range
        const nextTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const newHistory = [...prev, { time: nextTime, score: newScore }];
        
        if (newHistory.length > 20) {
          newHistory.shift();
        }
        return newHistory;
      });
      
      if (Math.random() > 0.5) {
        notifyActivity('login', `Global access token refreshed`);
      }
    }, 5000);

    return () => {
      clearInterval(scoreInterval);
      clearInterval(chartInterval);
    };
  }, [notifyActivity]);

  return (
    <RealTimeContext.Provider value={{ users, alerts, dashboardMetrics, activityFeed }}>
      {children}
    </RealTimeContext.Provider>
  );
};
