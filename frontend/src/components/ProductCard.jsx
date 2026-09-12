import { Link } from "react-router-dom";
import { FiStar } from "react-icons/fi";
import ProductImage from "./ProductImage";
import { formatPrice } from "../utils/format";

function ProductCard({ product, onAddToCart, busy = false }) {
  const inStock = product.stock > 0;

  return (
    <article className="product-card">
      <ProductImage icon={product.icon} name={product.category} />
      <p className="product-category">{product.category}</p>
      <h3>{product.name}</h3>
      <p className="product-description">{product.description}</p>
      <div className="product-meta">
        <strong>{formatPrice(product.price)}</strong>
        <span className="rating">
          <FiStar /> {product.rating}
        </span>
      </div>
      <p className={`stock-badge ${inStock ? "in" : "out"}`}>
        {inStock ? "In stock" : "Out of stock"}
      </p>
      <div className="product-actions">
        <button
          type="button"
          disabled={!inStock || busy}
          onClick={() => onAddToCart(product)}
        >
          {busy ? "Adding..." : "Add to Cart"}
        </button>
        <Link to={`/products/${product.id}`} className="ghost-btn">
          View Details
        </Link>
      </div>
    </article>
  );
}

export default ProductCard;
