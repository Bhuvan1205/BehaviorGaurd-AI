const BASE_URL = "http://localhost:8000";

export async function sendEvent(payload) {
  try {
    const response = await fetch(`${BASE_URL}/event`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    const data = await response.json();

    console.log("Backend Response:", data);

    return data;
  } catch (error) {
    console.error("API Call Failed:", error);
    throw error;
  }
}

// 🔹 STRICT mapper (NO fake history anymore)
export function mapToBackendFormat(frontendData, history) {
  const now = new Date();

  const currentEvent = {
    timestamp: now.toISOString(),
    logon_count: Number(frontendData.logons),
    device_count: Number(frontendData.devices),
    hour: now.getHours(),
  };

  return {
    user_id: frontendData.userId,

    event: currentEvent,

    user_history: history.length > 0 ? history : [currentEvent],
  };
}