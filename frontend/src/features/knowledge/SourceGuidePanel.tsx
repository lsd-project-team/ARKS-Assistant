import { useContext, useState } from 'react';
import { ArrowDown, ChevronRight } from 'lucide-react';
import { BaselineContext } from './engineeringData';
import { guideForPage, sourceCheckId, sourceEvidence } from './sourceGuides';
import type { SourceClaim, SourceFlow } from './sourceGuides';
import type { Route } from './routes';
import './source-guides.css';

type Navigate = (route: Route) => void;
export function SourceGuidePanel({ page, navigate }: { page: string; navigate: Navigate }) {
  const guide = guideForPage(page);
  // 专题保留整体入口；局部图默认展示对应环节，避免胶检页先打开配方排序。
  const [selected, setSelected] = useState(guide?.initialFlows?.[page] ?? guide?.flows[0]?.id);
  if (!guide) return null;
  const flow = guide.flows.find((item) => item.id === selected) ?? guide.flows[0];
  return (
    <section className="section source-guide" aria-label={guide.title}>
      <div className="section-heading">
        <div>
          <h2>{guide.title}</h2>
          <p>选择环节，阅读对应的条件、调用和返回分支。</p>
        </div>
      </div>
      <div className="source-guide-tabs" role="group" aria-label="选择阅读环节">
        {guide.flows.map((item) => (
          <button
            key={item.id}
            aria-pressed={item.id === flow.id}
            aria-controls={`source-flow-${item.id}`}
            id={`source-tab-${item.id}`}
            onClick={() => setSelected(item.id)}
          >
            {item.title}
          </button>
        ))}
      </div>
      <SourceFlowPanel key={flow.id} flow={flow} navigate={navigate} />
      <details className="source-guide-boundary">
        <summary>本次说明的源码范围</summary>
        {guide.boundaries.map((claim, index) => (
          <SourceClaimText key={index} claim={claim} navigate={navigate} />
        ))}
      </details>
    </section>
  );
}

function SourceFlowPanel({ flow, navigate }: { flow: SourceFlow; navigate: Navigate }) {
  const [selected, setSelected] = useState(flow.steps[0].id);
  const step = flow.steps.find((item) => item.id === selected) ?? flow.steps[0];
  return (
    <div
      className="card panel source-flow-panel"
      role="region"
      id={`source-flow-${flow.id}`}
      aria-labelledby={`source-tab-${flow.id}`}
    >
      <SourceClaimText claim={flow} navigate={navigate} />
      <div className="source-flow-layout">
        <ol
          className="source-flow-nodes"
          aria-label={`${flow.title}${flow.sequential === false ? '阅读分支' : '流程节点'}`}
        >
          {flow.steps.map((item, index) => (
            <li key={item.id}>
              <button
                className={item.id === step.id ? 'selected' : ''}
                aria-pressed={item.id === step.id}
                onClick={() => setSelected(item.id)}
              >
                <span>{String(index + 1).padStart(2, '0')}</span>
                <b>{item.title}</b>
                <ChevronRight size={14} />
              </button>
              {flow.sequential !== false && index < flow.steps.length - 1 && (
                <ArrowDown className="source-flow-arrow" size={16} aria-hidden="true" />
              )}
            </li>
          ))}
        </ol>
        <article className="source-step-detail" aria-live="polite">
          <h3>{step.title}</h3>
          <SourceClaimText claim={step} navigate={navigate} />
          {step.outcomes.map((branch, index) => (
            <section className="source-flow-outcome" key={index}>
              <h4>{branch.label}</h4>
              <SourceClaimText claim={branch} navigate={navigate} />
            </section>
          ))}
        </article>
      </div>
    </div>
  );
}

function SourceClaimText({ claim, navigate }: { claim: SourceClaim; navigate: Navigate }) {
  const checks = useContext(BaselineContext);
  const changed = claim.refs.some((id) => {
    const file = sourceEvidence.ranges[id].file;
    const check = checks[sourceCheckId(file)];
    return check && check.status !== 'match';
  });
  return (
    <div className="source-claim">
      <p>{claim.text}</p>
      {changed && (
        <p className="source-claim-changed">
          对应源码已变化或无法读取，以下保存的依据需要重新核对。
        </p>
      )}
      <details className="source-claim-evidence">
        <summary>
          源码依据 <span>{claim.refs.length}</span>
        </summary>
        {claim.refs.map((id) => {
          const ref = sourceEvidence.ranges[id];
          const source = sourceEvidence.sources[ref.file];
          // 跳转时按本条依据的版本再次读取当前文件，不借用历史索引版本。
          return (
            <div key={id} className="source-evidence-range">
              <button
                className="text-button"
                onClick={() =>
                  navigate({
                    kind: 'project-source',
                    path: source.path,
                    start: ref.start,
                    end: ref.end,
                    expectedVersion: source.sha256,
                  })
                }
              >
                {ref.method} · L{ref.start}–{ref.end} ↗
              </button>
              <small>{source.path}</small>
              <pre>
                {ref.code
                  .split('\n')
                  .map((line, index) => `${ref.start + index}: ${line}`)
                  .join('\n')}
              </pre>
            </div>
          );
        })}
      </details>
    </div>
  );
}
