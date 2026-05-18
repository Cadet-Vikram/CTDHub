// src/components/Sidebar.jsx
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Search, UserPlus, Users, Bell,
  AlertTriangle, Brain, LogOut, Shield,
} from "lucide-react";
import { useAuthStore } from "../hooks/useAuthStore";

const NAV_ITEMS = [
  { to: "/",         icon: LayoutDashboard, label: "Dashboard" },
  { to: "/search",   icon: Search,          label: "Search / Match" },
  { to: "/register", icon: UserPlus,        label: "Register Child" },
  { to: "/missing",  icon: Users,           label: "Missing Children" },
  { to: "/alerts",   icon: Bell,            label: "Alerts" },
  { to: "/sos",      icon: AlertTriangle,   label: "SOS Emergency",  danger: true },
  { to: "/training", icon: Brain,           label: "Model Training" },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();

  return (
    <aside style={{
      width: "var(--sidebar-width)",
      background: "var(--bg-surface)",
      borderRight: "1px solid var(--border)",
      position: "fixed",
      top: 0, left: 0, bottom: 0,
      display: "flex",
      flexDirection: "column",
      zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{ padding: "1.5rem 1.25rem", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{
            width: 36, height: 36,
            background: "linear-gradient(135deg, #3b82f6, #06b6d4)",
            borderRadius: 10,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Shield size={18} color="white" />
          </div>
          <div>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 13, lineHeight: 1.2 }}>
              Connecting
            </div>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 13, lineHeight: 1.2, color: "var(--accent-cyan)" }}>
              the Dots
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: "1rem 0.75rem", display: "flex", flexDirection: "column", gap: 4 }}>
        {NAV_ITEMS.map(({ to, icon: Icon, label, danger }) => (
          <NavLink key={to} to={to} end={to === "/"} style={({ isActive }) => ({
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            padding: "0.55rem 0.75rem",
            borderRadius: "var(--radius)",
            textDecoration: "none",
            fontSize: 14,
            fontWeight: 500,
            color: isActive
              ? (danger ? "#ef4444" : "var(--accent-blue)")
              : danger ? "#f87171" : "var(--text-secondary)",
            background: isActive
              ? (danger ? "rgba(239,68,68,0.1)" : "rgba(59,130,246,0.1)")
              : "transparent",
            transition: "all 0.15s",
          })}>
            <Icon size={16} />
            {label}
            {danger && (
              <span style={{
                marginLeft: "auto",
                width: 8, height: 8,
                background: "#ef4444",
                borderRadius: "50%",
                animation: "sos-pulse 2s infinite",
              }} />
            )}
          </NavLink>
        ))}
      </nav>

      {/* User footer */}
      <div style={{ padding: "1rem 0.75rem", borderTop: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
          <div style={{
            width: 32, height: 32,
            background: "var(--bg-hover)",
            borderRadius: "50%",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 13, fontWeight: 700, color: "var(--accent-blue)",
          }}>
            {user?.full_name?.[0] || "?"}
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600 }}>{user?.full_name || "Officer"}</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "capitalize" }}>
              {user?.role || "user"}
            </div>
          </div>
        </div>
        <button onClick={logout} className="btn btn-ghost" style={{ width: "100%", justifyContent: "center", padding: "0.4rem" }}>
          <LogOut size={14} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
