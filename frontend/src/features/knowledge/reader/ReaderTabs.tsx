import { useId, useState, type ReactNode } from 'react';
import './reader.css';

/** 保留两页内容的挂载状态，返回图谱时继续使用原节点与缩放位置。 */
export function ReaderTabs({
  graph,
  document,
  documentOpen,
  onDocumentChange,
}: {
  graph: (openDocument: () => void) => ReactNode;
  document: ReactNode;
  documentOpen?: boolean;
  onDocumentChange?: (open: boolean) => void;
}) {
  const id = useId();
  const [localOpen, setLocalOpen] = useState(false);
  const [documentVisited, setDocumentVisited] = useState(documentOpen === true);
  const open = documentOpen ?? localOpen;
  const select = (value: boolean) => {
    if (value) setDocumentVisited(true);
    setLocalOpen(value);
    onDocumentChange?.(value);
  };
  return (
    <div className="unified-reader" data-reader-layout="graph-and-text">
      <div className="reader-tabs" role="tablist" aria-label="阅读方式">
        {[false, true].map((value) => (
          <button
            key={String(value)}
            type="button"
            role="tab"
            id={`${id}-tab-${value}`}
            aria-controls={`${id}-panel-${value}`}
            aria-selected={open === value}
            onClick={() => select(value)}
          >
            {value ? '详细说明' : '图谱阅读'}
          </button>
        ))}
      </div>
      <div
        id={`${id}-panel-false`}
        role="tabpanel"
        aria-labelledby={`${id}-tab-false`}
        hidden={open}
      >
        {graph(() => select(true))}
      </div>
      <div
        id={`${id}-panel-true`}
        role="tabpanel"
        aria-labelledby={`${id}-tab-true`}
        hidden={!open}
      >
        {(open || documentVisited) && document}
      </div>
    </div>
  );
}
