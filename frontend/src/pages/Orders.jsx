import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Loading from "../components/Loading";
import { useAuth } from "../context/AuthContext";
import { getOrdersByCustomer } from "../services/orderService";
import { formatPrice, formatShortDate } from "../utils/format";

function Orders() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getOrdersByCustomer(user.customerId).then((data) => {
      if (!active) return;
      setOrders(data);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [user.customerId]);

  return (
    <div className="page">
      <h1>Orders</h1>
      <p className="muted">Your demo order history for AI support scenarios.</p>
      {loading ? (
        <Loading label="Loading orders..." />
      ) : orders.length === 0 ? (
        <div className="empty-state">
          <h2>No orders yet</h2>
          <p>Place an order to ask the assistant “Where is my order?”</p>
          <Link to="/products" className="btn primary">Shop products</Link>
        </div>
      ) : (
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Date</th>
                <th>Amount</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.orderId}>
                  <td>{order.orderId}</td>
                  <td>{formatShortDate(order.createdAt)}</td>
                  <td>{formatPrice(order.totalAmount)}</td>
                  <td><span className="status-badge">{order.orderStatus}</span></td>
                  <td>
                    <Link to={`/orders/${order.orderId}`}>View Order</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Orders;
