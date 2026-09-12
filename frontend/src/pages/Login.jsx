import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Login() {
  const { login, status, error, setError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = async (event) => {
    event.preventDefault();
    if (!email || !password) {
      setError("Enter email and password.");
      return;
    }

    try {
      await login({ email, password });
      navigate(location.state?.from || "/", { replace: true });
    } catch {
      // shown via context error
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">ABC Technologies</p>
        <h1>Welcome Back</h1>
        <p>Login with your demo account to shop and ask the AI assistant.</p>
        <form onSubmit={handleLogin}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              setError("");
            }}
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
              setError("");
            }}
          />
          {error && <p className="form-error">{error}</p>}
          <button type="submit" disabled={status === "logging-in"}>
            {status === "logging-in" ? "Logging in..." : "Login"}
          </button>
        </form>
        <p>
          Don't have an account? <Link to="/register">Create Account</Link>
        </p>
      </div>
    </div>
  );
}

export default Login;
