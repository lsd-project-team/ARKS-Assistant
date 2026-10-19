import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { knowledgeAssets } from './scripts/knowledge/resources.mjs';
import { publicAssets } from './scripts/build/public-assets.mjs';

export default defineConfig({
  plugins: [react(), tailwindcss(), knowledgeAssets(), publicAssets()],
  server: { proxy: { '/api': 'http://127.0.0.1:8765' } },
  build: { chunkSizeWarningLimit: 3000, manifest: true },
});
