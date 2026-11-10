import type { SourceFlow } from '../sourceGuides';

const escape = (text: string) =>
  text.replace(
    /[&<>"']/g,
    (char) =>
      ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      })[char]!,
  );

/** 沿用原说明已有的顺序；并列阅读分支不添加执行箭头。 */
export function flowDocument(flow: SourceFlow) {
  const columns = flow.steps.length < 4 ? 1 : 2;
  const rows = Math.ceil(flow.steps.length / columns);
  const width = columns * 288 + 48,
    height = rows * 114 + 62;
  const point = (index: number) => ({
    x: 24 + (index % columns) * 288,
    y: 44 + Math.floor(index / columns) * 114,
  });
  const nodes = flow.steps
    .map((step, index) => {
      const { x, y } = point(index);
      const label = escape(step.title);
      const lines = [...step.title].reduce<string[]>((result, char, i) => {
        const line = Math.floor(i / 16);
        result[line] = (result[line] ?? '') + char;
        return result;
      }, []);
      return `<g data-node-id="${escape(step.id)}" data-node-label="${label}" role="button" tabindex="0" aria-label="${label}">
      <rect x="${x}" y="${y}" width="260" height="78" rx="9" fill="var(--panel)" stroke="var(--line)"/>
      <text x="${x + 16}" y="${y + 23}" font-size="11" fill="var(--muted)">${String(index + 1).padStart(2, '0')}</text>
      <text font-size="14" fill="var(--ink)">${lines.map((line, i) => `<tspan x="${x + 16}" y="${y + 45 + i * 18}">${escape(line)}</tspan>`).join('')}</text></g>`;
    })
    .join('');
  const edges =
    flow.sequential === false
      ? ''
      : flow.steps
          .slice(1)
          .map((step, i) => {
            const a = point(i),
              b = point(i + 1);
            const across = a.y === b.y;
            const d = across
              ? `M${a.x + 260},${a.y + 39}H${b.x}`
              : `M${a.x + 130},${a.y + 78}V${a.y + 96}H${b.x + 130}V${b.y}`;
            return `<g data-edge-from="${escape(flow.steps[i].id)}" data-edge-to="${escape(step.id)}" data-edge-id="edge-${i}"><path d="${d}" fill="none" stroke="var(--muted)" stroke-width="1.2" marker-end="url(#arrow)"/></g>`;
          })
          .join('');
  return `<html><head><style>:root{--bg:#fafafa;--panel:#fff;--ink:#292d2b;--muted:#7a827d;--line:#d4ded8}:root[data-theme="dark"]{--bg:#181818;--panel:#222;--ink:#e8e8e8;--muted:#aaa;--line:#555}</style></head><body>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escape(flow.title)}">
    <defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0L7,3.5L0,7" fill="var(--muted)"/></marker></defs>
    <text x="24" y="23" font-size="12" fill="var(--muted)">${flow.sequential === false ? '并列阅读分支' : '环节顺序 · 各步返回分支见说明'}</text>${edges}${nodes}</svg></body></html>`;
}
