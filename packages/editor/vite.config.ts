import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  // Relative asset paths so the built app works when served from an
  // arbitrary path prefix, e.g. Home Assistant's per-install ingress URL
  // (/api/hassio_ingress/<token>/) -- not just from the domain root.
  base: "./",
  plugins: [svelte()],
  resolve: process.env.VITEST ? { conditions: ["browser"] } : undefined,
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["test/setup.ts"],
  },
});
