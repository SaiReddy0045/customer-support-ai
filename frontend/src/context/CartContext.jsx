import { createContext, useContext, useMemo, useState } from "react";
import {
  addToCart as addItemToStorage,
  clearCart as clearStoredCart,
  getCart,
  getCartCount,
  getCartTotals,
  removeFromCart as removeStoredItem,
  updateCartQuantity as updateStoredQuantity,
} from "../services/cartService";

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const [items, setItems] = useState(() => getCart());
  const [busyId, setBusyId] = useState(null);

  const refresh = (nextItems) => {
    setItems(nextItems);
    return nextItems;
  };

  const addToCart = async (product, quantity = 1) => {
    setBusyId(product.id);
    await new Promise((resolve) => setTimeout(resolve, 220));
    const next = refresh(addItemToStorage(product, quantity));
    setBusyId(null);
    return next;
  };

  const updateQuantity = (productId, quantity) => {
    refresh(updateStoredQuantity(productId, quantity));
  };

  const removeItem = (productId) => {
    refresh(removeStoredItem(productId));
  };

  const clearCart = () => {
    refresh(clearStoredCart());
  };

  const totals = getCartTotals(items);
  const count = getCartCount(items);

  const value = useMemo(
    () => ({
      items,
      totals,
      count,
      busyId,
      addToCart,
      updateQuantity,
      removeItem,
      clearCart,
    }),
    [items, busyId]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within CartProvider");
  }
  return context;
}
