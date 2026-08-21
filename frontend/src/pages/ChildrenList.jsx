import React, { useState, useEffect } from "react";

const MOCK_CHILDREN = [
  { id: "1", name: "Ravi Kumar", age: 8, gender: "Male", status: "missing", last_seen_location: "Chennai Central", created_at: "2024-01-15", has_embedding: true, contact_number: "+91-98765-43210" },
  { id: "2", name: "Priya Sharma", age: 12, gender: "Female", status: "missing", last_seen_location: "Mumbai Andheri", created_at: "2024-01-14", has_embedding: true, contact_number: "+91-87654-32109" },
  { id: "3", name: "Arjun Patel", age: 6, gender: "Male", status: "found", last_seen_location: "Delhi Connaught", created_at: "2024-01-12", has_embedding: false, contact_number: "+91-76543-21098" },
  { id: "4", name: "Meena Devi", age: 9, gender: "Female", status: "missing", last_seen_location: "Kolkata Park St", created_at: "2024-01-10", has_embedding: true, contact_number: "+91-65432-10987" },
  { id: "5", name: "Suresh Reddy", age: 14, gender: "Male", status: "found", last_seen_location: "Hyderabad Jubilee", created_at: "2024-01-09", has_embedding: true, contact_number: "+91-54321-09876" },
  { id: "6", name: "Ananya Singh", age: 7, gender: "Female", status: "missing", last_seen_location: "Bengaluru MG Road", created_at: "2024-01-08", has_embedding: false, contact_number: "+91-43210-98765" },
];

export default function ChildrenList() {
  const [children, setChildren] = useState(MOCK_CHILDREN);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const filtered = children.filter(c => {
    const matchStatus = filter === "all" || c.status === filter;
    const matchSearch = !search || c.name.toLowerCase().includes(search.toLowerCase()) || c.last_seen_location.toLowerCase().includes(search.toLowerCase());
    return matchStatus && matchSearch;
  });

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 10, color: "#475569", letterSpacing: 3, marginBottom: 6 }}>CASE MANAGEMENT</div>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "#e2e8f0" }}>Children <span style={{ color: "#8b5cf6" }}>Registry</span></h1>
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 24, alignItems: "center" }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search by name or location..."
          style={{ flex: 1, background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 4, padding: "10px 16px", color: "#e2e8f0", fontSize: 12, fontFamily: "inherit", outline: "none" }}
        />
        {["all", "missing", "found"].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            background: filter === f ? "#1e2a45" : "transparent",
            border: `1px solid ${filter === f ? "#3b82f6" : "#1e2a45"}`,
            color: filter === f ? "#e2e8f0" : "#64748b",
            padding: "10px 20px", borderRadius: 4, cursor: "pointer",
            fontSize: 10, letterSpacing: 2, fontFamily: "inherit",
          }}>{f.toUpperCase()}</button>
        ))}
      </div>

      <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #1e2a45" }}>
              {["NAME", "AGE", "GENDER", "LAST SEEN", "REGISTERED", "EMBEDDING", "CONTACT", "STATUS", "ACTIONS"].map(h => (
                <th key={h} style={{ padding: "12px 20px", textAlign: "left", fontSize: 9, color: "#475569", letterSpacing: 2, fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(c => (
              <tr key={c.id} style={{ borderBottom: "1px solid #0a0e1a" }}>
                <td style={{ padding: "14px 20px", fontSize: 13, color: "#e2e8f0", fontWeight: 600 }}>{c.name}</td>
                <td style={{ padding: "14px 20px", fontSize: 12, color: "#94a3b8" }}>{c.age}</td>
                <td style={{ padding: "14px 20px", fontSize: 12, color: "#94a3b8" }}>{c.gender}</td>
                <td style={{ padding: "14px 20px", fontSize: 11, color: "#64748b" }}>{c.last_seen_location}</td>
                <td style={{ padding: "14px 20px", fontSize: 11, color: "#64748b" }}>{c.created_at}</td>
                <td style={{ padding: "14px 20px" }}>
                  <span style={{ fontSize: 9, color: c.has_embedding ? "#22c55e" : "#475569" }}>
                    {c.has_embedding ? "◎ YES" : "○ NO"}
                  </span>
                </td>
                <td style={{ padding: "14px 20px", fontSize: 11, color: "#64748b" }}>{c.contact_number}</td>
                <td style={{ padding: "14px 20px" }}>
                  <StatusBadge status={c.status} />
                </td>
                <td style={{ padding: "14px 20px" }}>
                  <div style={{ display: "flex", gap: 8 }}>
                    <ActionBtn label="VIEW" color="#3b82f6" />
                    <ActionBtn label="ALERT" color="#ef4444" />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ padding: "12px 20px", borderTop: "1px solid #1e2a45", fontSize: 10, color: "#475569", letterSpacing: 2 }}>
          SHOWING {filtered.length} OF {children.length} RECORDS
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = { missing: ["rgba(239,68,68,0.1)", "#ef4444", "rgba(239,68,68,0.3)"], found: ["rgba(34,197,94,0.1)", "#22c55e", "rgba(34,197,94,0.3)"] };
  const [bg, fg, bd] = colors[status] || colors.missing;
  return (
    <span style={{ fontSize: 9, letterSpacing: 2, padding: "3px 8px", borderRadius: 2, background: bg, color: fg, border: `1px solid ${bd}` }}>
      {status.toUpperCase()}
    </span>
  );
}

function ActionBtn({ label, color }) {
  return (
    <button style={{
      background: "transparent", border: `1px solid ${color}44`,
      color, padding: "4px 10px", borderRadius: 3, cursor: "pointer",
      fontSize: 9, letterSpacing: 1, fontFamily: "inherit",
    }}>{label}</button>
  );
}
