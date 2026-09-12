const PREFIX = "abc_";

export const STORAGE_KEYS = {
  USERS: `${PREFIX}users`,
  SESSION: `${PREFIX}session`,
  CART: `${PREFIX}cart`,
  ORDERS: `${PREFIX}orders`,
  CONVERSATIONS: `${PREFIX}conversations`,
  COUNTERS: `${PREFIX}counters`,
  CHECKOUT: `${PREFIX}checkout_draft`,
};

export function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function writeJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function removeKey(key) {
  localStorage.removeItem(key);
}

export function getCounters() {
  return readJson(STORAGE_KEYS.COUNTERS, {
    customer: 10001,
    order: 10001,
  });
}

export function saveCounters(counters) {
  writeJson(STORAGE_KEYS.COUNTERS, counters);
}

export function nextCustomerId() {
  const counters = getCounters();
  const id = `CUS-${counters.customer}`;
  counters.customer += 1;
  saveCounters(counters);
  return id;
}

export function nextOrderId() {
  const counters = getCounters();
  const year = new Date().getFullYear();
  const id = `ORD-${year}-${counters.order}`;
  counters.order += 1;
  saveCounters(counters);
  return id;
}

export function randomHex(length = 8) {
  const chars = "0123456789ABCDEF";
  let result = "";
  for (let i = 0; i < length; i += 1) {
    result += chars[Math.floor(Math.random() * chars.length)];
  }
  return result;
}

export function nextTransactionId() {
  return `TXN-${randomHex(8)}`;
}

export function nextConversationId() {
  return `CONV-${randomHex(10)}`;
}
