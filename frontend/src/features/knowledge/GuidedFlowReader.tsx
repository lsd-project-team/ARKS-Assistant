import { useRef, useState } from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Select } from '../../shared/ui/Select';
import { useAppearance } from '../settings/lib/appearance';
import { DiagramFrame, diagramHref } from './DiagramFrame';
import type { GuidedDiagram } from './guidedDiagrams';
import type { SourceFlow } from './sourceGuides';
import { SourceStepDetail } from './SourceStepDetail';

export function GuidedFlowReader({ flow, diagram }: { flow: SourceFlow; diagram: GuidedDiagram }) {
  const [selected, setSelected] = useState(flow.steps[0].id);
  const reader = useRef<HTMLDivElement>(null);
  const index = flow.steps.findIndex((step) => step.id === selected);
  const step = flow.steps[index];
  const mode = useAppearance((state) => state.mode);
  const theme = mode === 'dark' ? 'dark' : 'light';
  const selectNode = (nodeId: string) => {
    // 多条提前返回可以共享一个图节点；当前步骤命中时保留阅读上下文。
    const target = diagram.steps[selected]?.includes(nodeId)
      ? flow.steps[index]
      : flow.steps.find((item) => diagram.steps[item.id]?.includes(nodeId));
    if (target) setSelected(target.id);
    // 图下半部也能直接读到对应说明，滚动只发生在主动点图时。
    if (target)
      requestAnimationFrame(() =>
        reader.current
          ?.querySelector('.source-step-detail')
          ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }),
      );
  };
  return (
    <div className="guided-flow-reader" ref={reader}>
      <div className="guided-step-controls" aria-label="逐步阅读">
        <span>逐步看</span>
        <Select aria-label="选择步骤" value={step.id} onValueChange={setSelected}>
          {flow.steps.map((item, position) => (
            <option key={item.id} value={item.id}>
              {position + 1}. {item.title}
            </option>
          ))}
        </Select>
        <span className="guided-step-count">
          {index + 1} / {flow.steps.length}
        </span>
        <button
          className="button"
          disabled={index === 0}
          onClick={() => setSelected(flow.steps[index - 1].id)}
        >
          <ArrowLeft size={15} /> 上一步
        </button>
        <button
          className="button"
          disabled={index === flow.steps.length - 1}
          onClick={() => setSelected(flow.steps[index + 1].id)}
        >
          下一步 <ArrowRight size={15} />
        </button>
      </div>
      <div className="guided-flow-layout">
        <figure className="guided-flow-diagram" aria-label={diagram.title}>
          <figcaption>
            <span>{diagram.title}</span>
            <a
              href={diagramHref(diagram.path, theme, diagram.sha256)}
              target="_blank"
              rel="noreferrer"
            >
              全屏阅读 ↗
            </a>
          </figcaption>
          <DiagramFrame
            path={diagram.path}
            title={diagram.title}
            revision={diagram.sha256}
            theme={theme}
            activeNode={diagram.steps[step.id][0]}
            onNode={selectNode}
          />
        </figure>
        <SourceStepDetail step={step} heading={false} />
      </div>
    </div>
  );
}
