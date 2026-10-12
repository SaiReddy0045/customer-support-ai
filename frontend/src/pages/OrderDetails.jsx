import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Loading from "../components/Loading";
import { getOrderById, getTrackingByOrderId } from "../services/orderService";
import { formatDate, formatPrice } from "../utils/format";

function OrderDetails() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [tracking, setTracking] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshOrder = useCallback(async () => {
    const [orderData, trackingData] = await Promise.all([
      getOrderById(orderId),
      getTrackingByOrderId(orderId),
    ]);
    setOrder(orderData);
    setTracking(trackingData || orderData?.tracking || null);
  }, [orderId]);

  useEffect(() => {
    let active = true;
    refreshOrder()
      .then(() => {
        if (!active) return;
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [refreshOrder]);

  const activeTracking = tracking?.stages || [];
  const displayedStatus = tracking?.status || order?.orderStatus;

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

  return (
    <div className="page">
      <p className="eyebrow">Order</p>
      <h1>{order.orderId}</h1>
      <p className="muted">Placed {formatDate(order.createdAt)}</p>
      <span className="status-badge">{displayedStatus}</span>

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
          {typeof order.shippingAddress === "string" ? (
            <p>{order.shippingAddress}</p>
          ) : (
            <>
              <p>{order.shippingAddress?.fullName}</p>
              <p>{order.shippingAddress?.address}</p>
              <p>{order.shippingAddress?.city}, {order.shippingAddress?.state} {order.shippingAddress?.pincode}</p>
              <p>{order.shippingAddress?.phone}</p>
            </>
          )}
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
            {order.cancellationEligible && (
              <button
                type="button"
                className="btn ghost"
                onClick={() => navigate("/support", {
                  state: {
                    prompt: `Cancel order ${order.orderId}`,
                    context: { orderId: order.orderId },
                  },
                })}
              >
                Request cancellation
              </button>
            )}
            {order.refundEligible && (
                <button
                  type="button"
                  className="btn text"
                  onClick={() => navigate("/support", {
                    state: {
                      prompt: `I need a refund for order ${order.orderId}`,
                      context: { orderId: order.orderId },
                    },
                  })}
                >
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

      {activeTracking.length > 0 && (
        <section className="panel" style={{ marginTop: "1.5rem" }}>
          <h2>Tracking Timeline</h2>
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {activeTracking.map((step, index) => (
              <div
                key={`${step.name}-${index}`}
                style={{
                  padding: "0.75rem 1rem",
                  borderLeft: "4px solid #3b82f6",
                  background: "rgba(59,130,246,0.04)",
                  borderRadius: "8px",
                }}
              >
                <strong>{step.name}</strong>
                <p style={{ margin: "0.2rem 0 0" }}>
                  {step.current ? "Current delivery stage" : step.completed ? "Completed" : "Upcoming"}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default OrderDetails;
