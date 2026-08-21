export const API_BASE_URL = import.meta.env.VITE_API_URL || "";

function resolveUrl(path) {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

async function request(path, { method = "GET", data, headers = {} } = {}) {
  const isFormData = typeof FormData !== "undefined" && data instanceof FormData;
  const authHeader = api.defaults.headers.common.Authorization;
  const sanitizedHeaders = { ...headers };
  if (isFormData) {
    delete sanitizedHeaders["Content-Type"];
    delete sanitizedHeaders["content-type"];
  }

  const response = await fetch(resolveUrl(path), {
    method,
    headers: {
      ...(authHeader ? { Authorization: authHeader } : {}),
      ...(!isFormData && data !== undefined ? { "Content-Type": "application/json" } : {}),
      ...sanitizedHeaders,
    },
    body:
      data === undefined
        ? undefined
        : isFormData
          ? data
          : typeof data === "string"
            ? data
            : JSON.stringify(data),
  });

  const contentType = response.headers.get("content-type") || "";
  const parsed = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = parsed?.detail || parsed?.message || "Request failed";
    const error = new Error(detail);
    error.response = { status: response.status, data: parsed };
    throw error;
  }

  return { data: parsed };
}

const api = {
  defaults: {
    headers: {
      common: {},
    },
  },
  get: (path, config) => request(path, { ...(config || {}), method: "GET" }),
  post: (path, data, config) => request(path, { ...(config || {}), method: "POST", data }),
  patch: (path, data, config) => request(path, { ...(config || {}), method: "PATCH", data }),
  put: (path, data, config) => request(path, { ...(config || {}), method: "PUT", data }),
  delete: (path, config) => request(path, { ...(config || {}), method: "DELETE" }),
};

export function apiUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL || "http://localhost:8000"}${normalizedPath}`;
}

export default api;
