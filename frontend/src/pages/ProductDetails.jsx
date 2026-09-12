import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FiStar } from "react-icons/fi";
import ProductImage from "../components/ProductImage";
import Loading from "../components/Loading";
import { getProductById } from "../services/productService";
import { useCart } from "../context/CartContext";
import { formatPrice } from "../utils/format";

function ProductDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { addToCart, busyId } = useCart();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getProductById(id).then((data) => {
      if (!active) return;
      setProduct(data);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="page">
        <Loading label="Loading product..." />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="page empty-state">
        <h2>Product not found</h2>
        <Link to="/products">Back to products</Link>
      </div>
    );
  }

  const askAi = () => {
    navigate("/support", {
      state: {
        prompt: `Tell me about ${product.name}.`,
        context: {
          productId: product.id,
          productName: product.name,
          productPrice: product.price,
          productDescription: product.description,
        },
      },
    });
  };

  const buyNow = async () => {
    await addToCart(product, quantity);
    navigate("/checkout");
  };

  return (
    <div className="page product-details">
      <div className="details-grid">
        <ProductImage product={product} large />
        <div className="details-copy">
          <p className="product-category">{product.category}</p>
          <h1>{product.name}</h1>
          <p className="rating">
            <FiStar /> {product.rating} · {product.reviews} reviews
          </p>
          <p className="price-lg">{formatPrice(product.price)}</p>
          <p>{product.description}</p>
          <p className={`stock-badge ${product.stock > 0 ? "in" : "out"}`}>
            {product.stock > 0 ? `${product.stock} available` : "Out of stock"}
          </p>

          <div className="qty-control">
            <button type="button" onClick={() => setQuantity((n) => Math.max(1, n - 1))}>
              −
            </button>
            <span>{quantity}</span>
            <button type="button" onClick={() => setQuantity((n) => n + 1)}>
              +
            </button>
          </div>

          <div className="hero-actions">
            <button
              type="button"
              className="btn primary"
              disabled={product.stock === 0 || busyId === product.id}
              onClick={() => addToCart(product, quantity)}
            >
              {busyId === product.id ? "Adding to cart..." : "Add to Cart"}
            </button>
            <button
              type="button"
              className="btn ghost"
              disabled={product.stock === 0}
              onClick={buyNow}
            >
              Buy Now
            </button>
            <button type="button" className="btn text" onClick={askAi}>
              Ask AI about this product
            </button>
          </div>
        </div>
      </div>

      <section className="spec-card">
        <h2>Specifications</h2>
        <dl>
          {Object.entries(product.specs).map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}

export default ProductDetails;
