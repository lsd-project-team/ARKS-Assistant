import { useEffect, useState, type CSSProperties } from 'react';
import { getSharedHighlighter, type SupportedLanguages } from '@pierre/diffs';

const languages: Record<string, SupportedLanguages> = {
  js: 'javascript',
  javascript: 'javascript',
  ts: 'typescript',
  typescript: 'typescript',
  jsx: 'jsx',
  tsx: 'tsx',
  cs: 'csharp',
  csharp: 'csharp',
  python: 'python',
  py: 'python',
  json: 'json',
  css: 'css',
  html: 'html',
  xml: 'xml',
  bash: 'bash',
  sh: 'bash',
  sql: 'sql',
  yaml: 'yaml',
  yml: 'yaml',
  cpp: 'cpp',
  c: 'c',
  java: 'java',
  go: 'go',
  rust: 'rust',
  rs: 'rust',
  powershell: 'powershell',
  ps1: 'powershell',
  markdown: 'markdown',
};
type Token = { content: string; light?: string; dark?: string };

export function CodeSyntax({
  content,
  language,
  startLine,
}: {
  content: string;
  language?: string;
  startLine?: number;
}) {
  const [highlighted, setHighlighted] = useState<{
    content: string;
    language?: string;
    lines: Token[][];
  }>();
  useEffect(() => {
    let alive = true;
    const lang = languages[language?.toLowerCase() || ''];
    if (!lang || content.length > 60000) return;
    void getSharedHighlighter({ themes: ['github-light', 'github-dark'], langs: [lang] })
      .then((highlighter) => {
        if (!alive) return;
        const result = highlighter.codeToTokensWithThemes(content, {
          lang,
          themes: { light: 'github-light', dark: 'github-dark' },
        });
        setHighlighted({
          content,
          language,
          lines: result.map((line) =>
            line.map((token) => ({
              content: token.content,
              light: token.variants?.light.color,
              dark: token.variants?.dark.color,
            })),
          ),
        });
      })
      .catch(() => {
        /* 高亮失败保留完整纯文本代码。 */
      });
    return () => {
      alive = false;
    };
  }, [content, language]);
  const lines =
    highlighted?.content === content && highlighted.language === language
      ? highlighted.lines
      : content.split('\n').map((line) => [{ content: line } as Token]);
  return (
    <code className="code-syntax">
      {lines.map((line, i) => (
        <span className="code-line" key={i}>
          {startLine !== undefined && (
            <span className="code-line-number" aria-hidden="true">
              {startLine + i}
            </span>
          )}
          {line.map((token, j) => (
            <span
              key={j}
              style={{ '--code-light': token.light, '--code-dark': token.dark } as CSSProperties}
            >
              {token.content}
            </span>
          ))}
          {i < lines.length - 1 ? '\n' : ''}
        </span>
      ))}
    </code>
  );
}
