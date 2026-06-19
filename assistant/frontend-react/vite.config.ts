import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

// Electron loads the bundle over file://, where Vite's default `crossorigin`
// attribute on module/style tags causes the assets to fail loading. Strip it.
function stripCrossorigin(): Plugin {
  return {
    name: 'electron-strip-crossorigin',
    transformIndexHtml(html) {
      return html.replace(/\s+crossorigin/g, '');
    },
  };
}

// base './' is required so built asset paths are relative — Electron loads the
// bundle over file://, where absolute '/assets/...' paths would 404.
export default defineConfig({
  plugins: [react(), stripCrossorigin()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1500,
  },
  server: { port: 5273 },
});
