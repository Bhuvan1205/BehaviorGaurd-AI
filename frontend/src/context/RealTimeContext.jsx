import { createContext, useContext, useState } from "react";
import { sendEvent, mapToBackendFormat } from "../services/api";

const RealTimeContext = createContext(null);

export function RealTimeProvider({ children }) {
  const [userHistory, setUserHistory] = useState([]);
  const [lastResult, setLastResult] = useState(null);
  const [alerts, setAlerts] = useState([]);

  async function processEvent(frontendData) {
    const payload = mapToBackendFormat(frontendData, userHistory);

    const response = await sendEvent(payload);

    // update history
    setUserHistory((prev) => [...prev, payload.event]);

    // update last result
    setLastResult(response);

    // update alerts
    if (response.alert.alert) {
      setAlerts((prev) => [
        {
          user_id: response.alert.user_id,
          risk: response.alert.risk,
          level: response.alert.level,
          timestamp: new Date().toISOString(),
        },
        ...prev,
      ]);
    }

    return response;
  }

  return (
    <RealTimeContext.Provider
      value={{
        userHistory,
        lastResult,
        alerts,
        processEvent,
      }}
    >
      {children}
    </RealTimeContext.Provider>
  );
}

export function useRealTime() {
  const context = useContext(RealTimeContext);
  if (!context) {
    throw new Error("useRealTime must be used inside RealTimeProvider");
  }
  return context;
}