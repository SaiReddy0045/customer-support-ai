import { Link, useNavigate } from "react-router-dom";
import CartItem from "../components/CartItem";
import OrderSummary from "../components/OrderSummary";
import { useCart } from "../context/CartContext";

function Cart() {
  const { items, totals, updateQuantity, removeItem } = useCart();
  const navigate = useNavigate();

  if (items.length === 0) {
    return (
      <div className="page empty-state">
        <h1>Your cart is empty</h1>
        <p>Add a product to start a demo order for the AI support agent.</p>
        <Link to="/products" className="btn primary">
          Continue Shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="page cart-page">
      <h1>Cart</h1>
      <div className="cart-layout">
        <div className="cart-list">
          {items.map((item) => (
            <CartItem
              key={item.id}
              item={item}
              onQuantity={updateQuantity}
              onRemove={removeItem}
            />
          ))}
        </div>
        <div>
          <OrderSummary items={items} totals={totals} />
          <div className="stack-actions">
            <Link to="/products" className="btn ghost">
              Continue Shopping
            </Link>
            <button type="button" className="btn primary" onClick={() => navigate("/checkout")}>
              Proceed to Checkout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Cart;
