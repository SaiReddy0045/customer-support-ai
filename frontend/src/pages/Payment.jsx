import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { clearCheckoutDraft, getCheckoutDraft } from "../services/checkoutService";
import { processDemoPayment } from "../services/paymentService";
import { createOrder } from "../services/orderService";
import { formatPrice } from "../utils/format";

function Payment() {
  const draft = getCheckoutDraft();
  const { user } = useAuth();
  const { clearCart } = useCart();
  const navigate = useNavigate();
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [card, setCard] = useState({
    name: user?.name || "",
    number: "4111 1111 1111 1111",
    expiry: "12/28",
    cvv: "123",
  });
  const [upiId, setUpiId] = useState("customer@abcpay");
  const [bank, setBank] = useState("ABC Demo Bank");

  if (!draft) {
    return (
      <div className="page empty-state">
        <h1>No payment in progress</h1>
        <p>Complete checkout first.</p>
        <Link to="/checkout" className="btn primary">Go to checkout</Link>
      </div>
    );
  }

  const method = draft.paymentMethod;
  const amount = draft.totals.total;

  const placeOrder = async (paymentStatus, orderStatus, transactionId) => {
    const order = await createOrder({
      customerId: user.customerId,
      items: draft.items,
      totals: draft.totals,
      paymentMethod: method,
      paymentStatus,
      orderStatus,
      transactionId,
      shippingAddress: draft.shippingAddress,
    });
    clearCart();
    clearCheckoutDraft();
    return order;
  };

  const handlePay = async (event) => {
    event.preventDefault();
    setProcessing(true);
    setError("");

    try {
      if (method === "cod") {
        const order = await placeOrder("Pending Payment", "Pending Payment", null);
        setResult({ type: "cod", order });
        return;
      }

      const payment = await processDemoPayment({
        amount,
        paymentMethod: method,
        customerId: user.customerId,
        cardNumber: card.number,
        cvv: card.cvv,
        upiId,
        bank,
      });

      const order = await placeOrder(
        "Payment Successful",
        "Order Confirmed",
        payment.transactionId
      );
      setResult({ type: "success", order, payment });
    } catch (err) {
      setError(err.message || "Payment failed");
      setResult({ type: "failed" });
    } finally {
      setProcessing(false);
    }
  };

  if (result?.type === "success" || result?.type === "cod") {
    const order = result.order;
    return (
      <div className="payment-page">
        <div className="payment-card">
          <p className="eyebrow">ABC Pay · Demo</p>
          <h1>{result.type === "cod" ? "Order placed" : "Payment Successful"}</h1>
          <p className="payment-subtitle">
            {result.type === "cod"
              ? "Cash on Delivery selected. Payment will be collected later."
              : "Your demo payment was recorded for the AI billing agent."}
          </p>
          <div className="result-grid">
            {result.payment && (
              <p><span>Transaction ID</span><strong>{result.payment.transactionId}</strong></p>
            )}
            <p><span>Order ID</span><strong>{order.orderId}</strong></p>
            <p><span>Amount</span><strong>{formatPrice(order.totalAmount)}</strong></p>
            <p><span>Customer ID</span><strong>{order.customerId}</strong></p>
            <p><span>Status</span><strong>{order.orderStatus}</strong></p>
          </div>
          <div className="stack-actions">
            <Link to={`/orders/${order.orderId}`} className="btn primary">View Order</Link>
            <Link to="/products" className="btn ghost">Continue Shopping</Link>
            <Link
              to="/support"
              state={{ prompt: `Tell me about order ${order.orderId}.`, context: { orderId: order.orderId } }}
              className="btn text"
            >
              Ask AI about this order
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="payment-page">
      <div className="payment-card">
        <p className="demo-banner">Demo Payment · ABC Pay never contacts a real bank</p>
        <h1>ABC Pay</h1>
        <p className="payment-subtitle">Complete this simulated payment to create a demo order.</p>

        <div className="payment-amount">
          <div>
            <span>Amount</span>
            <strong>{formatPrice(amount)}</strong>
          </div>
          <div>
            <span>Customer ID</span>
            <strong>{user.customerId}</strong>
          </div>
        </div>

        {processing && (
          <div className="processing-box">Processing Payment...</div>
        )}

        <form onSubmit={handlePay}>
          {method === "card" && (
            <div className="card-details">
              <label>Cardholder Name</label>
              <input value={card.name} onChange={(e) => setCard({ ...card, name: e.target.value })} />
              <label>Card Number</label>
              <input
                value={card.number}
                maxLength="19"
                onChange={(e) => setCard({ ...card, number: e.target.value })}
              />
              <div className="card-row">
                <div>
                  <label>Expiry Date</label>
                  <input value={card.expiry} maxLength="5" onChange={(e) => setCard({ ...card, expiry: e.target.value })} />
                </div>
                <div>
                  <label>CVV</label>
                  <input value={card.cvv} maxLength="3" onChange={(e) => setCard({ ...card, cvv: e.target.value })} />
                </div>
              </div>
              <p className="muted">Use CVV 000 or a card ending in 0002 to simulate failure.</p>
            </div>
          )}

          {method === "upi" && (
            <div className="card-details">
              <label>UPI ID</label>
              <input value={upiId} onChange={(e) => setUpiId(e.target.value)} />
              <p className="muted">Use an ID containing “fail” to simulate a failed payment.</p>
            </div>
          )}

          {method === "netbanking" && (
            <div className="card-details">
              <label>Bank</label>
              <select value={bank} onChange={(e) => setBank(e.target.value)}>
                <option>ABC Demo Bank</option>
                <option>National Demo Bank</option>
                <option>City Demo Bank</option>
              </select>
            </div>
          )}

          {method === "cod" && (
            <p>No online payment needed. Confirm to place the order with pending payment.</p>
          )}

          {error && (
            <div className="fail-box">
              <h2>Payment Failed</h2>
              <p>{error}</p>
            </div>
          )}

          <button type="submit" className="pay-button" disabled={processing}>
            {processing
              ? "Processing Payment..."
              : method === "cod"
                ? `Place order ${formatPrice(amount)}`
                : `Pay ${formatPrice(amount)}`}
          </button>
          <button type="button" className="btn ghost full" onClick={() => navigate("/checkout")}>
            Cancel
          </button>
        </form>
      </div>
    </div>
  );
}

export default Payment;
