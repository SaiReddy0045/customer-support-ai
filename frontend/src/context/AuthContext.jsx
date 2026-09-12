import { createContext, useContext, useState } from "react";
import {
  getSession,
  login as loginRequest,
  logout as logoutSession,
  register as registerRequest,
} from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getSession());
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

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
