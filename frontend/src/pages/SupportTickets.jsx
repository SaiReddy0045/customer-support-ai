import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Loading from "../components/Loading";
import { getSupportTickets } from "../services/supportTicketService";
import { formatShortDate } from "../utils/format";

function SupportTickets() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadTickets = () => {
    setLoading(true);
    setError("");
    getSupportTickets()
      .then(setTickets)
      .catch((requestError) => setError(requestError.message || "Ticket history could not be loaded."))
      .finally(() => setLoading(false));
  };

  useEffect(() => loadTickets(), []);

  return (
    <div className="page">
      <p className="eyebrow">Account</p>
      <h1>Support tickets</h1>
      <p className="muted">These are internal demo records; no live representative has been contacted.</p>
      {loading ? <Loading label="Loading support tickets..." /> : error ? (
        <section className="empty-state" role="alert">
          <h2>Ticket history unavailable</h2>
          <p>{error}</p>
          <button className="btn ghost" type="button" onClick={loadTickets}>Retry</button>
        </section>
      ) : tickets.length === 0 ? (
        <section className="empty-state">
          <h2>No support tickets</h2>
          <p>Ask the support assistant to create an internal ticket.</p>
          <Link className="btn primary" to="/support">Open support</Link>
        </section>
      ) : (
        <div className="table-card">
          <table>
            <thead><tr><th>Ticket</th><th>Category</th><th>Order</th><th>Created</th><th>Status</th></tr></thead>
            <tbody>{tickets.map((ticket) => (
              <tr key={ticket.ticketId}>
                <td>{ticket.ticketId}</td>
                <td>{ticket.category}</td>
                <td>{ticket.orderId || "-"}</td>
                <td>{formatShortDate(ticket.createdAt)}</td>
                <td><span className="status-badge">{ticket.status}</span></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default SupportTickets;
