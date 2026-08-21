import React, { useState, useContext } from "react";
import { AppContext } from "../contexts/AppContext";

const MOCK_ALERTS = [
  { id: 1, type: "sos", child_name: "Ravi Kumar", message: "SOS: Child spotted near Chennai Central", status: "sent", created_at: "2024-01-15 09:42" },
  { id: 2, type: "broadcast", child_name: "Priya Sharma", message: "AMBER Alert: Missing child in Mumbai zone", status: "broadcast", created_at: "2024-01-14 14:20" },
  { id: 3, type: "match_found", child_name: "Arjun Patel", message: "Face match found — 94.2% confidence", status: "resolved", created_at: "2024-01-12 11:05" },
];

export default function AlertsPanel() {
  const { showNotification } = useContext(AppContext);
  const [alerts, setAlerts] = useState(MOCK_ALERTS);
  const [sosForm, setSosForm] = useState({ child_id: "", reporter_name: "", reporter_phone: "", message: "" });
  const [sending, setSending] = useState(false);

  const sendSOS = async () => {
    if (!sosForm.reporter_name || !sosForm.reporter_phone) {
      showNotification("Please fill reporter details", "error");
      return;
    }
    setSending(true);
    await new Promise(r => setTimeout(r, 1000));
    const newAlert = {
      id: Date.now(), type: "sos",
      child_name: "Unknown (Demo)", message: sosForm.message || "SOS Alert triggered",
      status: "sent", created_at: new Date().toLocaleString("en-IN"),
    };
    setAlerts(a => [newAlert, ...a]);
    showNotification("SOS Alert sent to authorities!", "success");
    setSosForm({ child_id: "", reporter_name: "", reporter_phone: "", message: "" });
    setSending(false);
  };

  const typeColors = { sos: "#ef4444", broadcast: "#f59e0b", match_found: "#22c55e" };
  const typeIcons = { sos: "⚡", broadcast: "◉", match_found: "◎" };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 10, color: "#475569", letterSpacing: 3, marginBottom: 6 }}>EMERGENCY SYSTEM</div>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "#e2e8f0" }}>Alerts & <span style={{ color: "#ef4444" }}>Emergency</span></h1>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 24 }}>
        <div>
          <div style={{ fontSize: 10, color: "#94a3b8", letterSpacing: 2, marginBottom: 16 }}>ALERT HISTORY</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {alerts.map(a => (
              <div key={a.id} style={{
                background: "#0d1220",
                border: `1px solid ${typeColors[a.type] || "#1e2a45"}22`,
                borderLeft: `3px solid ${typeColors[a.type] || "#1e2a45"}`,
                borderRadius: 8, padding: 20,
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <span style={{ fontSize: 18, color: typeColors[a.type] }}>{typeIcons[a.type] || "◈"}</span>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>{a.child_name}</div>
                      <div style={{ fontSize: 9, color: "#475569", letterSpacing: 2 }}>{a.type.toUpperCase().replace("_", " ")}</div>
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 9, color: "#475569", letterSpacing: 1 }}>{a.created_at}</div>
                    <span style={{ fontSize: 9, color: a.status === "resolved" ? "#22c55e" : "#f59e0b", letterSpacing: 1 }}>
                      {a.status.toUpperCase()}
                    </span>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: "#64748b" }}>{a.message}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ background: "#0d1220", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8 }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(239,68,68,0.2)", display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444", boxShadow: "0 0 8px #ef4444" }} />
              <span style={{ fontSize: 11, color: "#ef4444", letterSpacing: 2, fontWeight: 700 }}>SEND SOS ALERT</span>
            </div>
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
              <SOSField label="REPORTER NAME" value={sosForm.reporter_name} onChange={v => setSosForm(f => ({ ...f, reporter_name: v }))} />
              <SOSField label="PHONE NUMBER" value={sosForm.reporter_phone} onChange={v => setSosForm(f => ({ ...f, reporter_phone: v }))} />
              <SOSField label="LOCATION / MESSAGE" value={sosForm.message} onChange={v => setSosForm(f => ({ ...f, message: v }))} multiline />
              <button onClick={sendSOS} disabled={sending} style={{
                background: sending ? "#1e2a45" : "linear-gradient(135deg, #dc2626, #ef4444)",
                color: "#fff", border: "none", borderRadius: 4, padding: "14px",
                fontSize: 12, fontWeight: 700, letterSpacing: 2, cursor: "pointer", fontFamily: "inherit",
              }}>
                {sending ? "SENDING..." : "⚡ TRIGGER SOS"}
              </button>
            </div>
          </div>

          <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8, padding: 20 }}>
            <div style={{ fontSize: 10, color: "#475569", letterSpacing: 2, marginBottom: 16 }}>ALERT CHANNELS</div>
            {[
              { icon: "◈", label: "SMS to Family", status: "Active", color: "#22c55e" },
              { icon: "◎", label: "Police Station Alert", status: "Active", color: "#22c55e" },
              { icon: "⊕", label: "NGO Network", status: "Active", color: "#22c55e" },
              { icon: "≡", label: "Firebase Push", status: "Setup Required", color: "#f59e0b" },
            ].map(c => (
              <div key={c.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span style={{ color: "#3b82f6" }}>{c.icon}</span>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>{c.label}</span>
                </div>
                <span style={{ fontSize: 9, color: c.color, letterSpacing: 1 }}>{c.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SOSField({ label, value, onChange, multiline }) {
  const style = { width: "100%", background: "#111827", border: "1px solid #1e2a45", borderRadius: 4, padding: "10px 12px", color: "#e2e8f0", fontSize: 12, fontFamily: "inherit", boxSizing: "border-box", outline: "none" };
  return (
    <div>
      <label style={{ display: "block", fontSize: 9, color: "#475569", letterSpacing: 2, marginBottom: 6 }}>{label}</label>
      {multiline ? <textarea value={value} onChange={e => onChange(e.target.value)} rows={3} style={{ ...style, resize: "vertical" }} />
        : <input value={value} onChange={e => onChange(e.target.value)} style={style} />}
    </div>
  );
}
