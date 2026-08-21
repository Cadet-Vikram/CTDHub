// src/pages/MissingList.jsx
import { useState, useEffect } from "react";
import { Search, User, MapPin, Calendar, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import api from "../utils/api";

export default function MissingList() {
  const [children, setChildren] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("missing");

  useEffect(() => {
    setLoading(true);
    api.get(`/children/list?status=${status}&limit=100`)
      .then(r => setChildren(r.data.children || []))
      .catch(() => setChildren([]))
      .finally(() => setLoading(false));
  }, [status]);

  const filtered = children.filter(c =>
    c.name?.toLowerCase().includes(query.toLowerCase()) ||
    c.last_seen_location?.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Missing Children Database</h1>
        <p className="page-subtitle">{children.length} records loaded</p>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ position: "relative", flex: 1 }}>
          <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
          <input className="form-input" style={{ paddingLeft: 32 }} placeholder="Search by name or location..." value={query} onChange={e => setQuery(e.target.value)} />
        </div>
        <select className="form-select" style={{ width: 140 }} value={status} onChange={e => setStatus(e.target.value)}>
          <option value="missing">Missing</option>
          <option value="found">Found</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {loading ? (
        <div className="grid-3">{Array(6).fill(0).map((_, i) => <div key={i} className="skeleton" style={{ height: 160 }} />)}</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: "center", padding: "4rem", color: "var(--text-muted)" }}>
          <User size={48} style={{ opacity: 0.3, marginBottom: "1rem" }} />
          <div>No children found</div>
        </div>
      ) : (
        <div className="grid-3">
          {filtered.map(c => (
            <div key={c.id} className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
                <div style={{
                  width: 52, height: 52, borderRadius: 10, flexShrink: 0,
                  background: c.face_image_path ? `url(${(import.meta.env.VITE_API_URL || "")}/${c.face_image_path}) center/cover` : "var(--bg-hover)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {!c.face_image_path && <User size={22} style={{ color: "var(--text-muted)" }} />}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontFamily: "var(--font-display)" }}>{c.name}</div>
                  <div style={{ color: "var(--text-muted)", fontSize: 12 }}>Age {c.age} · {c.gender || "—"}</div>
                  <span className={`badge badge-${c.status}`} style={{ marginTop: 4 }}>{c.status}</span>
                </div>
              </div>
              {c.last_seen_location && (
                <div style={{ display: "flex", gap: 6, alignItems: "flex-start", color: "var(--text-secondary)", fontSize: 12 }}>
                  <MapPin size={12} style={{ marginTop: 1, flexShrink: 0 }} />
                  <span>{c.last_seen_location}</span>
                </div>
              )}
              {c.last_seen_date && (
                <div style={{ display: "flex", gap: 6, alignItems: "center", color: "var(--text-muted)", fontSize: 12 }}>
                  <Calendar size={12} />
                  <span>{new Date(c.last_seen_date).toLocaleDateString()}</span>
                </div>
              )}
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.25rem" }}>
                {c.has_biometrics && <span className="badge badge-medium">Biometrics</span>}
                {c.aadhaar_verified && <span className="badge" style={{ background: "rgba(139,92,246,0.15)", color: "#a78bfa" }}>Aadhaar ✓</span>}
                {c.too_young_for_biometrics && <span className="badge badge-high">Under 5</span>}
              </div>
              <Link to={`/child/${c.id}`} className="btn btn-ghost" style={{ justifyContent: "center", fontSize: 12 }}>
                <ExternalLink size={12} /> View Details
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
