import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ProductGrid from "../components/ProductGrid";
import Loading from "../components/Loading";
import { getProducts, PRODUCT_CATEGORIES } from "../services/productService";
import { useCart } from "../context/CartContext";

function Products() {
  const { addToCart, busyId } = useCart();
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("All");
  const [sort, setSort] = useState("newest");
  const search = searchParams.get("q") || "";

  useEffect(() => {
    let active = true;
    getProducts().then((data) => {
      if (!active) return;
      setProducts(data);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const visible = useMemo(() => {
    let list = [...products];
    if (category !== "All") {
      list = list.filter((product) => product.category === category);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (product) =>
          product.name.toLowerCase().includes(q) ||
          product.description.toLowerCase().includes(q) ||
          product.category.toLowerCase().includes(q)
      );
    }
    if (sort === "price-asc") list.sort((a, b) => a.price - b.price);
    if (sort === "price-desc") list.sort((a, b) => b.price - a.price);
    if (sort === "rating") list.sort((a, b) => b.rating - a.rating);
    if (sort === "newest") {
      list.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    }
    return list;
  }, [products, category, search, sort]);

  return (
    <div className="page products-page">
      <div className="products-header">
        <div>
          <p className="eyebrow">Store</p>
          <h1>Technology products</h1>
          <p>Browse wearables, audio, smart home devices and accessories.</p>
        </div>
      </div>

      <div className="catalog-controls">
        <input
          className="search-field"
          value={search}
          placeholder="Search products"
          onChange={(event) => {
            const value = event.target.value;
            if (value) setSearchParams({ q: value });
            else setSearchParams({});
          }}
        />
        <div className="chip-row">
          {PRODUCT_CATEGORIES.map((item) => (
            <button
              key={item}
              type="button"
              className={category === item ? "chip active" : "chip"}
              onClick={() => setCategory(item)}
            >
              {item}
            </button>
          ))}
        </div>
        <select value={sort} onChange={(event) => setSort(event.target.value)}>
          <option value="newest">Newest</option>
          <option value="price-asc">Price Low → High</option>
          <option value="price-desc">Price High → Low</option>
          <option value="rating">Rating</option>
        </select>
      </div>

      {loading ? (
        <Loading label="Loading products..." />
      ) : (
        <ProductGrid products={visible} busyId={busyId} onAddToCart={addToCart} />
      )}
    </div>
  );
}

export default Products;
