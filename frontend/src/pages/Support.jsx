import { useLocation } from "react-router-dom";
import ChatWindow from "../components/ChatWindow";
import useChat from "../hooks/useChat";
import { useAuth } from "../context/AuthContext";

function Support() {
  const { user, isLoggedIn } = useAuth();
  const location = useLocation();
  const prompt = location.state?.prompt || "";
  const extraContext = location.state?.context || {};

  const {
    messages,
    loading,
    error,
    agentState,
    conversations,
    sendMessage,
    loadConversation,
    startNewConversation,
  } = useChat({
    customerId: user?.customerId,
    initialPrompt: prompt,
    extraContext,
  });

  return (
    <div className="page support-page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">ABC Technologies</p>
          <h1>AI Customer Support</h1>
          <p>Ask anything about your orders, billing, refunds or products.</p>
        </div>
      </div>
      {!isLoggedIn && (
        <p className="info-banner">
          You can chat as a guest. Sign in to let the assistant use your Customer ID, orders and billing history.
        </p>
      )}
      <ChatWindow
        messages={messages}
        loading={loading}
        error={error}
        agentState={agentState}
        conversations={conversations}
        onSend={sendMessage}
        onSelectConversation={loadConversation}
        onNewConversation={startNewConversation}
      />
    </div>
  );
}

export default Support;
