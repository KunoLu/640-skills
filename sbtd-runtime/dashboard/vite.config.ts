import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build output is committed under static/ (ADR 0002 / D1). CI rebuilds from
// source and requires byte-identical output, so keep the build deterministic:
// no timestamps, no environment-dependent values in emitted files.
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "static",
    emptyOutDir: true,
    sourcemap: false,
    minify: "esbuild",
    target: "es2022",
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
