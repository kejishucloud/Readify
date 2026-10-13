import { defineConfig } from "vite";
export default defineConfig({
  base: "./",
  server: {
    port: 5173,
    strictPort: true,
    // Run Django on http://127.0.0.1:8000. Proxying retains same-site session + CSRF in dev.
    proxy: {
      "/api": {target: "http://127.0.0.1:8000", changeOrigin: true},
      "/user": {target: "http://127.0.0.1:8000", changeOrigin: true},
    },
  },
});
