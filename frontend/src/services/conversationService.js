import { STORAGE_KEYS, nextConversationId, readJson, writeJson } from "../utils/storage";

function getAllConversations() {
  return readJson(STORAGE_KEYS.CONVERSATIONS, []);
}

function saveAll(conversations) {
  writeJson(STORAGE_KEYS.CONVERSATIONS, conversations);
  return conversations;
}

export function getConversations(customerId) {
  const id = customerId || "guest";
  return getAllConversations()
    .filter((conversation) => conversation.customerId === id)
    .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
}

export function getConversation(conversationId) {
  return (
    getAllConversations().find(
      (conversation) => conversation.conversationId === conversationId
    ) || null
  );
}

export function createConversation(customerId, firstMessages = []) {
  const now = new Date().toISOString();
  const conversation = {
    conversationId: nextConversationId(),
    customerId: customerId || "guest",
    messages: firstMessages,
    createdAt: now,
    updatedAt: now,
  };

  saveAll([conversation, ...getAllConversations()]);
  return conversation;
}

export function appendMessages(conversationId, messages) {
  const now = new Date().toISOString();
  const next = getAllConversations().map((conversation) => {
    if (conversation.conversationId !== conversationId) return conversation;
    return {
      ...conversation,
      messages: [...conversation.messages, ...messages],
      updatedAt: now,
    };
  });

  saveAll(next);
  return next.find((conversation) => conversation.conversationId === conversationId);
}
