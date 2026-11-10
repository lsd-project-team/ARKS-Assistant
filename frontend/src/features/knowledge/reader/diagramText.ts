/** 只在节点原有空间允许时增大字号，避免大字挤出边框或盖住副标题。 */
export function clarifyNodeText(svg: SVGSVGElement) {
  const win = svg.ownerDocument.defaultView!;
  for (const node of svg.querySelectorAll<SVGGraphicsElement>('[data-node-id]')) {
    const shape = [...node.children].find((element) =>
      ['rect', 'polygon', 'path'].includes(element.tagName.toLowerCase()),
    ) as SVGGraphicsElement | undefined;
    if (!shape) continue;
    const box = shape.getBBox();
    if (!box.width || !box.height) continue;
    const labels = [...node.querySelectorAll<SVGTextElement>('text.t-primary,text.tree-label')];
    for (const label of labels) {
      const original =
        Number(label.dataset.readerFontSize) || parseFloat(win.getComputedStyle(label).fontSize);
      label.dataset.readerFontSize = String(original);
      const peers = [...node.querySelectorAll<SVGTextElement>('text')].filter(
        (text) => text !== label,
      );
      for (
        let size = Math.max(original, 14);
        size >= original;
        size = Math.max(original, size - 0.5)
      ) {
        label.style.fontSize = `${size}px`;
        const bounds = label.getBBox();
        const inside =
          bounds.x >= box.x + 6 &&
          bounds.x + bounds.width <= box.x + box.width - 6 &&
          bounds.y >= box.y + 4 &&
          bounds.y + bounds.height <= box.y + box.height - 4;
        const overlaps = peers.some((text) => {
          const other = text.getBBox();
          return (
            bounds.x < other.x + other.width &&
            bounds.x + bounds.width > other.x &&
            bounds.y < other.y + other.height + 1 &&
            bounds.y + bounds.height + 1 > other.y
          );
        });
        if ((inside && !overlaps) || size === original) break;
      }
    }
  }
}
