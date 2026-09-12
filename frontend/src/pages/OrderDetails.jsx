import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Loading from "../components/Loading";
import { getOrderById, updateOrderStatus } from "../services/orderService";
import { formatDate, formatPrice } from "../utils/format";

function OrderDetails() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getOrderById(orderId).then((data) => {
      if (!active) return;
      setOrder(data);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [orderId]);

  if (loading) {
    return (
      <div className="page">
        <Loading label="Loading order..." />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="page empty-state">
        <h2>Order not found</h2>
        <Link to="/orders">Back to orders</Link>
      </div>
    );
  }

  const requestRefund = async () => {
    const updated = await updateOrderStatus(order.orderId, {
      orderStatus: "Refund Requested",
    });
    setOrder(updated);
  };

  return (
    <div className="page">
      <p className="eyebrow">Order</p>
      <h1>{order.orderId}</h1>
      <p className="muted">Placed {formatDate(order.createdAt)}</p>
      <span className="status-badge">{order.orderStatus}</span>

      <div className="details-split">
        <section className="panel">
          <h2>Items</h2>
          {order.items.map((item) => (
            <div className="checkout-item" key={item.id}>
              <div>
                <h3>{item.name}</h3>
                <p>Qty {item.quantity}</p>
              </div>
              <strong>{formatPrice(item.price * item.quantity)}</strong>
            </div>
          ))}
          <p><strong>Total:</strong> {formatPrice(order.totalAmount)}</p>
          <p><strong>Payment:</strong> {order.paymentStatus} · {order.paymentMethod}</p>
          {order.transactionId && <p><strong>Transaction:</strong> {order.transactionId}</p>}
        </section>
        <section className="panel">
          <h2>Shipping</h2>
          <p>{order.shippingAddress?.fullName}</p>
          <p>{order.shippingAddress?.address}</p>
          <p>
            {order.shippingAddress?.city}, {order.shippingAddress?.state}{" "}
            {order.shippingAddress?.pincode}
          </p>
          <p>{order.shippingAddress?.phone}</p>
          <div className="stack-actions">
            <button
              type="button"
              className="btn ghost"
              onClick={() =>
                navigate("/support", {
                  state: {
                    prompt: `Ask AI about this order ${order.orderId}`,
                    context: { orderId: order.orderId },
                  },
                })
              }
            >
              Ask AI about this order
            </button>
            {order.paymentStatus === "Payment Successful" &&
              order.orderStatus !== "Refund Requested" &&
              order.orderStatus !== "Refunded" && (
                <button type="button" className="btn text" onClick={requestRefund}>
                  Request refund / Ask AI about this refund
                </button>
              )}
            {order.transactionId && (
              <button
                type="button"
                className="btn text"
                onClick={() =>
                  navigate("/support", {
                    state: {
                      prompt: `Why was I charged ${formatPrice(order.totalAmount)} for ${order.orderId}?`,
                      context: { orderId: order.orderId, transactionId: order.transactionId },
                    },
                  })
                }
              >
                Ask AI about this charge
              </button>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default OrderDetails;
