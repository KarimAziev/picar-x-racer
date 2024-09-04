import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import Components from "unplugin-vue-components/vite";
import { PrimeVueResolver } from "unplugin-vue-components/resolvers";

// https://vitejs.dev/config/
export default defineConfig({
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
  server: {
    port: 4000,
    cors: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:9000/",
        changeOrigin: true,
        secure: false,
      },
      "/mjpg": {
        target: "http://127.0.0.1:9000/",

        changeOrigin: true,
        secure: false,
      },
      "/mpng": {
        target: "http://127.0.0.1:9000/",

        changeOrigin: true,
        secure: false,
      },
    },
  },
});
