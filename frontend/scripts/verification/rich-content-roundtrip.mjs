// 将真实 API/SSE 保存的回答送入同一前端解析器、Renderer 和实际图形引擎。
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { JSDOM } from 'jsdom';
import { init, use } from 'echarts/core';
import { BarChart, LineChart, PieChart, TreeChart } from 'echarts/charts';
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import { parseContent } from '../../src/features/chat/rich/parseContent.ts';
import { chartOptions, mindmapOptions } from '../../src/features/chat/rich/chartOptions.ts';

const input = process.argv[2]
  ? await readFile(process.argv[2], 'utf8')
  : await new Promise((resolve, reject) => {
      let value = '';
      process.stdin.setEncoding('utf8');
      process.stdin.on('data', (part) => {
        value += part;
      });
      process.stdin.on('end', () => resolve(value));
      process.stdin.on('error', reject);
    });
const { reports } = JSON.parse(input);
const compiled = await build({
  entryPoints: [
    fileURLToPath(
      new URL('../../src/features/chat/components/AnswerMarkdown.tsx', import.meta.url),
    ),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  jsx: 'automatic',
  external: [
    'react',
    'react/*',
    'react-dom',
    'react-dom/*',
    '@tanstack/react-query',
    'lucide-react',
    '@radix-ui/*',
    '@pierre/diffs',
    'clsx',
    'tailwind-merge',
    'zustand',
  ],
  loader: { '.css': 'empty' },
  plugins: [
    {
      name: 'offline-external-boundaries',
      setup(builder) {
        builder.onResolve(
          {
            filter:
              /(state\/store|api\/client|hooks\/useSourceCitation|materials\/OriginalMaterialViewer|components\/(HandoverMaterialViewer|SelectionPreview))$/,
          },
          ({ path }) => ({ path, namespace: 'boundary' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          loader: 'js',
          contents: path.endsWith('store')
            ? 'export const useWorkspace = s => s({projectId:"verification"}); useWorkspace.getState = () => ({projectId:"verification"});'
            : path.endsWith('api/client')
              ? 'export class ApiError extends Error {}; export const api = () => {throw Error("离线渲染禁止网络");};'
              : path.endsWith('useSourceCitation')
                ? 'export const useSourceCitation = () => () => false; export const readCitationSource = () => {throw Error("离线渲染禁止网络");};'
                : 'export const OriginalMaterialViewer = () => null; export const HandoverMaterialViewer = () => null; export const SelectionPreview = () => null;',
        }));
      },
    },
  ],
});
const require = createRequire(import.meta.url);
const module = { exports: {} };
new Function('require', 'module', 'exports', compiled.outputFiles[0].text)(
  require,
  module,
  module.exports,
);
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');
use([
  BarChart,
  LineChart,
  PieChart,
  TreeChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  SVGRenderer,
]);
const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.SVGElement = dom.window.SVGElement;
globalThis.CSSStyleSheet = dom.window.CSSStyleSheet;
// jsdom 没有文字排版引擎；SVG 图形引擎仍实际运行，仅替代文字尺寸测量。
dom.window.HTMLCanvasElement.prototype.getContext = () => ({
  measureText: (text) => ({ width: String(text).length * 8 }),
});
dom.window.SVGElement.prototype.getBBox = function () {
  return { x: 0, y: 0, width: (this.textContent?.length || 1) * 8, height: 20 };
};
dom.window.SVGElement.prototype.getComputedTextLength = function () {
  return (this.textContent?.length || 1) * 8;
};
const { renderMermaid } = await import('../../src/features/chat/rich/mermaidRender.ts');
const flatten = (blocks) =>
  blocks.flatMap((block) =>
    block.type === 'collapsible' ? [block, ...flatten(block.blocks)] : [block],
  );
const summary = [];
try {
  for (const report of reports) {
    const segments = parseContent(report.answer);
    assert.ok(segments.every((segment) => !['fallback', 'pending'].includes(segment.type)));
    const blocks = flatten(
      segments
        .filter((segment) => segment.type === 'rich')
        .flatMap((segment) => segment.document.blocks),
    );
    assert.ok(blocks.every((block) => block.type !== 'unsupported'));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(
      ['source-evidence', 'verification', report.run_id],
      report.context || { source_evidence: [] },
    );
    let html;
    try {
      html = renderToStaticMarkup(
        createElement(
          QueryClientProvider,
          { client },
          createElement(module.exports.AnswerMarkdown, {
            content: report.answer,
            runId: report.run_id,
          }),
        ),
      );
    } finally {
      client.clear();
    }
    assert.match(html, /class="rich-content"/);
    assert.doesNotMatch(html, /未知内容块类型|此内容块暂时无法显示|<script>/);
    let graphics = 0;
    for (const block of blocks) {
      if (block.type === 'chart' || block.type === 'mindmap') {
        const chart = init(null, null, { renderer: 'svg', ssr: true, width: 640, height: 420 });
        try {
          chart.setOption(block.type === 'chart' ? chartOptions(block) : mindmapOptions(block));
          assert.match(chart.renderToSVGString(), /<svg/);
        } finally {
          chart.dispose();
        }
        graphics++;
      }
      if (block.type === 'mermaid') {
        assert.match(await renderMermaid(block.content, false), /<svg/);
        graphics++;
      }
    }
    summary.push({
      run_id: report.run_id,
      types: blocks.map((block) => block.type),
      graphics,
      rendered: true,
    });
  }
} finally {
  dom.window.close();
}
process.stdout.write(JSON.stringify({ reports: summary }) + '\n');
