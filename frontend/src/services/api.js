import axios from "axios";


export const USE_MOCK_API = false;

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

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
      const customerId = user?.customerId || user?.customer_id;
      const sessionToken = user?.sessionToken;
      if (customerId) {
        config.headers["X-Customer-Id"] = customerId;
      }
      if (sessionToken) {
        config.headers.Authorization = `Bearer ${sessionToken}`;
      }
    } catch {
      // ignore malformed session in this prototype
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    if (error.response?.status === 401) {
      localStorage.removeItem("abc_session");
      window.dispatchEvent(new CustomEvent("abc-session-expired"));
    }
    if (detail) {
      error.message = Array.isArray(detail)
        ? detail.map((item) => item.msg).join("; ")
        : detail;
    }
    return Promise.reject(error);
  }
);

export default api;
