// https://vitejs.dev/config/
import type { UserConfig } from "vite";
import { fileURLToPath, URL } from "node:url";
import postcss from "./postcss.config";
import vue from "@vitejs/plugin-vue";
import Components from "unplugin-vue-components/vite";
import { PrimeVueResolver } from "@primevue/auto-import-resolver";

// https://vitejs.dev/config/
export const baseConfig = {
  envDir: "./",
  plugins: [
    vue(),
    Components({
      resolvers: [PrimeVueResolver()],
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  css: {
    postcss,
  },
  build: {
    assetsDir: "assets",
  },
} satisfies UserConfig;
