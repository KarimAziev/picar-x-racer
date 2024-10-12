import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import Components from "unplugin-vue-components/vite";
import { PrimeVueResolver } from "unplugin-vue-components/resolvers";

const mainAppPort = process.env.VITE_MAIN_APP_PORT || 8000;
const wsAppPort = process.env.VITE_WS_APP_PORT || 8001;

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
    port: 4000, // Vite front-end dev server runs on this port
    cors: true,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${mainAppPort}/`,
        changeOrigin: true,
        secure: false,
      },
      "/ws/video-stream": {
        target: `ws://127.0.0.1:${mainAppPort}/`,
        changeOrigin: true,
        secure: false,
      },
      "/px/api": {
        target: `http://127.0.0.1:${wsAppPort}/`,
        changeOrigin: true,
        secure: false,
      },
      "/px/ws": {
        target: `ws://127.0.0.1:${wsAppPort}/`,
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
