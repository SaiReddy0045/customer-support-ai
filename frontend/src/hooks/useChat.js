import { useEffect, useRef, useState } from "react";
import { sendMessage as sendAiMessage } from "../services/aiService";
import {
  appendMessages,
  createConversation,
  getConversation,
  getConversations,
} from "../services/conversationService";

const WELCOME =
  "Hello. I'm the ABC Technologies AI Customer Support Assistant. Ask me about your orders, billing, refunds or products.";

export default function useChat({ customerId, initialPrompt, extraContext }) {
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [agentState, setAgentState] = useState({
    online: true,
    processing: false,
    intent: null,
    agent: null,
    agentLabel: null,
    conversationId: null,
  });

  useEffect(() => {
    const existing = getConversations(customerId)[0];
    if (existing) {
      setConversation(existing);
      setMessages(existing.messages);
      setAgentState((current) => ({
        ...current,
        conversationId: existing.conversationId,
      }));
      return;
    }

    const created = createConversation(customerId, [
      {
        role: "assistant",
        text: WELCOME,
        createdAt: new Date().toISOString(),
      },
    ]);
    setConversation(created);
    setMessages(created.messages);
    setAgentState((current) => ({
      ...current,
      conversationId: created.conversationId,
    }));
  }, [customerId]);

  const sentPrompt = useRef("");

  useEffect(() => {
    if (!initialPrompt || !conversation) return;
    if (sentPrompt.current === `${conversation.conversationId}:${initialPrompt}`) {
      return;
    }
    sentPrompt.current = `${conversation.conversationId}:${initialPrompt}`;
    sendMessage(initialPrompt, extraContext);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversation?.conversationId, initialPrompt]);

  const loadConversation = (conversationId) => {
    const next = getConversation(conversationId);
    if (!next) return;
    setConversation(next);
    setMessages(next.messages);
    setAgentState((current) => ({
      ...current,
      conversationId: next.conversationId,
    }));
  };

  const startNewConversation = () => {
    const created = createConversation(customerId, [
      {
        role: "assistant",
        text: WELCOME,
        createdAt: new Date().toISOString(),
      },
    ]);
    setConversation(created);
    setMessages(created.messages);
    setError("");
    setAgentState({
      online: true,
      processing: false,
      intent: null,
      agent: null,
      agentLabel: null,
      conversationId: created.conversationId,
    });
  };

  const sendMessage = async (text, context = extraContext) => {
    if (!text?.trim() || !conversation) return;

    const userMessage = {
      role: "user",
      text: text.trim(),
      createdAt: new Date().toISOString(),
    };

    setMessages((current) => [...current, userMessage]);
    appendMessages(conversation.conversationId, [userMessage]);
    setLoading(true);
    setError("");
    setAgentState((current) => ({
      ...current,
      processing: true,
      intent: "classifying",
      agent: null,
      agentLabel: "Intent Classifier",
    }));

    try {
      const result = await sendAiMessage(text.trim(), customerId, {
        ...context,
        conversationId: conversation.conversationId,
      });

      const assistantMessage = {
        role: "assistant",
        text: result.response,
        intent: result.intent,
        agent: result.agent,
        createdAt: new Date().toISOString(),
      };

      setMessages((current) => [...current, assistantMessage]);
      appendMessages(conversation.conversationId, [assistantMessage]);
      setAgentState({
        online: true,
        processing: false,
        intent: result.intent,
        agent: result.agent,
        agentLabel: result.agentLabel || result.agent,
        conversationId: result.conversation_id || conversation.conversationId,
      });
    } catch (err) {
      setError(err.message || "Network error");
      const fallback = {
        role: "assistant",
        text: "I couldn't reach the support service. Please try again in a moment.",
        createdAt: new Date().toISOString(),
      };
      setMessages((current) => [...current, fallback]);
      setAgentState((current) => ({
        ...current,
        processing: false,
        intent: null,
        agentLabel: "Support Agent",
      }));
    } finally {
      setLoading(false);
    }
  };

  return {
    messages,
    loading,
    error,
    agentState,
    conversation,
    conversations: getConversations(customerId),
    sendMessage,
    loadConversation,
    startNewConversation,
  };
}
