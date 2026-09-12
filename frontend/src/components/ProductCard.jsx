import { Link } from "react-router-dom";
import { FiStar } from "react-icons/fi";
import ProductImage from "./ProductImage";
import { formatPrice } from "../utils/format";

function ProductCard({ product, onAddToCart, busy = false }) {
  const inStock = product.stock > 0;

  return (
    <article className="product-card">
      <Link to={`/products/${product.id}`} className="product-media">
        <ProductImage product={product} />
        {product.featured && <span className="photo-badge">Featured</span>}
        {!inStock && <span className="photo-badge sold">Sold out</span>}
      </Link>
      <div className="product-body">
        <p className="product-category">{product.category}</p>
        <h3>
          <Link to={`/products/${product.id}`}>{product.name}</Link>
        </h3>
        <p className="product-description">{product.description}</p>
        <div className="product-meta">
          <strong>{formatPrice(product.price)}</strong>
          <span className="rating">
            <FiStar /> {product.rating}
            <em>({product.reviews})</em>
          </span>
        </div>
        <p className={`stock-badge ${inStock ? "in" : "out"}`}>
          {inStock ? "In stock · Free shipping over ₹2,000" : "Out of stock"}
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
      </div>
    </article>
  );
}

export default ProductCard;
