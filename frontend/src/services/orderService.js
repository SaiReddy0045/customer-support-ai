import api, { USE_MOCK_API } from "./api";
import { STORAGE_KEYS, nextOrderId, readJson, writeJson } from "../utils/storage";

function getAllOrders() {
  return readJson(STORAGE_KEYS.ORDERS, []);
}

function saveAllOrders(orders) {
  writeJson(STORAGE_KEYS.ORDERS, orders);
  return orders;
}

export async function createOrder(orderInput) {
  if (USE_MOCK_API) {
    const order = {
      orderId: orderInput.orderId || nextOrderId(),
      customerId: orderInput.customerId,
      items: orderInput.items,
      totals: orderInput.totals,
      totalAmount: orderInput.totals?.total ?? orderInput.totalAmount,
      paymentMethod: orderInput.paymentMethod,
      paymentStatus: orderInput.paymentStatus,
      orderStatus: orderInput.orderStatus,
      transactionId: orderInput.transactionId || null,
      shippingAddress: orderInput.shippingAddress,
      createdAt: new Date().toISOString(),
    };

    saveAllOrders([order, ...getAllOrders()]);
    return order;
  }

  const response = await api.post("/orders", orderInput);
  return response.data;
}

export async function getOrdersByCustomer(customerId) {
  if (USE_MOCK_API) {
    return getAllOrders().filter((order) => order.customerId === customerId);
  }

  const response = await api.get(`/orders/${customerId}`);
  return response.data;
}

export async function getOrderById(orderId) {
  if (USE_MOCK_API) {
    return getAllOrders().find((order) => order.orderId === orderId) || null;
  }

  const response = await api.get(`/orders/detail/${orderId}`);
  return response.data;
}

export async function updateOrderStatus(orderId, updates) {
  if (USE_MOCK_API) {
    const next = getAllOrders().map((order) =>
      order.orderId === orderId ? { ...order, ...updates } : order
    );
    saveAllOrders(next);
    return next.find((order) => order.orderId === orderId) || null;
  }

  const response = await api.post("/refund", { orderId, ...updates });
  return response.data;
}

export function getOrderStats(orders) {
  return {
    total: orders.length,
    pending: orders.filter((order) =>
      ["Pending Payment", "Processing", "Order Confirmed"].includes(order.orderStatus)
    ).length,
    completed: orders.filter((order) =>
      ["Shipped", "Delivered"].includes(order.orderStatus)
    ).length,
    refunds: orders.filter((order) =>
      ["Refund Requested", "Refunded"].includes(order.orderStatus)
    ).length,
  };
}
