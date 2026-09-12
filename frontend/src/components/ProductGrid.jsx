import ProductCard from "./ProductCard";

function ProductGrid({ products, onAddToCart, busyId }) {
  if (!products || products.length === 0) {
    return (
      <div className="empty-state">
        <h3>No products found</h3>
        <p>Try another search or category.</p>
      </div>
    );
  }

  return (
    <div className="product-grid">
      {products.map((product) => (
        <ProductCard
          key={product.id}
          product={product}
          busy={busyId === product.id}
          onAddToCart={onAddToCart}
        />
      ))}
    </div>
  );
}

export default ProductGrid;
