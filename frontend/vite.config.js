import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // In local dev, /api calls go to backend at 8000
      // In production (Vercel), VITE_API_URL points to Cloud Run
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/ws":  { target: "ws://localhost:8000",   ws: true },
    },
  },
  build: { outDir: "dist", sourcemap: false },
});
