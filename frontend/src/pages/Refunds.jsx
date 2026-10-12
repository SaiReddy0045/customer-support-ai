import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Loading from "../components/Loading";
import api from "../services/api";
import { formatPrice, formatShortDate } from "../utils/format";

function Refunds() {
  const [refunds, setRefunds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadRefunds = () => {
    setLoading(true);
    setError("");
    api.get("/refunds")
      .then(({ data }) => setRefunds(data))
      .catch((requestError) => setError(requestError.message || "Refund history could not be loaded."))
      .finally(() => setLoading(false));
  };

  useEffect(() => loadRefunds(), []);

  return (
    <div className="page">
      <p className="eyebrow">Account</p>
      <h1>Refund requests</h1>
      <p className="muted">Demo refund requests are recorded in your account. No funds are returned by this simulation.</p>
      {loading ? <Loading label="Loading refund history..." /> : error ? (
        <section className="empty-state" role="alert">
          <h2>Refund history unavailable</h2>
          <p>{error}</p>
          <button className="btn ghost" type="button" onClick={loadRefunds}>Retry</button>
        </section>
      ) : refunds.length === 0 ? (
        <section className="empty-state">
          <h2>No refund requests</h2>
          <p>Eligible paid orders can be reviewed with support.</p>
          <Link className="btn primary" to="/support">Contact support</Link>
        </section>
      ) : (
        <div className="table-card">
          <table>
            <thead><tr><th>Refund</th><th>Order</th><th>Requested</th><th>Amount</th><th>Status</th></tr></thead>
            <tbody>{refunds.map((refund) => (
              <tr key={refund.refundId}>
                <td>{refund.refundId}</td>
                <td><Link to={`/orders/${refund.orderId}`}>{refund.orderId}</Link></td>
                <td>{formatShortDate(refund.requestedAt)}</td>
                <td>{formatPrice(refund.amount)}</td>
                <td><span className="status-badge">{refund.status}</span></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Refunds;
