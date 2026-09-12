import { STORAGE_KEYS, readJson, writeJson, removeKey } from "../utils/storage";

export function saveCheckoutDraft(draft) {
  writeJson(STORAGE_KEYS.CHECKOUT, draft);
  return draft;
}

export function getCheckoutDraft() {
  return readJson(STORAGE_KEYS.CHECKOUT, null);
}

export function clearCheckoutDraft() {
  removeKey(STORAGE_KEYS.CHECKOUT);
}
