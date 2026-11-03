import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Maximize, Minus, Plus, PanelRight, Scan, Search, Download } from 'lucide-react';
import './reader.css';

export interface DiagramNode {
  id: string;
  label: string;
  description?: string;
  context?: string;
  branches: { id: string; label: string; target: string }[];
}
export interface CanvasCommands {
  fit: () => void;
  zoom: (factor: number) => void;
  export: () => void;
}
interface CanvasBridge {
  selected?: string;
  select: (id: string) => void;
  register: (nodes: DiagramNode[], commands?: CanvasCommands) => void;
  setScale: (scale: number) => void;
}
const CanvasContext = createContext<CanvasBridge | null>(null);
export const useReaderCanvas = () => useContext(CanvasContext);

export function ReaderFrame({
  title,
  children,
  detail,
  onDocument,
  onSelect,
  selectedId,
}: {
  title: string;
  children: ReactNode;
  detail?: (node: DiagramNode | undefined, select: (id: string) => void) => ReactNode;
  onDocument?: () => void;
  onSelect?: (id: string) => void;
  selectedId?: string;
}) {
  const frame = useRef<HTMLElement>(null);
  const commands = useRef<CanvasCommands | undefined>(undefined);
  const [nodes, setNodes] = useState<DiagramNode[]>([]);
  const [selected, setSelected] = useState<string>();
  const [query, setQuery] = useState('');
  const [scale, setScale] = useState(1);
  const [ready, setReady] = useState(false);
  const [showDetail, setShowDetail] = useState(true);
  const [message, setMessage] = useState('');
  const [isFullscreen, setIsFullscreen] = useState(false);
  useEffect(() => {
    const update = () => setIsFullscreen(document.fullscreenElement === frame.current);
    document.addEventListener('fullscreenchange', update);
    return () => document.removeEventListener('fullscreenchange', update);
  }, []);
  const detailId = useId();
  const select = useCallback(
    (id: string) => {
      setSelected(id);
      onSelect?.(id);
    },
    [onSelect],
  );
  const register = useCallback((items: DiagramNode[], actions?: CanvasCommands) => {
    setNodes(items);
    commands.current = actions;
    setReady(Boolean(actions));
    setSelected((current) => (items.some((item) => item.id === current) ? current : items[0]?.id));
  }, []);
  const activeId = selectedId ?? selected;
  const node = nodes.find((item) => item.id === activeId);
  const matches = query.trim()
    ? nodes.filter((item) =>
        `${item.label} ${item.description ?? ''} ${item.context ?? ''}`
          .toLowerCase()
          .includes(query.trim().toLowerCase()),
      )
    : [];
  const fullscreen = async () => {
    try {
      if (document.fullscreenElement === frame.current) await document.exitFullscreen();
      else await frame.current?.requestFullscreen();
    } catch {
      setMessage('浏览器未允许全屏，可收起说明区扩大画布。');
    }
  };
  return (
    <section ref={frame} className="reader-frame" aria-label={`${title} 图谱阅读器`}>
      <div className="reader-toolbar" role="toolbar" aria-label="图谱工具">
        <label className="reader-search">
          <Search size={15} aria-hidden="true" />
          <input
            aria-label="查找图中节点"
            placeholder="查找节点…"
            disabled={nodes.length === 0}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <div className="reader-tools">
          <button type="button" disabled={!ready} onClick={() => commands.current?.fit()}>
            <Scan size={15} />
            适应画布
          </button>
          <div className="reader-zoom" role="group" aria-label="缩放">
            <button
              type="button"
              aria-label="缩小图谱"
              disabled={!ready}
              onClick={() => commands.current?.zoom(0.8)}
            >
              <Minus size={15} />
            </button>
            <button
              type="button"
              aria-label="以原始大小阅读"
              disabled={!ready}
              onClick={() => commands.current?.zoom(1 / scale)}
            >
              <span aria-label="当前缩放">{Math.round(scale * 100)}%</span>
            </button>
            <button
              type="button"
              aria-label="放大图谱"
              disabled={!ready}
              onClick={() => commands.current?.zoom(1.25)}
            >
              <Plus size={15} />
            </button>
          </div>
          <button
            type="button"
            aria-label={isFullscreen ? '退出全屏' : '全屏阅读'}
            onClick={() => void fullscreen()}
          >
            <Maximize size={15} />
          </button>
          <button
            type="button"
            aria-pressed={showDetail}
            aria-controls={detailId}
            onClick={() => setShowDetail(!showDetail)}
          >
            <PanelRight size={15} />
            说明
          </button>
          <button type="button" disabled={!ready} onClick={() => commands.current?.export()}>
            <Download size={15} />
            导出 SVG
          </button>
        </div>
      </div>
      {query.trim() && (
        <div className="reader-search-results" role="region" aria-label="节点查找结果">
          <span role="status">
            {matches.length ? `找到 ${matches.length} 个节点` : '没有匹配的节点'}
          </span>
          {matches.map((item) => (
            <button
              type="button"
              key={item.id}
              aria-pressed={activeId === item.id}
              onClick={() => {
                select(item.id);
                setQuery('');
                setShowDetail(true);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
      <CanvasContext.Provider value={{ selected: activeId, select, register, setScale }}>
        <div className="reader-body" data-details={showDetail}>
          <div className="reader-canvas">{children}</div>
          <aside
            id={detailId}
            className="reader-detail"
            hidden={!showDetail}
            aria-label="节点说明"
            aria-live="polite"
          >
            {detail ? detail(node, select) : <DiagramNodeDetail node={node} select={select} />}
            {onDocument && (
              <button
                type="button"
                className="text-button reader-document-link"
                onClick={onDocument}
              >
                阅读详细说明 →
              </button>
            )}
          </aside>
        </div>
      </CanvasContext.Provider>
      <div className="reader-footnote">
        <span>
          {ready
            ? '拖动画布移动 · Ctrl + 滚轮缩放 · 点击节点查看说明'
            : '按所选环节阅读图表与条件说明'}
        </span>
        {nodes.length > 0 && <span>{nodes.length} 个节点</span>}
        {message && <span role="status">{message}</span>}
      </div>
    </section>
  );
}

export function DiagramNodeDetail({
  node,
  select,
}: {
  node?: DiagramNode;
  select: (id: string) => void;
}) {
  if (!node)
    return (
      <>
        <span className="reader-kicker">图谱说明</span>
        <h2>选择图中节点</h2>
        <p>点击图中对象，查看名称、图内说明与关联关系。</p>
      </>
    );
  return (
    <>
      <span className="reader-kicker">当前节点</span>
      <h2>{node.label}</h2>
      {node.description && (
        <section>
          <h3>图中说明</h3>
          <p>{node.description}</p>
        </section>
      )}
      {node.context && (
        <section>
          <h3>所属环节</h3>
          <p>{node.context}</p>
        </section>
      )}
      {node.branches.length > 0 && (
        <section>
          <h3>关联关系</h3>
          <div className="reader-branches">
            {node.branches.map((branch) => (
              <button type="button" key={branch.id} onClick={() => select(branch.target)}>
                {branch.label}
              </button>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
