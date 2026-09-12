import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getOrderStats, getOrdersByCustomer } from "../services/orderService";
import { formatPrice, formatShortDate } from "../utils/format";
import Loading from "../components/Loading";

function Profile() {
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

  const stats = getOrderStats(orders);
  const recent = orders.slice(0, 5);

  return (
    <div className="page">
      <h1>Welcome, {user.name}</h1>
      <p className="muted">
        Customer ID {user.customerId} · {user.email}
      </p>

      <div className="stat-grid">
        <article className="stat-card"><span>Total Orders</span><strong>{stats.total}</strong></article>
        <article className="stat-card"><span>Pending Orders</span><strong>{stats.pending}</strong></article>
        <article className="stat-card"><span>Completed Orders</span><strong>{stats.completed}</strong></article>
        <article className="stat-card"><span>Refund Requests</span><strong>{stats.refunds}</strong></article>
      </div>

      <section className="panel">
        <div className="section-heading">
          <h2>Recent Orders</h2>
          <Link to="/support">Talk to AI Support</Link>
        </div>
        {loading ? (
          <Loading label="Loading orders..." />
        ) : recent.length === 0 ? (
          <p className="muted">No orders yet.</p>
        ) : (
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
              {recent.map((order) => (
                <tr key={order.orderId}>
                  <td>{order.orderId}</td>
                  <td>{formatShortDate(order.createdAt)}</td>
                  <td>{formatPrice(order.totalAmount)}</td>
                  <td>{order.orderStatus}</td>
                  <td>
                    <Link to={`/orders/${order.orderId}`}>View Order</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default Profile;
