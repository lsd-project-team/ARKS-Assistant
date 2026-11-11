import { useMemo, useState, type ReactNode } from 'react';
import { guideForPage, type SourceStep } from './sourceGuides';
import { ReaderFrame, DiagramNodeDetail, type DiagramNode } from './reader/ReaderFrame';
import { DiagramViewport } from './reader/DiagramViewport';
import { flowDocument } from './reader/flowDocument';

export type StepVisual = (flow: string, step: string) => ReactNode;

export function SourceGuidePanel({
  page,
  renderVisual,
  overview,
}: {
  page: string;
  renderVisual?: StepVisual;
  overview?: ReactNode;
}) {
  const guide = guideForPage(page);
  // 原图与补充流程共用阅读区；切换环节时保留原图入口，避免页面重复堆叠画布。
  const [selected, setSelected] = useState(
    overview ? 'overview' : (guide?.initialFlows?.[page] ?? guide?.flows[0]?.id),
  );
  const [stepId, setStepId] = useState<string>();
  const flow = guide?.flows.find((item) => item.id === selected) ?? guide?.flows[0];
  const step = flow?.steps.find((item) => item.id === stepId) ?? flow?.steps[0];
  const map = useMemo(() => (flow ? flowDocument(flow) : ''), [flow]);
  if (!guide || !flow || !step) return null;
  const visual = renderVisual?.(flow.id, step.id);
  const chooseFlow = (id: string) => {
    setSelected(id);
    setStepId(undefined);
  };
  return (
    <section className="section" aria-label={guide.title}>
      <div className="unified-reader" data-reader-layout="diagram">
        <div className="reader-flows" role="group" aria-label="选择阅读环节">
          {overview && (
            <button
              type="button"
              aria-pressed={selected === 'overview'}
              onClick={() => chooseFlow('overview')}
            >
              完整图谱
            </button>
          )}
          {guide.flows.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={selected !== 'overview' && flow.id === item.id}
              onClick={() => chooseFlow(item.id)}
            >
              {item.title}
            </button>
          ))}
        </div>
        {overview && selected === 'overview' ? (
          overview
        ) : (
          <>
            <label className="reader-step-picker">
              阅读节点
              <select
                aria-label="选择阅读节点"
                value={step.id}
                onChange={(event) => setStepId(event.target.value)}
              >
                {flow.steps.map((item, i) => (
                  <option key={item.id} value={item.id}>
                    {i + 1}. {item.title}
                  </option>
                ))}
              </select>
            </label>
            <ReaderFrame
              key={`${flow.id}-${visual ? step.id : 'map'}`}
              title={flow.title}
              selectedId={visual ? undefined : step.id}
              onSelect={visual ? undefined : (id) => setStepId(id)}
              detail={(node, select) => (
                <GuideStepDetail
                  step={step}
                  index={flow.steps.indexOf(step)}
                  node={visual ? node : undefined}
                  select={select}
                />
              )}
            >
              {visual || <DiagramViewport title={flow.title} source={map} />}
            </ReaderFrame>
          </>
        )}
      </div>
    </section>
  );
}

function GuideStepDetail({
  step,
  index,
  node,
  select,
}: {
  step: SourceStep;
  index: number;
  node?: DiagramNode;
  select: (id: string) => void;
}) {
  return (
    <>
      {node ? (
        <DiagramNodeDetail node={node} select={select} />
      ) : (
        <>
          <span className="reader-kicker">阅读节点 {String(index + 1).padStart(2, '0')}</span>
          <h2>{step.title}</h2>
        </>
      )}
      <section>
        <h3>{node ? `阅读环节 · ${step.title}` : '作用与执行条件'}</h3>
        <p>{step.text}</p>
      </section>
      {step.outcomes.map((outcome, i) => (
        <section key={i}>
          <h3>{outcome.label}</h3>
          <p>{outcome.text}</p>
        </section>
      ))}
    </>
  );
}
