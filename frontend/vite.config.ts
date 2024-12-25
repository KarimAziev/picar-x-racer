import { defineConfig } from "vite";
import { baseConfig } from "./vite.config.base";

const mainAppPort = process.env.VITE_MAIN_APP_PORT || 8000;
const wsAppPort = process.env.VITE_WS_APP_PORT || 8001;
const serverPort = +(process.env.VITE_DEV_SERVER_PORT || "4000");

// https://vitejs.dev/config/
export default defineConfig({
  ...baseConfig,
  server: {
    port: serverPort, // Vite front-end dev server runs on this port
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
        ws: true,
      },
      "/ws/sync": {
        target: `ws://127.0.0.1:${mainAppPort}/`,
        changeOrigin: true,
        secure: false,
        ws: true,
      },
      "/ws/object-detection": {
        target: `ws://127.0.0.1:${mainAppPort}/`,
        changeOrigin: true,
        secure: false,
        ws: true,
      },
      "/px/api": {
        target: `http://127.0.0.1:${wsAppPort}/`,
        changeOrigin: true,
        secure: false,
      },
      "/px/ws": {
        target: `ws://127.0.0.1:${wsAppPort}/`,
        ws: true,
        changeOrigin: true,
        secure: false,
      },
      "/ws/audio-stream": {
        target: `ws://127.0.0.1:${mainAppPort}/`,
        ws: true,
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
