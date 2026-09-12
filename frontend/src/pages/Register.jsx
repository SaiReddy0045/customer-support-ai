import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Register() {
  const { register, status, error, setError } = useAuth();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [created, setCreated] = useState(null);

  const update = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.password) {
      setError("Please fill all fields.");
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (form.password.length < 6) {
      setError("Use at least 6 characters for this demo password.");
      return;
    }

    try {
      const customer = await register(form);
      setCreated(customer);
    } catch {
      // error already stored in auth context
    }
  };

  if (created) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <p className="eyebrow">Account created successfully</p>
          <h1>Welcome, {created.name}</h1>
          <p>Your Customer ID is</p>
          <div className="customer-id-box">{created.customerId}</div>
          <p className="muted">
            This frontend demo stores accounts in localStorage only. Real
            authentication will be handled by FastAPI later.
          </p>
          <Link to="/login" className="btn primary full">
            Continue to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">ABC Technologies</p>
        <h1>Create Account</h1>
        <p>Register to get a Customer ID for orders and AI support.</p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="name">Full Name</label>
          <input id="name" value={form.name} onChange={update("name")} placeholder="Your name" />
          <label htmlFor="email">Email</label>
          <input id="email" type="email" value={form.email} onChange={update("email")} placeholder="you@email.com" />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" value={form.password} onChange={update("password")} placeholder="Create a password" />
          <label htmlFor="confirmPassword">Confirm Password</label>
          <input id="confirmPassword" type="password" value={form.confirmPassword} onChange={update("confirmPassword")} placeholder="Repeat password" />
          {error && <p className="form-error">{error}</p>}
          <button type="submit" disabled={status === "registering"}>
            {status === "registering" ? "Creating account..." : "Create Account"}
          </button>
        </form>
        <p>
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
}

export default Register;
