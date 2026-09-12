import axios from "axios";

// Toggle this to false once FastAPI is running.
export const USE_MOCK_API = true;

export const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const session = localStorage.getItem("abc_session");
  if (session) {
    try {
      const user = JSON.parse(session);
      if (user?.customerId) {
        config.headers["X-Customer-Id"] = user.customerId;
      }
    } catch {
      // ignore malformed session in this prototype
    }
  }
  return config;
});

export default api;
