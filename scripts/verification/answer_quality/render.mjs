// 使用应用的Markdown配置渲染实际结果，测试图片只核对关联位置，不冒充设备原图。
import { readFile, readdir, writeFile, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { resolve, dirname } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const input = resolve(process.argv[2]);
const output = resolve(process.argv[3]);
if (
  !input.startsWith(resolve(root, "output") + "/") &&
  !input.startsWith(resolve(root, "output") + "\\")
)
  throw new Error("仅允许读取output内的测评结果");
if (
  !output.startsWith(resolve(root, "output") + "/") &&
  !output.startsWith(resolve(root, "output") + "\\")
)
  throw new Error("仅允许写入output");
const require = createRequire(resolve(root, "frontend/package.json"));
const { createElement } = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const { default: Markdown } = await import(
  pathToFileURL(require.resolve("react-markdown"))
);
const { default: gfm } = await import(
  pathToFileURL(require.resolve("remark-gfm"))
);
const manifest = JSON.parse(
  await readFile(resolve(input, "manifest.json"), "utf8"),
);
const files = await readdir(resolve(input, "results"));
const results = await Promise.all(
  files
    .filter((name) => name.endsWith(".json"))
    .map(async (name) =>
      JSON.parse(await readFile(resolve(input, "results", name), "utf8")),
    ),
);
const rows = manifest.cases
  .map((item) => results.find((row) => row.id === item.id))
  .filter(Boolean);
const allCss = await readFile(
  resolve(root, "frontend/src/shared/styles/base.css"),
  "utf8",
);
const markdownCss = allCss.slice(
  allCss.indexOf(".markdown {"),
  allCss.indexOf(".source-link {"),
);
const escape = (text) =>
  String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
const navigation = rows
  .map((row) => `<a href="${row.id}.html">${row.id}</a>`)
  .join(" ");
const shell = (
  title,
  body,
) => `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(title)}</title><style>${markdownCss}
:root{--text:#283b37;--text-secondary:#547064;--border:#d7e0d9;--muted:#6a7d71;--surface-subtle:#f2f5f2;--surface-hover:#e5ece6}*{box-sizing:border-box}body{margin:0;background:#f7faf7;font-family:'Segoe UI','Microsoft YaHei UI',sans-serif}main{max-width:860px;padding:25px;margin:auto}nav{font-size:13px;line-height:2.2;margin-bottom:22px}nav a{padding:5px;color:#526959}h1{font-size:20px}header,footer{font-size:12px;color:#677c6d;margin:16px 0}.question{margin:20px 0 24px 80px;padding:15px 20px;background:#e7eee6;border-radius:15px;line-height:1.8;font-size:14px}.answer{background:white;border:1px solid #d7e0d9;border-radius:12px;padding:24px;max-width:690px}.markdown{line-height:1.8}.source-link{font-size:11px;border:1px solid var(--border);padding:1px 4px;border-radius:4px;color:var(--text-secondary)}.images{max-width:690px;margin-top:18px}.test-image{padding:10px;border:1px dashed #becbbf;border-radius:7px;margin:8px 0;color:#6c7e70;font-size:12px}.test-image img{width:20px;height:20px;vertical-align:middle;image-rendering:pixelated}.index{line-height:2}details{font-size:13px;line-height:1.7;margin-top:25px}pre{white-space:pre-wrap}
</style><main><h1>ARKS · 20题实际回复审阅</h1><header>15条经验、5条流程 · ${escape(manifest.model)} · seed ${manifest.seed} · 隔离测评，不是正式对话</header><nav>${navigation}</nav>${body}</main></html>`;
await mkdir(output, { recursive: true });
for (const row of rows) {
  const rendered = renderToStaticMarkup(
    createElement(Markdown, {
      children: row.answer || `本题运行失败：${row.error || "未知原因"}`,
      remarkPlugins: [[gfm, { singleTilde: false }]],
      urlTransform: (url) => url,
      components: {
        a: ({ children }) =>
          createElement("span", { className: "source-link" }, children),
      },
    }),
  );
  const images = (row.cited_records || [])
    .map((key) =>
      Array.from(
        { length: row.seeds[key].image_count },
        (_, index) =>
          `<div class="test-image"><img alt="隔离测试图片" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII="> ${escape(key)} · 原图位置 ${index + 1} / ${row.seeds[key].image_count}（测试资产，不是设备试验照片）</div>`,
      ).join(""),
    )
    .join("");
  await writeFile(
    resolve(output, `${row.id}.html`),
    shell(
      row.id,
      `<div class="question">${escape(row.question)}</div><article class="answer"><header>ARKS 实际回答 · ${row.seconds}s</header><div class="markdown">${rendered}</div></article><section class="images">${images}</section><details><summary>本题先验核对点</summary><ul>${row.oracle.map((point) => `<li>${escape(point)}</li>`).join("")}</ul></details><footer>该页保留实际生成文本，只复用应用渲染规则；未将失败样本改写成示例答案。</footer>`,
    ),
    "utf8",
  );
}
await writeFile(
  resolve(output, "index.html"),
  shell(
    "测评目录",
    `<div class="index">${rows.map((row) => `<div><a href="${row.id}.html">${row.id} · ${escape(row.question)}</a></div>`).join("")}</div>`,
  ),
  "utf8",
);
console.log(`已渲染${rows.length}题，目录：${output}`);
