import { formatPrice } from "../utils/format";

function OrderSummary({ items, totals, compact = false }) {
  return (
    <div className={`order-summary-card ${compact ? "compact" : ""}`}>
      <h2>Order Summary</h2>
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <span>
              {item.name} × {item.quantity}
            </span>
            <strong>{formatPrice(item.price * item.quantity)}</strong>
          </li>
        ))}
      </ul>
      <div className="summary-row">
        <span>Subtotal</span>
        <span>{formatPrice(totals.subtotal)}</span>
      </div>
      <div className="summary-row">
        <span>Tax (18%)</span>
        <span>{formatPrice(totals.tax)}</span>
      </div>
      <div className="summary-row">
        <span>Shipping</span>
        <span>{totals.shipping === 0 ? "Free" : formatPrice(totals.shipping)}</span>
      </div>
      <div className="summary-row total">
        <span>Total</span>
        <strong>{formatPrice(totals.total)}</strong>
      </div>
    </div>
  );
}

export default OrderSummary;
