import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy /api calls to the FastAPI backend so the frontend has no CORS worries.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
