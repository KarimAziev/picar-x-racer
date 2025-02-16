// https://vitejs.dev/config/
import type { UserConfig } from "vite";
import { fileURLToPath, URL } from "node:url";
import tailwindcssPlugin from "@tailwindcss/vite";
import Components from "unplugin-vue-components/vite";
import { PrimeVueResolver } from "@primevue/auto-import-resolver";
import vue from "@vitejs/plugin-vue";

// https://vitejs.dev/config/
export const baseConfig = {
  envDir: "./",
  plugins: [
    vue(),
    tailwindcssPlugin(),
    Components({
      resolvers: [PrimeVueResolver()],
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    assetsDir: "assets",
  },
} satisfies UserConfig;
