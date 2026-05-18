import React, { useContext } from "react";
import { AppContext } from "../contexts/AppContext";

const MOCK_RECENT = [
  { id: 1, name: "Ravi Kumar", age: 8, location: "Chennai Central", date: "2024-01-15", status: "missing" },
  { id: 2, name: "Priya Sharma", age: 12, location: "Mumbai Andheri", date: "2024-01-14", status: "missing" },
  { id: 3, name: "Arjun Patel", age: 6, location: "Delhi Connaught", date: "2024-01-12", status: "found" },
  { id: 4, name: "Meena Devi", age: 9, location: "Kolkata Park St", date: "2024-01-10", status: "missing" },
  { id: 5, name: "Suresh Reddy", age: 14, location: "Hyderabad Jubilee", date: "2024-01-09", status: "found" },
];

const MOCK_ACTIVITY = [
  { time: "09:42", event: "Face match found — 94.2% confidence", type: "match" },
  { time: "09:15", event: "SOS Alert sent for Ravi Kumar", type: "alert" },
  { time: "08:55", event: "New child registered: Priya Sharma", type: "register" },
  { time: "08:30", event: "Age progression generated for case #A2241", type: "info" },
  { time: "07:52", event: "Authority notified — Chennai Zone 4", type: "alert" },
];

export default function Dashboard() {
  const { stats, setPage } = useContext(AppContext);

  return (
    <div>
      <Header />
      <StatsGrid stats={stats} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24, marginTop: 24 }}>
        <RecentCases cases={MOCK_RECENT} setPage={setPage} />
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <ActivityFeed activity={MOCK_ACTIVITY} />
          <QuickActions setPage={setPage} />
        </div>
      </div>
    </div>
  );
}

function Header() {
  const now = new Date().toLocaleDateString("en-IN", { weekday: "long", year: "numeric", month: "long", day: "numeric" });
  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ fontSize: 10, color: "#475569", letterSpacing: 3, marginBottom: 6 }}>{now.toUpperCase()}</div>
      <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: "#e2e8f0", letterSpacing: -0.5 }}>
        Operations <span style={{ color: "#3b82f6" }}>Dashboard</span>
      </h1>
      <p style={{ margin: "6px 0 0", fontSize: 12, color: "#64748b" }}>
        Real-time overview of the Connecting the Dots identification system
      </p>
    </div>
  );
}

function StatsGrid({ stats }) {
  const cards = [
    { label: "CURRENTLY MISSING", value: stats.currently_missing || 183, color: "#ef4444", icon: "◉", sub: "Across all states" },
    { label: "CHILDREN FOUND", value: stats.found || 64, color: "#22c55e", icon: "◎", sub: "This year" },
    { label: "FACE SEARCHES", value: stats.total_searches || 3241, color: "#3b82f6", icon: "◈", sub: "Total queries" },
    { label: "ALERTS SENT", value: stats.total_alerts || 892, color: "#f59e0b", icon: "⚡", sub: "To authorities" },
    { label: "TOTAL REGISTERED", value: stats.total_registered || 247, color: "#8b5cf6", icon: "≡", sub: "In system" },
    { label: "SUCCESS RATE", value: "26.0%", color: "#06b6d4", icon: "◆", sub: "Recovery rate" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
      {cards.map(c => (
        <div key={c.label} style={{
          background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8,
          padding: "20px 24px", position: "relative", overflow: "hidden",
        }}>
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: c.color, opacity: 0.6 }} />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ fontSize: 9, color: "#475569", letterSpacing: 3, marginBottom: 8 }}>{c.label}</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: c.color }}>{typeof c.value === "number" ? c.value.toLocaleString() : c.value}</div>
              <div style={{ fontSize: 10, color: "#475569", marginTop: 4 }}>{c.sub}</div>
            </div>
            <span style={{ fontSize: 24, color: c.color, opacity: 0.3 }}>{c.icon}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function RecentCases({ cases, setPage }) {
  return (
    <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8 }}>
      <div style={{ padding: "18px 24px", borderBottom: "1px solid #1e2a45", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 11, color: "#94a3b8", letterSpacing: 2 }}>RECENT CASES</span>
        <button onClick={() => setPage("children")} style={{
          background: "transparent", border: "1px solid #1e2a45", color: "#3b82f6",
          fontSize: 10, padding: "4px 12px", borderRadius: 3, cursor: "pointer", letterSpacing: 1,
        }}>VIEW ALL</button>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {["NAME", "AGE", "LAST SEEN", "DATE", "STATUS"].map(h => (
              <th key={h} style={{ padding: "10px 24px", textAlign: "left", fontSize: 9, color: "#475569", letterSpacing: 2, fontWeight: 500, borderBottom: "1px solid #1e2a45" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cases.map(c => (
            <tr key={c.id} style={{ borderBottom: "1px solid #111827" }}>
              <td style={{ padding: "12px 24px", fontSize: 12, color: "#e2e8f0" }}>{c.name}</td>
              <td style={{ padding: "12px 24px", fontSize: 12, color: "#94a3b8" }}>{c.age}</td>
              <td style={{ padding: "12px 24px", fontSize: 11, color: "#64748b" }}>{c.location}</td>
              <td style={{ padding: "12px 24px", fontSize: 11, color: "#64748b" }}>{c.date}</td>
              <td style={{ padding: "12px 24px" }}>
                <span style={{
                  fontSize: 9, letterSpacing: 2, padding: "3px 8px", borderRadius: 2,
                  background: c.status === "found" ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
                  color: c.status === "found" ? "#22c55e" : "#ef4444",
                  border: `1px solid ${c.status === "found" ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
                }}>{c.status.toUpperCase()}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActivityFeed({ activity }) {
  const typeColors = { match: "#22c55e", alert: "#ef4444", register: "#3b82f6", info: "#64748b" };
  return (
    <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8 }}>
      <div style={{ padding: "18px 20px", borderBottom: "1px solid #1e2a45" }}>
        <span style={{ fontSize: 11, color: "#94a3b8", letterSpacing: 2 }}>LIVE ACTIVITY</span>
      </div>
      <div style={{ padding: "8px 0" }}>
        {activity.map((a, i) => (
          <div key={i} style={{ padding: "10px 20px", display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: typeColors[a.type], marginTop: 4, flexShrink: 0, boxShadow: `0 0 6px ${typeColors[a.type]}` }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11, color: "#94a3b8" }}>{a.event}</div>
              <div style={{ fontSize: 9, color: "#475569", marginTop: 3, letterSpacing: 1 }}>{a.time}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function QuickActions({ setPage }) {
  const actions = [
    { label: "Register Missing Child", icon: "⊕", page: "register", color: "#3b82f6" },
    { label: "Search by Face Photo", icon: "◎", page: "search", color: "#22c55e" },
    { label: "Send Broadcast Alert", icon: "⚡", page: "alerts", color: "#f59e0b" },
  ];
  return (
    <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8 }}>
      <div style={{ padding: "18px 20px", borderBottom: "1px solid #1e2a45" }}>
        <span style={{ fontSize: 11, color: "#94a3b8", letterSpacing: 2 }}>QUICK ACTIONS</span>
      </div>
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
        {actions.map(a => (
          <button key={a.label} onClick={() => setPage(a.page)} style={{
            display: "flex", alignItems: "center", gap: 12,
            background: "transparent", border: `1px solid ${a.color}22`,
            color: a.color, padding: "12px 16px", borderRadius: 6, cursor: "pointer",
            fontSize: 12, letterSpacing: 0.5, textAlign: "left", transition: "all 0.15s",
          }}
            onMouseOver={e => e.currentTarget.style.background = `${a.color}11`}
            onMouseOut={e => e.currentTarget.style.background = "transparent"}
          >
            <span style={{ fontSize: 18 }}>{a.icon}</span>
            {a.label}
          </button>
        ))}
      </div>
    </div>
  );
}
