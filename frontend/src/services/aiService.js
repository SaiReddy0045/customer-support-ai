import api, { USE_MOCK_API } from "./api";
import { getOrdersByCustomer } from "./orderService";
import { getProducts } from "./productService";

function delay(ms = 900) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function classifyIntent(message) {
  const text = message.toLowerCase();

  if (
    text.includes("refund") ||
    text.includes("return") ||
    text.includes("money back")
  ) {
    return { intent: "refund", agent: "refund_agent", agentLabel: "Refund Agent" };
  }

  if (
    text.includes("charged") ||
    text.includes("billing") ||
    text.includes("invoice") ||
    text.includes("payment") ||
    text.includes("twice") ||
    text.includes("upi") ||
    text.includes("card")
  ) {
    return { intent: "billing", agent: "billing_agent", agentLabel: "Billing Agent" };
  }

  if (
    text.includes("order") ||
    text.includes("ship") ||
    text.includes("delivery") ||
    text.includes("track") ||
    text.includes("where")
  ) {
    return { intent: "order", agent: "support_agent", agentLabel: "Support Agent" };
  }

  if (
    text.includes("product") ||
    text.includes("buy") ||
    text.includes("recommend") ||
    text.includes("watch") ||
    text.includes("earbuds") ||
    text.includes("speaker")
  ) {
    return {
      intent: "product",
      agent: "support_agent",
      agentLabel: "Support Agent",
    };
  }

  return {
    intent: "general_support",
    agent: "support_agent",
    agentLabel: "Support Agent",
  };
}

async function buildMockResponse(message, customerId, context = {}) {
  const { intent, agent, agentLabel } = classifyIntent(message);
  const text = message.toLowerCase();
  let orders = [];
  let products = [];

  try {
    if (customerId) {
      orders = await getOrdersByCustomer(customerId);
    }
    products = await getProducts();
  } catch {
    orders = [];
  }

  const latestOrder = orders[0];
  let response = "I can help with orders, billing, refunds and product questions.";

  if (intent === "refund") {
    response = latestOrder
      ? `I can help with a refund for order ${latestOrder.orderId} (${latestOrder.orderStatus}). Please confirm if you want to start a refund request for this order.`
      : "I can help with your refund request. Please provide your order ID, or sign in so I can look up your purchases.";
  } else if (intent === "billing") {
    response = latestOrder
      ? `I'll review billing for order ${latestOrder.orderId}. Amount: ₹${latestOrder.totalAmount?.toLocaleString("en-IN")}. Payment status: ${latestOrder.paymentStatus}. If you were charged twice, share the extra Transaction ID.`
      : "I'll help you review billing information. Please share your order ID or Customer ID.";
  } else if (intent === "order") {
    response = latestOrder
      ? `Your most recent order is ${latestOrder.orderId}, placed on ${new Date(latestOrder.createdAt).toLocaleDateString("en-IN")}. Current status: ${latestOrder.orderStatus}.`
      : "I can help you check order status. Please provide your order ID, or log in so I can find your orders.";
  } else if (intent === "product") {
    const mentioned = products.find((product) =>
      text.includes(product.name.toLowerCase().split(" ")[1] || "")
    );
    const featured = mentioned || products.find((product) => product.featured);
    response = featured
      ? `${featured.name} is a popular ${featured.category.toLowerCase()} pick at ₹${featured.price.toLocaleString("en-IN")} (${featured.rating}★). I can also compare it with other ABC products.`
      : "I can help you choose a product. Tell me whether you need wearables, audio, smart home or accessories.";
  } else if (text.includes("hello") || text.includes("hi")) {
    response =
      "Hello. I'm the ABC Technologies AI Customer Support Assistant. Ask me about an order, a charge, a refund, or a product.";
  }

  if (context.productName) {
    response = `${context.productName}: ${context.productDescription || "I can share details, availability and similar options."} Price ₹${Number(context.productPrice || 0).toLocaleString("en-IN")}. Would you like a comparison or help placing an order?`;
  }

  if (context.orderId) {
    response = `Looking at order ${context.orderId}. I can explain status, billing or start a refund from here. What would you like to do?`;
  }

  return {
    response,
    intent,
    agent,
    agentLabel,
    customer_id: customerId || null,
    conversation_id: context.conversationId || null,
    metadata: {
      source: "frontend_mock",
      latestOrderId: latestOrder?.orderId || null,
    },
  };
}

export async function sendMessage(message, customerId, context = {}) {
  if (USE_MOCK_API) {
    await delay();
    return buildMockResponse(message, customerId, context);
  }

  const response = await api.post("/chat", {
    message,
    customer_id: customerId,
    conversation_id: context.conversationId,
    metadata: context,
  });

  return response.data;
}
