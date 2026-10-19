type MarkdownNode = {
  type: string;
  value?: string;
  url?: string;
  children?: MarkdownNode[];
};

function isRecordLink(node: MarkdownNode) {
  return node.type === 'link' && /^debug-issue:[\w-]+\/[1-9]\d*$/.test(node.url || '');
}

function containsRecordLink(node: MarkdownNode): boolean {
  return isRecordLink(node) || Boolean(node.children?.some(containsRecordLink));
}

function plainText(node: MarkdownNode): string {
  return node.value || node.children?.map(plainText).join('') || '';
}

function isImageDisplayNotice(node: MarkdownNode) {
  if (node.type !== 'paragraph' || node.children?.some((child) => child.type !== 'text'))
    return false;
  const text = plainText(node).trim();
  return (
    /^(?:本次试验的)?原图如下[：:]$/.test(text) ||
    /^[（(]?\s*\d+\s*张原图随上述引用直接展示\s*[）)]?[。.]?$/.test(text)
  );
}

function standaloneRecordLinks(node: MarkdownNode) {
  if (node.type !== 'paragraph' || !node.children?.some(isRecordLink)) return;
  if (node.children.some((child) => child.type !== 'text' && !isRecordLink(child))) return;
  const label = node.children
    .filter((child) => child.type === 'text')
    .map(plainText)
    .join('');
  if (!/^(?:来源|记录文字与全部原图|记录正文与全部原图|原文与原图|原图)?[：:\s。；;]*$/.test(label))
    return;
  return node.children.filter(isRecordLink);
}

function endingParagraph(node?: MarkdownNode): MarkdownNode | undefined {
  if (node?.type === 'paragraph') return node;
  if (node?.type === 'list') return endingParagraph(node.children?.at(-1)?.children?.at(-1));
}

// 只整理助手回复的展示语句，不改原记录、引用版本或代码/引文中的原始内容。
export function remarkRecordAnswer() {
  return (tree: MarkdownNode) => {
    if (!tree.children || !containsRecordLink(tree)) return;
    const blocks: MarkdownNode[] = [];
    for (const block of tree.children) {
      if (isImageDisplayNotice(block)) continue;
      const links = standaloneRecordLinks(block);
      const ending = endingParagraph(blocks.at(-1));
      if (links && ending?.children) {
        for (const link of links) ending.children.push({ type: 'text', value: ' ' }, link);
      } else blocks.push(block);
    }
    tree.children = blocks;
  };
}
