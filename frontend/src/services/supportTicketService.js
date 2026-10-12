import api from "./api";

export async function getSupportTickets() {
  const response = await api.get("/support/tickets");
  return response.data;
}

export async function createSupportTicket(payload) {
  const response = await api.post("/support/tickets", payload);
  return response.data;
}

export async function getSupportTicket(ticketId) {
  const response = await api.get(`/support/tickets/${encodeURIComponent(ticketId)}`);
  return response.data;
}
