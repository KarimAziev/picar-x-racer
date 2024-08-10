// vite.config.js

import { defineConfig } from 'vite';
import path from 'node:path';
import tsconfigPaths from 'vite-tsconfig-paths';

// https://vitejs.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  plugins: [tsconfigPaths()],
  build: {
    target: 'esnext',
  },
});
