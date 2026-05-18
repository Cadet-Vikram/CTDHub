// src/utils/api.js
import axios from "axios";
import toast from "react-hot-toast";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1",
  timeout: 30000,
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const msg = error.response?.data?.detail || "Request failed";
    if (error.response?.status === 401) {
      toast.error("Session expired. Please log in again.");
    } else if (error.response?.status >= 500) {
      toast.error("Server error. Please try again.");
    }
    return Promise.reject(error);
  }
);

export default api;
