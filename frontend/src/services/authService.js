import api, { USE_MOCK_API } from "./api";
import {
  STORAGE_KEYS,
  nextCustomerId,
  readJson,
  writeJson,
  removeKey,
} from "../utils/storage";

function publicUser(user) {
  if (!user) return null;
  const { password, ...safeUser } = user;
  return safeUser;
}

function getUsers() {
  return readJson(STORAGE_KEYS.USERS, []);
}

export async function register({ name, email, password }) {
  if (USE_MOCK_API) {
    const users = getUsers();
    const existing = users.find(
      (user) => user.email.toLowerCase() === email.toLowerCase()
    );

    if (existing) {
      throw new Error("An account with this email already exists.");
    }

    const customer = {
      customerId: nextCustomerId(),
      name: name.trim(),
      email: email.trim().toLowerCase(),
      password,
      createdAt: new Date().toISOString(),
    };

    writeJson(STORAGE_KEYS.USERS, [...users, customer]);
    return publicUser(customer);
  }

  const response = await api.post("/auth/register", { name, email, password });
  return response.data;
}

export async function login({ email, password }) {
  if (USE_MOCK_API) {
    const users = getUsers();
    const customer = users.find(
      (user) => user.email.toLowerCase() === email.trim().toLowerCase()
    );

    if (!customer || customer.password !== password) {
      throw new Error("Invalid email or password.");
    }

    const session = publicUser(customer);
    writeJson(STORAGE_KEYS.SESSION, session);
    return session;
  }

  const response = await api.post("/auth/login", { email, password });
  writeJson(STORAGE_KEYS.SESSION, response.data);
  return response.data;
}

export function logout() {
  removeKey(STORAGE_KEYS.SESSION);
}

export function getSession() {
  return readJson(STORAGE_KEYS.SESSION, null);
}

export function getCustomerById(customerId) {
  return getUsers().find((user) => user.customerId === customerId) || null;
}
