import { useWorkspace } from '../lib/store';
import { Modal } from './ui';

export function HistoricalSourceDialog() {
  const citation = useWorkspace((state) => state.historicalSource);
  if (!citation) return null;
  const lines = citation.source.content.split('\n');
  const first = Math.max(1, citation.start - 8);
  const last = Math.min(lines.length, citation.end + 12);
  return (
    <Modal
      open
      onClose={() => useWorkspace.setState({ historicalSource: null })}
      title="原始源码引用"
      description="此引用来自另一个源码目录，按原始来源只读展示。"
      className="historical-source-dialog"
    >
      <div className="historical-source-path">
        {citation.source.path} · L{citation.start}–{citation.end}
      </div>
      <div className="historical-source-lines">
        {lines.slice(first - 1, last).map((text, index) => {
          const number = first + index;
          return (
            <div
              key={number}
              className={number >= citation.start && number <= citation.end ? 'cited' : ''}
            >
              <span>{number}</span>
              <code>{text || ' '}</code>
            </div>
          );
        })}
      </div>
    </Modal>
  );
}
