function AgentStatus({ status }) {
  const processing = status?.processing;
  const intent = status?.intent;
  const agentLabel = status?.agentLabel || status?.agent || "Support Agent";

  return (
    <aside className="agent-status-card">
      <div className="agent-status-head">
        <div>
          <p className="eyebrow">AI Assistant</p>
          <h3>Customer Support</h3>
        </div>
        <span className={`status-pill ${processing ? "busy" : "online"}`}>
          <i />
          {processing ? "Processing..." : "Online"}
        </span>
      </div>

      <div className="agent-status-grid">
        <div>
          <span>Intent detected</span>
          <strong>{intent ? formatLabel(intent) : "Waiting"}</strong>
        </div>
        <div>
          <span>Selected agent</span>
          <strong>{processing && !status?.agent ? "Intent Classifier" : formatLabel(agentLabel)}</strong>
        </div>
        <div>
          <span>Conversation</span>
          <strong className="mono">{status?.conversationId || "—"}</strong>
        </div>
      </div>

      <p className="agent-note">
        Demo status only. FastAPI + LangGraph will populate these fields later.
      </p>
    </aside>
  );
}

function formatLabel(value) {
  if (!value) return "—";
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default AgentStatus;
