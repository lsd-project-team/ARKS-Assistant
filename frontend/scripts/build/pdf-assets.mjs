// PDF 原页面在本地绘制，字体和解码资源随应用发布，不请求外部服务。
import { readFile, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = new URL('../../node_modules/pdfjs-dist/', import.meta.url);
const folders = ['cmaps', 'standard_fonts', 'wasm', 'iccs'];

export function pdfAssets() {
  return {
    name: 'arks-pdf-assets',
    async generateBundle() {
      for (const folder of folders) {
        for (const entry of await readdir(new URL(folder + '/', root), { withFileTypes: true })) {
          if (!entry.isFile()) continue;
          this.emitFile({
            type: 'asset',
            fileName: `assets/pdfjs/${folder}/${entry.name}`,
            source: await readFile(new URL(folder + '/' + entry.name, root)),
          });
        }
      }
      this.emitFile({
        type: 'asset',
        fileName: 'assets/pdfjs/LICENSE',
        source: await readFile(new URL('LICENSE', root)),
      });
    },
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const path = request.url?.split('?')[0] || '';
        if (!path.startsWith('/assets/pdfjs/')) return next();
        const [folder, name, ...rest] = path.slice('/assets/pdfjs/'.length).split('/');
        if (!folders.includes(folder) || !/^[\w.-]+$/.test(name || '') || rest.length) {
          response.statusCode = 404;
          response.end();
          return;
        }
        readFile(fileURLToPath(new URL(folder + '/' + name, root)))
          .then((bytes) => {
            response.setHeader(
              'Content-Type',
              name.endsWith('.wasm') ? 'application/wasm' : 'application/octet-stream',
            );
            response.end(bytes);
          })
          .catch(() => {
            response.statusCode = 404;
            response.end();
          });
      });
    },
  };
}
