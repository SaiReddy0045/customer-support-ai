import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import Loading from "./Loading";
import AgentStatus from "./AgentStatus";

const SUGGESTIONS = [
  "Where is my order?",
  "Can I get a refund?",
  "Why was I charged?",
  "Which product should I buy?",
  "Show my recent orders",
];

function ChatWindow({
  messages,
  loading,
  error,
  agentState,
  onSend,
  conversations = [],
  onSelectConversation,
  onNewConversation,
}) {
  return (
    <div className="support-layout">
      <AgentStatus status={agentState} />

      <section className="chat-container">
        <div className="messages">
          {messages.map((message, index) => (
            <ChatMessage key={`${message.createdAt}-${index}`} message={message} />
          ))}
          {loading && <Loading label="AI is thinking..." />}
          {error && <p className="chat-error">{error}</p>}
        </div>

        <div className="suggestion-row">
          {SUGGESTIONS.map((item) => (
            <button key={item} type="button" onClick={() => onSend(item)}>
              {item}
            </button>
          ))}
        </div>

        <ChatInput onSend={onSend} disabled={loading} />
      </section>

      <aside className="history-card">
        <div className="history-head">
          <h3>Conversations</h3>
          <button type="button" onClick={onNewConversation}>
            New
          </button>
        </div>
        {conversations.length === 0 ? (
          <p className="muted">No chat history yet.</p>
        ) : (
          <ul>
            {conversations.map((item) => (
              <li key={item.conversationId}>
                <button type="button" onClick={() => onSelectConversation(item.conversationId)}>
                  <strong>{item.conversationId.slice(0, 14)}</strong>
                  <small>{new Date(item.updatedAt).toLocaleDateString("en-IN")}</small>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
    </div>
  );
}

export default ChatWindow;
