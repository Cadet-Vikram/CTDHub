// src/pages/SOSPage.jsx
import { useState, useEffect } from "react";
import { AlertTriangle, MapPin, Phone, Send, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";
import api from "../utils/api";

export default function SOSPage() {
  const [form, setForm] = useState({
    child_id: "", child_name: "", reporter_phone: "",
    location_description: "", lat: "", lng: "", additional_info: "",
  });
  const [loading, setLoading] = useState(false);
  const [triggered, setTriggered] = useState(false);
  const [children, setChildren] = useState([]);

  useEffect(() => {
    api.get("/children/list?status=missing&limit=100")
      .then(r => setChildren(r.data.children || []))
      .catch(() => {});

    // Get current location
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setForm(f => ({
          ...f,
          lat: pos.coords.latitude.toFixed(6),
          lng: pos.coords.longitude.toFixed(6),
        }));
      });
    }
  }, []);

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSelectChild = (e) => {
    const child = children.find(c => c.id === e.target.value);
    if (child) setForm(f => ({ ...f, child_id: child.id, child_name: child.name }));
  };

  const handleTrigger = async () => {
    if (!form.child_name || !form.reporter_phone || !form.location_description) {
      toast.error("Child name, your phone and location are required");
      return;
    }
    if (!window.confirm("⚠️ This will send EMERGENCY ALERTS to police and authorities. Confirm?")) return;

    setLoading(true);
    try {
      await api.post("/sos/trigger", {
        child_id: form.child_id || "unknown",
        child_name: form.child_name,
        reporter_phone: form.reporter_phone,
        location_description: form.location_description,
        lat: parseFloat(form.lat) || 0,
        lng: parseFloat(form.lng) || 0,
        additional_info: form.additional_info,
      });
      setTriggered(true);
      toast.success("🚨 SOS Alert sent! Authorities have been notified.", { duration: 8000 });
    } catch (err) {
      toast.error("SOS failed. Call police directly: 100");
    } finally {
      setLoading(false);
    }
  };

  if (triggered) {
    return (
      <div className="fade-in" style={{ maxWidth: 600, margin: "4rem auto", textAlign: "center" }}>
        <div style={{ width: 80, height: 80, background: "rgba(16,185,129,0.15)", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1.5rem" }}>
          <CheckCircle size={40} style={{ color: "#10b981" }} />
        </div>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.75rem", marginBottom: "0.75rem" }}>SOS Alert Sent</h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: "2rem" }}>
          Emergency alerts have been dispatched to all nearby police stations and authorities. They will contact you shortly.
        </p>
        <div className="card" style={{ textAlign: "left", marginBottom: "1.5rem" }}>
          <h4 style={{ fontWeight: 600, marginBottom: "0.75rem" }}>Emergency Contacts</h4>
          {[["Police", "100"], ["Childline", "1098"], ["Women Helpline", "1091"], ["Emergency", "112"]].map(([name, num]) => (
            <div key={num} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ color: "var(--text-secondary)" }}>{name}</span>
              <a href={`tel:${num}`} style={{ color: "var(--accent-cyan)", fontWeight: 700, textDecoration: "none" }}>{num}</a>
            </div>
          ))}
        </div>
        <button className="btn btn-ghost" onClick={() => setTriggered(false)}>Send Another Alert</button>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ width: 40, height: 40, background: "rgba(239,68,68,0.15)", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <AlertTriangle size={20} style={{ color: "#ef4444" }} />
          </div>
          <div>
            <h1 className="page-title">SOS Emergency Alert</h1>
            <p className="page-subtitle">Triggers instant notification to all nearby police & authorities</p>
          </div>
        </div>
      </div>

      <div className="alert-banner critical" style={{ marginBottom: "1.5rem" }}>
        <AlertTriangle size={16} />
        <div>Only use this for genuine emergencies. False alerts are punishable under law. For immediate danger, also call <strong>100 (Police)</strong> or <strong>1098 (Childline)</strong>.</div>
      </div>

      <div style={{ maxWidth: 640 }}>
        <div className="card">
          <h3 style={{ fontFamily: "var(--font-display)", fontWeight: 600, marginBottom: "1.25rem" }}>Emergency Report</h3>

          <div className="form-group">
            <label className="form-label">Select Registered Child (if known)</label>
            <select className="form-select" onChange={handleSelectChild}>
              <option value="">-- Not in system / Unknown --</option>
              {children.map(c => <option key={c.id} value={c.id}>{c.name} (Age {c.age})</option>)}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Child's Name *</label>
            <input className="form-input" placeholder="Child's full name" value={form.child_name} onChange={set("child_name")} />
          </div>

          <div className="form-group">
            <label className="form-label"><Phone size={12} style={{ display: "inline" }} /> Your Phone Number *</label>
            <input className="form-input" type="tel" placeholder="+91 9876543210" value={form.reporter_phone} onChange={set("reporter_phone")} />
          </div>

          <div className="form-group">
            <label className="form-label"><MapPin size={12} style={{ display: "inline" }} /> Current Location *</label>
            <input className="form-input" placeholder="Near ABC School, MG Road, Bangalore..." value={form.location_description} onChange={set("location_description")} />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">GPS Latitude</label>
              <input className="form-input" type="number" step="any" value={form.lat} onChange={set("lat")} placeholder="Auto-detected" />
            </div>
            <div className="form-group">
              <label className="form-label">GPS Longitude</label>
              <input className="form-input" type="number" step="any" value={form.lng} onChange={set("lng")} placeholder="Auto-detected" />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Additional Information</label>
            <textarea className="form-textarea" placeholder="Describe the situation, appearance, direction last seen..." value={form.additional_info} onChange={set("additional_info")} />
          </div>

          <button
            className="btn btn-sos"
            style={{ width: "100%", justifyContent: "center" }}
            onClick={handleTrigger}
            disabled={loading}
          >
            {loading ? "Sending Emergency Alert..." : <><Send size={16} /> TRIGGER SOS ALERT</>}
          </button>

          <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {[["Police: 100", "100"], ["Childline: 1098", "1098"], ["Emergency: 112", "112"]].map(([label, num]) => (
              <a key={num} href={`tel:${num}`} className="btn btn-ghost" style={{ flex: 1, justifyContent: "center", fontSize: 12 }}>
                <Phone size={12} /> {label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
