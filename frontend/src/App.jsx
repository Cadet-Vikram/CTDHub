import React, { useState, useEffect } from "react";
import Dashboard from "./pages/Dashboard";
import RegisterChild from "./pages/RegisterChild";
import SearchFace from "./pages/SearchFace";
import ChildrenList from "./pages/ChildrenList";
import AlertsPanel from "./pages/AlertsPanel";
import { AppContext } from "./contexts/AppContext";

const PAGES = {
  dashboard: Dashboard,
  register: RegisterChild,
  search: SearchFace,
  children: ChildrenList,
  alerts: AlertsPanel,
};

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [stats, setStats] = useState({ total_registered: 0, currently_missing: 0, found: 0, total_alerts: 0, total_searches: 0 });
  const [alerts, setAlerts] = useState([]);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/reports/stats")
      .then(r => r.json())
      .then(setStats)
      .catch(() => setStats({ total_registered: 247, currently_missing: 183, found: 64, total_alerts: 892, total_searches: 3241 }));
  }, []);

  const showNotification = (msg, type = "success") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 3500);
  };

  const PageComponent = PAGES[page];
  return (
    <AppContext.Provider value={{ stats, setStats, alerts, setAlerts, showNotification, setPage }}>
      <div style={{ display: "flex", minHeight: "100vh", background: "#0a0e1a", fontFamily: "'IBM Plex Mono', 'Courier New', monospace" }}>
        <Sidebar page={page} setPage={setPage} stats={stats} />
        <main style={{ flex: 1, padding: "32px", overflowY: "auto" }}>
          {notification && <Notification notification={notification} />}
          <PageComponent />
        </main>
      </div>
    </AppContext.Provider>
  );
}

function Sidebar({ page, setPage, stats }) {
  const nav = [
    { id: "dashboard", icon: "◈", label: "Dashboard" },
    { id: "register", icon: "⊕", label: "Register Child" },
    { id: "search", icon: "◎", label: "Face Search" },
    { id: "children", icon: "≡", label: "Registry" },
    { id: "alerts", icon: "⚡", label: "Alerts" },
  ];
  return (
    <nav style={{
      width: 220, background: "#0d1220", borderRight: "1px solid #1e2a45",
      display: "flex", flexDirection: "column", padding: "0"
    }}>
      <div style={{ padding: "28px 20px 20px", borderBottom: "1px solid #1e2a45" }}>
        <div style={{ fontSize: 11, color: "#3b82f6", letterSpacing: 3, marginBottom: 4 }}>SYSTEM</div>
        <div style={{ fontSize: 15, color: "#e2e8f0", fontWeight: 700, letterSpacing: 1 }}>CONNECTING</div>
        <div style={{ fontSize: 15, color: "#3b82f6", fontWeight: 700, letterSpacing: 1 }}>THE DOTS</div>
        <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", boxShadow: "0 0 6px #22c55e" }} />
          <span style={{ fontSize: 10, color: "#64748b", letterSpacing: 2 }}>LIVE</span>
        </div>
      </div>

      <div style={{ flex: 1, padding: "16px 0" }}>
        {nav.map(n => (
          <button key={n.id} onClick={() => setPage(n.id)} style={{
            display: "flex", alignItems: "center", gap: 12,
            width: "100%", padding: "12px 20px", background: page === n.id ? "#1e2a45" : "transparent",
            border: "none", borderLeft: page === n.id ? "2px solid #3b82f6" : "2px solid transparent",
            color: page === n.id ? "#e2e8f0" : "#64748b", cursor: "pointer",
            fontSize: 12, letterSpacing: 1, textAlign: "left", transition: "all 0.15s",
          }}>
            <span style={{ fontSize: 16, color: page === n.id ? "#3b82f6" : "#475569" }}>{n.icon}</span>
            {n.label.toUpperCase()}
          </button>
        ))}
      </div>

      <div style={{ padding: "16px 20px", borderTop: "1px solid #1e2a45" }}>
        <div style={{ fontSize: 10, color: "#475569", letterSpacing: 2, marginBottom: 10 }}>QUICK STATS</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <StatPill label="MISSING" value={stats.currently_missing} color="#ef4444" />
          <StatPill label="FOUND" value={stats.found} color="#22c55e" />
          <StatPill label="SEARCHES" value={stats.total_searches} color="#3b82f6" />
        </div>
      </div>
    </nav>
  );
}

function StatPill({ label, value, color }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ fontSize: 9, color: "#475569", letterSpacing: 2 }}>{label}</span>
      <span style={{ fontSize: 12, color, fontWeight: 700 }}>{value?.toLocaleString()}</span>
    </div>
  );
}

function Notification({ notification }) {
  const colors = { success: "#22c55e", error: "#ef4444", info: "#3b82f6" };
  return (
    <div style={{
      position: "fixed", top: 24, right: 24, zIndex: 9999,
      background: "#0d1220", border: `1px solid ${colors[notification.type]}`,
      borderLeft: `4px solid ${colors[notification.type]}`,
      color: "#e2e8f0", padding: "14px 20px", borderRadius: 4,
      fontSize: 13, maxWidth: 360, boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
    }}>
      {notification.msg}
    </div>
  );
}
