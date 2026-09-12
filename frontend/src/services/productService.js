import api, { USE_MOCK_API } from "./api";
import catalog from "../data/products";

function delay(ms = 250) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function getProducts() {
  if (USE_MOCK_API) {
    await delay();
    return catalog;
  }

  const response = await api.get("/products");
  return response.data;
}

export async function getProductById(id) {
  if (USE_MOCK_API) {
    await delay();
    return catalog.find((product) => product.id === id) || null;
  }

  const response = await api.get(`/products/${id}`);
  return response.data;
}

export function getFeaturedProducts(products = catalog) {
  return products.filter((product) => product.featured);
}

export const PRODUCT_CATEGORIES = [
  "All",
  "Wearables",
  "Audio",
  "Smart Home",
  "Accessories",
];
