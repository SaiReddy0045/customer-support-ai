import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import OrderSummary from "../components/OrderSummary";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { saveCheckoutDraft } from "../services/checkoutService";

const METHODS = [
  { id: "card", label: "Card", hint: "Credit / Debit card via ABC Pay demo" },
  { id: "upi", label: "UPI", hint: "Pay using a demo UPI ID" },
  { id: "netbanking", label: "Net Banking", hint: "Simulated bank transfer" },
  { id: "cod", label: "Cash on Delivery", hint: "Pay when the order arrives" },
];

function Checkout() {
  const { user } = useAuth();
  const { items, totals } = useCart();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    fullName: user?.name || "",
    phone: "",
    address: "",
    city: "",
    state: "",
    pincode: "",
    paymentMethod: "card",
  });

  const update = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleContinue = (event) => {
    event.preventDefault();
    if (items.length === 0) {
      setError("Your cart is empty.");
      return;
    }

    const required = ["fullName", "phone", "address", "city", "state", "pincode"];
    const missing = required.find((field) => !form[field].trim());
    if (missing) {
      setError("Please complete all shipping fields.");
      return;
    }

    saveCheckoutDraft({
      customer: {
        name: user.name,
        email: user.email,
        customerId: user.customerId,
      },
      shippingAddress: {
        fullName: form.fullName,
        phone: form.phone,
        address: form.address,
        city: form.city,
        state: form.state,
        pincode: form.pincode,
      },
      paymentMethod: form.paymentMethod,
      items,
      totals,
    });

    navigate("/payment");
  };

  if (items.length === 0) {
    return (
      <div className="page empty-state">
        <h1>Nothing to checkout</h1>
        <Link to="/products" className="btn primary">
          Continue Shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="page checkout-page">
      <h1>Checkout</h1>
      <form className="checkout-grid" onSubmit={handleContinue}>
        <div>
          <section className="panel">
            <h2>Customer Information</h2>
            <p><strong>Name:</strong> {user.name}</p>
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Customer ID:</strong> {user.customerId}</p>
          </section>

          <section className="panel">
            <h2>Shipping Address</h2>
            <label>Full Name</label>
            <input value={form.fullName} onChange={update("fullName")} />
            <label>Phone</label>
            <input value={form.phone} onChange={update("phone")} placeholder="10-digit mobile" />
            <label>Address</label>
            <input value={form.address} onChange={update("address")} placeholder="Street, apartment" />
            <div className="form-row">
              <div>
                <label>City</label>
                <input value={form.city} onChange={update("city")} />
              </div>
              <div>
                <label>State</label>
                <input value={form.state} onChange={update("state")} />
              </div>
              <div>
                <label>Pincode</label>
                <input value={form.pincode} onChange={update("pincode")} />
              </div>
            </div>
          </section>

          <section className="panel">
            <h2>Payment Method</h2>
            {METHODS.map((method) => (
              <label key={method.id} className="payment-option">
                <input
                  type="radio"
                  name="method"
                  value={method.id}
                  checked={form.paymentMethod === method.id}
                  onChange={update("paymentMethod")}
                />
                <div>
                  <strong>{method.label}</strong>
                  <p>{method.hint}</p>
                </div>
              </label>
            ))}
          </section>
        </div>

        <div>
          <OrderSummary items={items} totals={totals} />
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="btn primary full">
            Continue to Payment
          </button>
          <Link to="/cart" className="btn ghost full">
            Back to cart
          </Link>
        </div>
      </form>
    </div>
  );
}

export default Checkout;
