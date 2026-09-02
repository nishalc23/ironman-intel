import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // GitHub Pages serves the site from /<repo>/, so the demo build needs its
  // asset URLs prefixed. Local dev and any root-domain host leave this unset.
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    allowedHosts: ["localhost", "nishals-macbook-pro.tail396e25.ts.net"],
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
