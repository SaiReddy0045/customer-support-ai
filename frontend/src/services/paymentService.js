import api, { USE_MOCK_API } from "./api";
import { nextTransactionId } from "../utils/storage";

function delay(ms = 1400) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function shouldFail(payload) {
  const card = (payload.cardNumber || "").replace(/\s/g, "");
  const upi = (payload.upiId || "").toLowerCase();
  const cvv = payload.cvv || "";

  if (card.endsWith("0002") || cvv === "000" || upi.includes("fail")) {
    return true;
  }

  return false;
}

export async function processDemoPayment(payload) {
  if (USE_MOCK_API) {
    await delay();

    if (shouldFail(payload)) {
      const error = new Error(
        "Demo payment failed. Please try again or use another method."
      );
      error.code = "PAYMENT_FAILED";
      throw error;
    }

    return {
      success: true,
      transactionId: nextTransactionId(),
      amount: payload.amount,
      paymentMethod: payload.paymentMethod,
      paidAt: new Date().toISOString(),
      demo: true,
    };
  }

  const response = await api.post("/payment/demo", payload);
  return response.data;
}
