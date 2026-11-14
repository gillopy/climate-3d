import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo la UI corre en :5174 y el proxy manda /api y /media al :8010.
// En produccion `dist/` lo sirve FastAPI: un solo puerto para toda la app.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      "/api": "http://127.0.0.1:8010",
      "/media": "http://127.0.0.1:8010",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
