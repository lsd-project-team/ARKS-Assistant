import sprite from '../assets/file-icons/pierre.svg';
import theme from '../assets/file-icons/theme.json';
// SVG symbol 引用必须使用独立文件，不能被构建器内联成 data URL。
import dotnet from '../assets/file-icons/dotnet.svg?no-inline';

const fileNames = new Map(Object.entries(theme.fileNames));
const extensions = new Map(Object.entries(theme.extensions));
const colors = new Map(Object.entries(theme.colors));
const supplemental = {
  cs: 'csharp',
  cshtml: 'csharp',
  csproj: 'csproject',
  sln: 'solution',
  slnx: 'solution',
  resx: 'xml',
  config: 'xml',
  props: 'xml',
  targets: 'xml',
  xml: 'xml',
  ps1: 'powershell',
  psm1: 'powershell',
};
const supplementalTokens = new Set(Object.values(supplemental));
Object.entries(supplemental).forEach(([extension, token]) => extensions.set(extension, token));
Object.entries({
  csharp: '#31934d',
  csproject: '#6b66c2',
  solution: '#9465bd',
  xml: '#b47731',
  powershell: '#397dc5',
}).forEach(([token, color]) => colors.set(token, color));
const labels: Record<string, string> = {
  default: '文件',
  text: '文本文件',
  json: 'JSON 文件',
  html: 'HTML 文档',
  markdown: 'Markdown 文档',
  javascript: 'JavaScript 源码',
  typescript: 'TypeScript 源码',
  react: 'React 源码',
  python: 'Python 源码',
  c: 'C 源码',
  cpp: 'C++ 源码',
  git: 'Git 配置',
  vite: 'Vite 配置',
  prettier: 'Prettier 配置',
  css: '样式文件',
  bash: 'Shell 脚本',
  image: '图片文件',
  table: '表格文件',
  database: '数据库 / SQL',
  zip: '压缩文件',
  font: '字体文件',
  yml: 'YAML 配置',
  csharp: 'C# 源码',
  csproject: 'C# 项目',
  solution: '.NET 解决方案',
  xml: 'XML 文档 / 资源配置',
  powershell: 'PowerShell 脚本',
};

function iconForFile(path: string): string {
  const name = path.split(/[\\/]/).at(-1)?.toLowerCase() || '';
  const namedIcon = fileNames.get(name);
  if (namedIcon) return namedIcon;
  // 与 Codex 使用相同的规则：完整文件名优先，再从长到短匹配复合扩展名。
  // Map 避免 constructor、__proto__ 等普通文件名误命中对象原型。
  const parts = name.split('.');
  for (let index = 1; index < parts.length; index++) {
    const icon = extensions.get(parts.slice(index).join('.'));
    if (icon) return icon;
  }
  return 'default';
}

export function FileIcon({ name }: { name: string }) {
  const token = iconForFile(name);
  return (
    <span
      className="file-type-icon"
      style={{ color: colors.get(token) || theme.colors.default }}
      title={labels[token] || `${token} 文件`}
      aria-hidden="true"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" focusable="false">
        <use
          href={`${supplementalTokens.has(token) ? dotnet : sprite}#file-tree-builtin-${token}`}
        />
      </svg>
    </span>
  );
}
