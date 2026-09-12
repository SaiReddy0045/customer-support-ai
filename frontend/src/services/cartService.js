import { STORAGE_KEYS, readJson, writeJson } from "../utils/storage";

const TAX_RATE = 0.18;
const FREE_SHIPPING_THRESHOLD = 2000;
const SHIPPING_FEE = 99;

export function getCart() {
  return readJson(STORAGE_KEYS.CART, []);
}

export function saveCart(items) {
  writeJson(STORAGE_KEYS.CART, items);
  return items;
}

export function addToCart(product, quantity = 1) {
  const cart = getCart();
  const existing = cart.find((item) => item.id === product.id);

  let nextCart;
  if (existing) {
    nextCart = cart.map((item) =>
      item.id === product.id
        ? { ...item, quantity: item.quantity + quantity }
        : item
    );
  } else {
    nextCart = [
      ...cart,
      {
        id: product.id,
        name: product.name,
        price: product.price,
        category: product.category,
        icon: product.icon,
        quantity,
      },
    ];
  }

  return saveCart(nextCart);
}

export function updateCartQuantity(productId, quantity) {
  const nextQuantity = Math.max(1, Number(quantity) || 1);
  const nextCart = getCart().map((item) =>
    item.id === productId ? { ...item, quantity: nextQuantity } : item
  );
  return saveCart(nextCart);
}

export function removeFromCart(productId) {
  return saveCart(getCart().filter((item) => item.id !== productId));
}

export function clearCart() {
  return saveCart([]);
}

export function getCartCount(items = getCart()) {
  return items.reduce((total, item) => total + item.quantity, 0);
}

export function getCartTotals(items = getCart()) {
  const subtotal = items.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );
  const tax = Math.round(subtotal * TAX_RATE);
  const shipping = subtotal === 0 || subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : SHIPPING_FEE;
  const total = subtotal + tax + shipping;

  return { subtotal, tax, shipping, total, taxRate: TAX_RATE };
}
