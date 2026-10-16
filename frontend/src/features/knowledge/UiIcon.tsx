import {
  Archive,
  ArrowUp,
  ArrowUpRight,
  Brain,
  Check,
  CodeXml,
  Download,
  GitCompareArrows,
  House,
  Layers3,
  Link2,
  Menu,
  MessageCircle,
  Moon,
  Network,
  Pin,
  Plus,
  Search,
  Square,
  SquarePen,
  Sun,
  Upload,
  Waypoints,
  Workflow,
  X,
} from 'lucide-react';

// 资料页与工作区使用同一套图标，尺寸由所在控件决定。
const icons = {
  overview: House,
  flow: Workflow,
  modules: Layers3,
  code: CodeXml,
  sun: Sun,
  moon: Moon,
  menu: Menu,
  search: Search,
  link: Link2,
  close: X,
  arrow: ArrowUpRight,
  sequence: GitCompareArrows,
  dataflow: Waypoints,
  architecture: Network,
  chat: MessageCircle,
  memory: Brain,
  plus: Plus,
  edit: SquarePen,
  archive: Archive,
  check: Check,
  send: ArrowUp,
  stop: Square,
  pin: Pin,
  download: Download,
  upload: Upload,
};

export type UiIconName = keyof typeof icons;

export function UiIcon({ name, className = '' }: { name: UiIconName; className?: string }) {
  const Icon = icons[name];
  return <Icon className={`ui-icon ${className}`} strokeWidth={1.65} aria-hidden="true" />;
}
