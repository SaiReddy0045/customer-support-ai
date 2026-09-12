import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import {
  FiMenu,
  FiSearch,
  FiShoppingCart,
  FiMessageCircle,
  FiUser,
  FiX,
} from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";

function Navbar() {
  const { user, isLoggedIn, logout } = useAuth();
  const { count } = useCart();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const onSearch = (event) => {
    event.preventDefault();
    const next = query.trim();
    navigate(next ? `/products?q=${encodeURIComponent(next)}` : "/products");
    setMenuOpen(false);
  };

  const closeMenus = () => {
    setMenuOpen(false);
    setProfileOpen(false);
  };

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="brand" onClick={closeMenus}>
          <span className="brand-mark">ABC</span>
          <span className="brand-text">
            <strong>ABC Technologies</strong>
            <small>Customer Support AI</small>
          </span>
        </Link>

        <nav className={`nav-links ${menuOpen ? "open" : ""}`}>
          <NavLink to="/" end onClick={closeMenus}>
            Home
          </NavLink>
          <NavLink to="/products" onClick={closeMenus}>
            Products
          </NavLink>
        </nav>

        <form className="nav-search" onSubmit={onSearch}>
          <FiSearch />
          <input
            type="search"
            placeholder="Search products"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </form>

        <div className="nav-actions">
          <Link to="/cart" className="icon-link" onClick={closeMenus}>
            <FiShoppingCart />
            <span>Cart</span>
            {count > 0 && <em className="cart-badge">{count}</em>}
          </Link>

          <Link to="/support" className="icon-link ai-link" onClick={closeMenus}>
            <FiMessageCircle />
            <span>AI Support</span>
          </Link>

          {isLoggedIn ? (
            <div className="profile-wrap">
              <button
                type="button"
                className="profile-trigger"
                onClick={() => setProfileOpen((open) => !open)}
              >
                <FiUser />
                <span className="profile-meta">
                  <strong>{user.name}</strong>
                  <small>{user.customerId}</small>
                </span>
              </button>
              {profileOpen && (
                <div className="profile-menu">
                  <Link to="/profile" onClick={closeMenus}>
                    Profile
                  </Link>
                  <Link to="/orders" onClick={closeMenus}>
                    Orders
                  </Link>
                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      closeMenus();
                      navigate("/");
                    }}
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link to="/login" className="login-chip" onClick={closeMenus}>
              Login
            </Link>
          )}

          <button
            type="button"
            className="menu-toggle"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Toggle menu"
          >
            {menuOpen ? <FiX /> : <FiMenu />}
          </button>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
