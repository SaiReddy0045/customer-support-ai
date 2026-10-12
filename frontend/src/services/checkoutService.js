import { STORAGE_KEYS, readJson, writeJson, removeKey } from "../utils/storage";

function newIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() || `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function saveCheckoutDraft(draft) {
  const current = getCheckoutDraft();
  const nextDraft = {
    ...draft,
    idempotencyKey: draft.idempotencyKey || current?.idempotencyKey || newIdempotencyKey(),
  };
  writeJson(STORAGE_KEYS.CHECKOUT, nextDraft);
  return nextDraft;
}

export function getCheckoutDraft() {
  return readJson(STORAGE_KEYS.CHECKOUT, null);
}

export function clearCheckoutDraft() {
  removeKey(STORAGE_KEYS.CHECKOUT);
}
