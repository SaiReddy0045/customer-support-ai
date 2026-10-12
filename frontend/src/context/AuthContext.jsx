import { createContext, useContext, useEffect, useState } from "react";
import api from "../services/api";
import {
  getSession,
  login as loginRequest,
  logout as logoutSession,
  register as registerRequest,
} from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getSession());
  const [sessionChecking, setSessionChecking] = useState(Boolean(getSession()));
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const storedSession = getSession();
    const clearSession = () => {
      logoutSession();
      if (active) setUser(null);
    };
    window.addEventListener("abc-session-expired", clearSession);
    if (storedSession?.sessionToken) {
      api.get("/auth/me")
        .then(({ data }) => {
          if (!active) return;
          setUser((current) => ({ ...current, ...data }));
        })
        .catch(() => clearSession())
        .finally(() => {
          if (active) setSessionChecking(false);
        });
    } else {
      setSessionChecking(false);
    }
    return () => {
      active = false;
      window.removeEventListener("abc-session-expired", clearSession);
    };
  }, []);

  const register = async (payload) => {
    setStatus("registering");
    setError("");
    try {
      const customer = await registerRequest(payload);
      setStatus("idle");
      return customer;
    } catch (err) {
      setStatus("idle");
      setError(err.message);
      throw err;
    }
  };

  const login = async (payload) => {
    setStatus("logging-in");
    setError("");
    try {
      const session = await loginRequest(payload);
      setUser(session);
      setSessionChecking(false);
      setStatus("idle");
      return session;
    } catch (err) {
      setStatus("idle");
      setError(err.message);
      throw err;
    }
  };

  const logout = () => {
    logoutSession();
    setUser(null);
  };

  const value = {
    user,
    isLoggedIn: Boolean(user),
    sessionChecking,
    status,
    error,
    setError,
    register,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
