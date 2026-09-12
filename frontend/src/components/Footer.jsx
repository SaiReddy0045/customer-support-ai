import { Link } from "react-router-dom";

function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div>
          <strong>ABC Technologies</strong>
          <p>Smart devices, accessories and AI-powered customer support.</p>
        </div>
        <div className="footer-links">
          <Link to="/products">Store</Link>
          <Link to="/support">AI Support</Link>
          <Link to="/orders">Orders</Link>
          <Link to="/profile">Account</Link>
        </div>
        <p className="footer-note">Frontend demo for the LangGraph support agent.</p>
      </div>
    </footer>
  );
}

export default Footer;
