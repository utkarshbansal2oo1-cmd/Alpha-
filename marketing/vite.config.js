import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Marketing site: a completely separate Vite app from frontend/ (the
// recruiter product). Runs on its own port so both can run side by side
// during development; the Live Demo section calls the same backend API
// the recruiter product uses (see .env.example).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
  },
  build: {
    // Section-level code splitting: each marketing section is dynamically
    // imported (see App.jsx) so the initial bundle is just the shell +
    // hero, and heavier sections (demo, architecture diagram) load as the
    // user scrolls toward them.
    rollupOptions: {
      output: {
        manualChunks: {
          "framer-motion": ["framer-motion"],
        },
      },
    },
  },
});
