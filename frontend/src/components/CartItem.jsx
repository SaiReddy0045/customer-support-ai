import ProductImage from "./ProductImage";
import { formatPrice } from "../utils/format";

function CartItem({ item, onQuantity, onRemove }) {
  return (
    <div className="cart-item">
      <ProductImage icon={item.icon} name={item.category} />
      <div className="cart-item-info">
        <h3>{item.name}</h3>
        <p>{item.category}</p>
        <strong>{formatPrice(item.price)}</strong>
      </div>
      <div className="qty-control">
        <button type="button" onClick={() => onQuantity(item.id, item.quantity - 1)}>
          −
        </button>
        <span>{item.quantity}</span>
        <button type="button" onClick={() => onQuantity(item.id, item.quantity + 1)}>
          +
        </button>
      </div>
      <div className="cart-item-subtotal">
        <strong>{formatPrice(item.price * item.quantity)}</strong>
        <button type="button" className="text-btn" onClick={() => onRemove(item.id)}>
          Remove
        </button>
      </div>
    </div>
  );
}

export default CartItem;
