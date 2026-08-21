/**
 * Central API config
 * Local dev  : http://localhost:8000  (via vite proxy)
 * Production : VITE_API_URL env variable set in Vercel
 */

export const API_URL = import.meta.env.VITE_API_URL || "";

/**
 * Generic JSON fetch
 */
export async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Multipart upload (for photos)
 */
export async function apiUpload(path, formData) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
