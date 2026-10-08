import React, { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

const PAGES = [
  { to: "/threads", label: "Threads", hint: "MULTI vs MONO" },
  { to: "/scheduling", label: "Scheduling", hint: "Sincronismo" },
];

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKey = (e) => e.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <div className="app app-stage app-with-menu">
      <button
        type="button"
        className={`menu-btn ${menuOpen ? "menu-btn-open" : ""}`}
        onClick={() => setMenuOpen((o) => !o)}
        aria-label="Menu"
        aria-expanded={menuOpen}
      >
        <span />
        <span />
        <span />
      </button>

      <div
        className={`menu-overlay ${menuOpen ? "menu-overlay-open" : ""}`}
        onClick={() => setMenuOpen(false)}
      />
      <nav className={`menu-drawer ${menuOpen ? "menu-drawer-open" : ""}`}>
        <div className="menu-title">Trânsito</div>
        {PAGES.map((page) => (
          <NavLink
            key={page.to}
            to={page.to}
            className="menu-link"
            onClick={() => setMenuOpen(false)}
          >
            <span className="menu-link-label">{page.label}</span>
            <span className="menu-link-hint">{page.hint}</span>
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  );
}
