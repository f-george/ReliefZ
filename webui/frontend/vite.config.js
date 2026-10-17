import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // `npm run dev` serves the UI on :5173 and forwards API calls to the Flask server
  server: { proxy: { "/api": "http://127.0.0.1:8050" } },
  build: { outDir: "dist", emptyOutDir: true },
});
