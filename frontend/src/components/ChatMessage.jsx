function ChatMessage({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message ${isUser ? "user" : "bot"}`}>
      <div className="bubble">
        {!isUser && <small>AI Support</small>}
        <p>{message.text}</p>
        {message.intent && (
          <em>
            Routed to {message.agent?.replaceAll("_", " ") || message.intent}
          </em>
        )}
      </div>
    </div>
  );
}

export default ChatMessage;
