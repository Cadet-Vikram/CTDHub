import React, { useState, useContext, useRef } from "react";
import { AppContext } from "../contexts/AppContext";

export default function SearchFace() {
  const { showNotification } = useContext(AppContext);
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef();

  const handleFile = (file) => {
    if (!file || !file.type.startsWith("image/")) return;
    setImage(file);
    setPreview(URL.createObjectURL(file));
    setResults(null);
  };

  const handleSearch = async () => {
    if (!image) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("photo", image);
      formData.append("searched_by", "dashboard_user");

      const res = await fetch(`${(import.meta.env.VITE_API_URL || "")}/api/search/face`, { method: "POST", body: formData });
      const data = await res.json();
      setResults(data);
      if (data.matches?.length > 0) {
        showNotification(`Found ${data.matches.length} potential match(es)!`, "success");
      } else {
        showNotification("No matches found in database", "info");
      }
    } catch {
      // Demo mode: simulate results
      const mockResults = {
        matches: image ? [{
          child_id: "mock-1",
          name: "Ravi Kumar",
          age: 8,
          gender: "Male",
          similarity: 0.923,
          confidence_percent: 92.3,
          last_seen_location: "Chennai Central Station",
          contact_number: "+91-98765-43210",
        }] : [],
        face_count: 1,
        message: "Demo mode: showing simulated match",
      };
      setResults(mockResults);
      showNotification("Demo mode: simulated result shown", "info");
    }
    setLoading(false);
  };

  return (
    <div>
      <PageHeader />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 24 }}>
        <UploadPanel
          preview={preview}
          dragOver={dragOver}
          setDragOver={setDragOver}
          handleFile={handleFile}
          fileRef={fileRef}
          onSearch={handleSearch}
          loading={loading}
          image={image}
        />
        <ResultsPanel results={results} loading={loading} />
      </div>
      {results && <SearchInfo results={results} />}
    </div>
  );
}

function PageHeader() {
  return (
    <div>
      <div style={{ fontSize: 10, color: "#475569", letterSpacing: 3, marginBottom: 6 }}>AI-POWERED</div>
      <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "#e2e8f0" }}>
        Facial <span style={{ color: "#22c55e" }}>Recognition</span> Search
      </h1>
      <p style={{ margin: "6px 0 0", fontSize: 12, color: "#64748b" }}>
        Upload a photo to find matches in the missing children registry using ArcFace + cosine similarity
      </p>
    </div>
  );
}

function UploadPanel({ preview, dragOver, setDragOver, handleFile, fileRef, onSearch, loading, image }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
        style={{
          border: `2px dashed ${dragOver ? "#22c55e" : "#1e2a45"}`,
          borderRadius: 8, padding: 0, cursor: "pointer",
          background: dragOver ? "rgba(34,197,94,0.05)" : "#0d1220",
          minHeight: 280, display: "flex", alignItems: "center", justifyContent: "center",
          overflow: "hidden", transition: "all 0.2s",
        }}>
        {preview ? (
          <img src={preview} alt="Query" style={{ maxWidth: "100%", maxHeight: 320, objectFit: "contain" }} />
        ) : (
          <div style={{ textAlign: "center", padding: 40 }}>
            <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }}>◎</div>
            <div style={{ fontSize: 13, color: "#64748b", marginBottom: 8 }}>Drop photo here or click to upload</div>
            <div style={{ fontSize: 10, color: "#475569", letterSpacing: 2 }}>JPG, PNG, WEBP SUPPORTED</div>
          </div>
        )}
        <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
          onChange={e => handleFile(e.target.files[0])} />
      </div>

      {image && (
        <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 6, padding: "10px 16px", fontSize: 11, color: "#64748b" }}>
          ◈ {image.name} — {(image.size / 1024).toFixed(0)} KB
        </div>
      )}

      <button onClick={onSearch} disabled={!image || loading} style={{
        background: loading ? "#1e2a45" : "linear-gradient(135deg, #1d4ed8, #2563eb)",
        color: loading ? "#475569" : "#fff", border: "none", borderRadius: 6,
        padding: "14px", fontSize: 12, fontWeight: 700, letterSpacing: 2,
        cursor: image && !loading ? "pointer" : "not-allowed", transition: "all 0.2s",
        fontFamily: "inherit",
      }}>
        {loading ? "◎ SEARCHING..." : "◎ SEARCH DATABASE"}
      </button>

      <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 6, padding: 16 }}>
        <div style={{ fontSize: 10, color: "#475569", letterSpacing: 2, marginBottom: 12 }}>HOW IT WORKS</div>
        {[
          ["01", "DETECT", "MTCNN locates faces in uploaded image"],
          ["02", "EMBED", "ArcFace extracts 512-dim face embedding"],
          ["03", "MATCH", "Cosine similarity against all registered faces"],
          ["04", "RANK", "Results ranked by confidence score"],
        ].map(([n, t, d]) => (
          <div key={n} style={{ display: "flex", gap: 12, marginBottom: 10 }}>
            <span style={{ fontSize: 9, color: "#3b82f6", minWidth: 18 }}>{n}</span>
            <div>
              <div style={{ fontSize: 10, color: "#94a3b8", letterSpacing: 2 }}>{t}</div>
              <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>{d}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultsPanel({ results, loading }) {
  if (loading) return (
    <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 400 }}>
      <div style={{ textAlign: "center", color: "#64748b" }}>
        <div style={{ fontSize: 32, marginBottom: 16, animation: "spin 2s linear infinite" }}>◎</div>
        <div style={{ fontSize: 12, letterSpacing: 2 }}>ANALYZING...</div>
      </div>
    </div>
  );

  if (!results) return (
    <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 400 }}>
      <div style={{ textAlign: "center", color: "#475569", padding: 40 }}>
        <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.2 }}>◈</div>
        <div style={{ fontSize: 11, letterSpacing: 2 }}>RESULTS WILL APPEAR HERE</div>
      </div>
    </div>
  );

  if (!results.matches?.length) return (
    <div style={{ background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 400 }}>
      <div style={{ textAlign: "center", color: "#475569", padding: 40 }}>
        <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.3, color: "#ef4444" }}>○</div>
        <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 8 }}>No matches found</div>
        <div style={{ fontSize: 11, color: "#475569" }}>Below similarity threshold (60%)</div>
      </div>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ fontSize: 11, color: "#22c55e", letterSpacing: 2 }}>
        ◉ {results.matches.length} MATCH(ES) FOUND
      </div>
      {results.matches.map((m, i) => (
        <MatchCard key={m.child_id} match={m} rank={i + 1} />
      ))}
    </div>
  );
}

function MatchCard({ match, rank }) {
  const conf = match.confidence_percent;
  const color = conf >= 90 ? "#22c55e" : conf >= 75 ? "#f59e0b" : "#ef4444";

  return (
    <div style={{ background: "#0d1220", border: `1px solid ${color}33`, borderRadius: 8, padding: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 9, color: "#475569", letterSpacing: 2, marginBottom: 4 }}>MATCH #{rank}</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#e2e8f0" }}>{match.name}</div>
          <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>Age {match.age} · {match.gender}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 28, fontWeight: 800, color }}>{conf.toFixed(1)}%</div>
          <div style={{ fontSize: 9, color: "#475569", letterSpacing: 2 }}>CONFIDENCE</div>
        </div>
      </div>

      <div style={{ background: "#111827", borderRadius: 4, height: 4, marginBottom: 16, overflow: "hidden" }}>
        <div style={{ width: `${conf}%`, height: "100%", background: `linear-gradient(90deg, ${color}88, ${color})`, transition: "width 0.8s ease" }} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <InfoItem label="LAST SEEN" value={match.last_seen_location} />
        <InfoItem label="CONTACT" value={match.contact_number} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        <button style={{
          flex: 1, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
          color: "#ef4444", padding: "10px", borderRadius: 4, cursor: "pointer",
          fontSize: 10, letterSpacing: 2, fontFamily: "inherit",
        }}>⚡ SEND SOS ALERT</button>
        <button style={{
          flex: 1, background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.3)",
          color: "#3b82f6", padding: "10px", borderRadius: 4, cursor: "pointer",
          fontSize: 10, letterSpacing: 2, fontFamily: "inherit",
        }}>◈ VIEW PROFILE</button>
      </div>
    </div>
  );
}

function InfoItem({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 9, color: "#475569", letterSpacing: 2, marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 11, color: "#94a3b8" }}>{value || "N/A"}</div>
    </div>
  );
}

function SearchInfo({ results }) {
  return (
    <div style={{ marginTop: 24, background: "#0d1220", border: "1px solid #1e2a45", borderRadius: 8, padding: "16px 24px" }}>
      <div style={{ display: "flex", gap: 32 }}>
        <InfoItem label="FACES DETECTED" value={results.face_count} />
        <InfoItem label="SEARCH ID" value={results.search_id || "DEMO-001"} />
        <InfoItem label="STATUS" value={results.message} />
      </div>
    </div>
  );
}
