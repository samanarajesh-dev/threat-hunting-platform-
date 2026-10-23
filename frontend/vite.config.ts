import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the dashboard talks to the FastAPI backend through this proxy,
// so the browser sees one origin and CORS is never an issue.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});
