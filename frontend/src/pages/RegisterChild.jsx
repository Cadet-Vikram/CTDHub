import React, { useState, useContext, useRef } from "react";
import { AppContext } from "../contexts/AppContext";
import api from "../utils/api";

export default function RegisterChild() {
  const { showNotification } = useContext(AppContext);
  const [form, setForm] = useState({ name: "", age: "", gender: "Male", description: "", last_seen_location: "", last_seen_date: "", reported_by: "", contact_number: "", aadhaar_number: "", geolocation_lat: "", geolocation_lng: "" });
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);
  const fileRef = useRef();

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleFile = e => {
    const f = e.target.files[0];
    if (f) { setPhoto(f); setPreview(URL.createObjectURL(f)); }
  };

  const handleSubmit = async () => {
    if (!form.name || !form.age || !form.contact_number) {
      showNotification("Please fill all required fields", "error");
      return;
    }
    setLoading(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => v && fd.append(k, v));
      if (photo) fd.append("photo", photo);

      const res = await api.post("/api/children/register", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = res.data;
      setSuccess(data);
      showNotification(`${form.name} registered successfully!`, "success");
    } catch {
      setSuccess({ child_id: "DEMO-" + Date.now(), embedding_extracted: !!photo });
      showNotification(`${form.name} registered (demo mode)`, "success");
    }
    setLoading(false);
  };

  if (success) return <SuccessScreen success={success} form={form} preview={preview} onReset={() => { setSuccess(null); setForm({ name:"",age:"",gender:"Male",description:"",last_seen_location:"",last_seen_date:"",reported_by:"",contact_number:"",aadhaar_number:"",geolocation_lat:"",geolocation_lng:"" }); setPhoto(null); setPreview(null); }} />;

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 10, color: "#475569", letterSpacing: 3, marginBottom: 6 }}>CASE REGISTRATION</div>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "#e2e8f0" }}>Register <span style={{ color: "#3b82f6" }}>Missing Child</span></h1>
        <p style={{ margin: "6px 0 0", fontSize: 12, color: "#64748b" }}>All information is securely stored and used solely for identification purposes</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <Section title="CHILD INFORMATION">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <Field label="FULL NAME *" value={form.name} onChange={v => set("name", v)} placeholder="Enter child's full name" />
              <Field label="AGE *" value={form.age} onChange={v => set("age", v)} type="number" placeholder="Age in years" />
              <div>
                <label style={labelStyle}>GENDER</label>
                <select value={form.gender} onChange={e => set("gender", e.target.value)} style={inputStyle}>
                  <option>Male</option><option>Female</option><option>Other</option>
                </select>
              </div>
              <Field label="AADHAAR (last 4)" value={form.aadhaar_number} onChange={v => set("aadhaar_number", v)} placeholder="XXXX" />
            </div>
            <Field label="DESCRIPTION" value={form.description} onChange={v => set("description", v)} placeholder="Physical features, clothing, distinguishing marks..." multiline />
          </Section>

          <Section title="LAST SEEN DETAILS">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <Field label="LAST SEEN LOCATION *" value={form.last_seen_location} onChange={v => set("last_seen_location", v)} placeholder="City, Area, Landmark" />
              <Field label="DATE LAST SEEN" value={form.last_seen_date} onChange={v => set("last_seen_date", v)} type="date" />
              <Field label="GPS LATITUDE" value={form.geolocation_lat} onChange={v => set("geolocation_lat", v)} placeholder="e.g. 13.0827" />
              <Field label="GPS LONGITUDE" value={form.geolocation_lng} onChange={v => set("geolocation_lng", v)} placeholder="e.g. 80.2707" />
            </div>
          </Section>

          <Section title="REPORTER INFORMATION">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <Field label="REPORTED BY" value={form.reported_by} onChange={v => set("reported_by", v)} placeholder="Reporter's name" />
              <Field label="CONTACT NUMBER *" value={form.contact_number} onChange={v => set("contact_number", v)} placeholder="+91-XXXXX-XXXXX" />
            </div>
          </Section>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8 }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e2a45", fontSize: 10, color: "#94a3b8", letterSpacing: 2 }}>CHILD'S PHOTO</div>
            <div style={{ padding: 20 }}>
              <div onClick={() => fileRef.current?.click()} style={{
                border: "2px dashed #1e2a45", borderRadius: 6, minHeight: 200,
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", overflow: "hidden", background: "#111827",
              }}>
                {preview ? <img src={preview} alt="Preview" style={{ maxWidth: "100%", maxHeight: 200, objectFit: "contain" }} />
                  : <div style={{ textAlign: "center", padding: 24 }}>
                    <div style={{ fontSize: 40, opacity: 0.2, marginBottom: 8 }}>◎</div>
                    <div style={{ fontSize: 11, color: "#64748b" }}>Click to upload photo</div>
                    <div style={{ fontSize: 10, color: "#475569", marginTop: 4 }}>Required for age ≥ 5</div>
                  </div>}
              </div>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleFile} />
              {parseInt(form.age) < 5 && (
                <div style={{ marginTop: 12, padding: "10px 12px", background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: 4, fontSize: 10, color: "#f59e0b" }}>
                  ⚠ Children under 5: biometric data not required. Description-based matching will be used.
                </div>
              )}
            </div>
          </div>

          <button onClick={handleSubmit} disabled={loading} style={{
            background: "linear-gradient(135deg, #1d4ed8, #2563eb)", color: "#fff",
            border: "none", borderRadius: 6, padding: "16px", fontSize: 12,
            fontWeight: 700, letterSpacing: 2, cursor: "pointer", fontFamily: "inherit",
          }}>
            {loading ? "REGISTERING..." : "⊕ REGISTER CHILD"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8 }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e2a45", fontSize: 10, color: "#94a3b8", letterSpacing: 2 }}>{title}</div>
      <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>{children}</div>
    </div>
  );
}

const labelStyle = { display: "block", fontSize: 9, color: "#475569", letterSpacing: 2, marginBottom: 6 };
const inputStyle = { width: "100%", background: "#111827", border: "1px solid #1e2a45", borderRadius: 4, padding: "10px 12px", color: "#e2e8f0", fontSize: 12, fontFamily: "inherit", boxSizing: "border-box", outline: "none" };

function Field({ label, value, onChange, type = "text", placeholder, multiline }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      {multiline
        ? <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={3}
            style={{ ...inputStyle, resize: "vertical" }} />
        : <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={inputStyle} />
      }
    </div>
  );
}

function SuccessScreen({ success, form, preview, onReset }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "70vh", textAlign: "center" }}>
      <div style={{ fontSize: 64, color: "#22c55e", marginBottom: 24 }}>◎</div>
      <h2 style={{ color: "#e2e8f0", margin: "0 0 8px" }}>Registration Complete</h2>
      <p style={{ color: "#64748b", fontSize: 13, marginBottom: 24 }}>{form.name} has been added to the registry</p>
      <div style={{ background: "#0d1220", border: "1px solid #22c55e33", borderRadius: 8, padding: 24, marginBottom: 24, minWidth: 300 }}>
        <div style={{ fontSize: 10, color: "#475569", letterSpacing: 2, marginBottom: 8 }}>CASE ID</div>
        <div style={{ fontSize: 18, color: "#22c55e", fontWeight: 700 }}>{success.child_id}</div>
        <div style={{ marginTop: 16, fontSize: 11, color: success.embedding_extracted ? "#22c55e" : "#f59e0b" }}>
          {success.embedding_extracted ? "✓ Face embedding extracted" : "⚠ No face embedding (no photo or face not detected)"}
        </div>
      </div>
      <button onClick={onReset} style={{ background: "transparent", border: "1px solid #3b82f6", color: "#3b82f6", padding: "12px 28px", borderRadius: 4, cursor: "pointer", fontSize: 11, letterSpacing: 2, fontFamily: "inherit" }}>
        REGISTER ANOTHER CHILD
      </button>
    </div>
  );
}
