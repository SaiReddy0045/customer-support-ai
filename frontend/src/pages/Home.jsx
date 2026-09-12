import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  FiZap,
  FiShield,
  FiCpu,
  FiRefreshCw,
  FiMessageCircle,
} from "react-icons/fi";
import ProductGrid from "../components/ProductGrid";
import Loading from "../components/Loading";
import { getFeaturedProducts, getProducts } from "../services/productService";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";

const reasons = [
  { icon: FiZap, title: "Fast Support", text: "Ask the AI assistant about orders, billing and products instantly." },
  { icon: FiShield, title: "Secure Checkout", text: "Demo ABC Pay flow with clear payment and order records." },
  { icon: FiCpu, title: "Smart Recommendations", text: "Get help choosing wearables, audio and smart home devices." },
  { icon: FiRefreshCw, title: "Easy Refunds", text: "Create realistic refund scenarios for the future Refund Agent." },
  { icon: FiMessageCircle, title: "AI-Powered Assistance", text: "Intent routing preview for Billing, Refund and Support agents." },
];

function Home() {
  const { addToCart, busyId } = useCart();
  const { user } = useAuth();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getProducts().then((data) => {
      if (!active) return;
      setProducts(getFeaturedProducts(data));
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="home-page">
      <section className="hero-banner">
        <img src="/images/hero.jpg" alt="ABC Technologies devices on a desk" />
        <div className="hero-overlay">
          <p className="eyebrow light">ABC Technologies</p>
          <h1>Technology made for you.</h1>
          <p>
            Explore smart devices, accessories and technology products from ABC
            Technologies.
          </p>
          {user && (
            <p className="welcome-line">
              Welcome back, {user.name} · {user.customerId}
            </p>
          )}
          <div className="hero-actions">
            <Link to="/products" className="btn primary">
              Explore Products
            </Link>
            <Link to="/support" className="btn light">
              Ask AI Assistant
            </Link>
          </div>
        </div>
      </section>

      <div className="page">
        <section className="ai-promo-wide">
          <img src="/images/lifestyle.jpg" alt="Customer using a smartphone" />
          <article>
            <p className="eyebrow">Need help choosing a product?</p>
            <h2>Ask our AI Customer Support Assistant.</h2>
            <p>
              Billing, refunds, order tracking and product advice — one chat that
              will later connect to LangGraph agents.
            </p>
            <div className="mini-chat">
              <div className="mini-bubble bot">Where is my latest order?</div>
              <div className="mini-bubble user">I can check that for you.</div>
            </div>
            <Link to="/support" className="btn primary">
              Talk to AI Support
            </Link>
          </article>
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Our products</p>
              <h2>Featured Products</h2>
            </div>
            <Link to="/products">View all</Link>
          </div>
          {loading ? (
            <Loading label="Loading products..." />
          ) : (
            <ProductGrid
              products={products}
              busyId={busyId}
              onAddToCart={addToCart}
            />
          )}
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Why ABC</p>
              <h2>Why ABC Technologies?</h2>
            </div>
          </div>
          <div className="reason-grid">
            {reasons.map((reason) => (
              <article key={reason.title} className="reason-card">
                <reason.icon />
                <h3>{reason.title}</h3>
                <p>{reason.text}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export default Home;
