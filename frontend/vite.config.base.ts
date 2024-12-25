// https://vitejs.dev/config/
import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import Components from "unplugin-vue-components/vite";

import { PrimeVueResolver } from "@primevue/auto-import-resolver";

// https://vitejs.dev/config/
export const baseConfig = {
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
  build: {
    assetsDir: "assets",
  },
};
