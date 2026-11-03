import { useMemo, useState, type ReactNode } from 'react';
import { guideForPage, type SourceGuide, type SourceStep } from './sourceGuides';
import { ReaderTabs } from './reader/ReaderTabs';
import { ReaderFrame, DiagramNodeDetail, type DiagramNode } from './reader/ReaderFrame';
import { DiagramViewport } from './reader/DiagramViewport';
import { flowDocument } from './reader/flowDocument';
import './source-guides.css';

export type StepVisual = (flow: string, step: string) => ReactNode;

export function SourceGuidePanel({
  page,
  renderVisual,
}: {
  page: string;
  renderVisual?: StepVisual;
}) {
  const guide = guideForPage(page);
  const [selected, setSelected] = useState(guide?.initialFlows?.[page] ?? guide?.flows[0]?.id);
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
      <ReaderTabs
        document={
          <SourceGuideDocument
            key={flow.id}
            guide={guide}
            renderVisual={renderVisual}
            initialFlow={flow.id}
            initialStep={step.id}
          />
        }
        graph={(openDocument) => (
          <>
            <div className="reader-flows" role="group" aria-label="选择阅读环节">
              {guide.flows.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={flow.id === item.id}
                  onClick={() => chooseFlow(item.id)}
                >
                  {item.title}
                </button>
              ))}
            </div>
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
              onDocument={openDocument}
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
      />
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

export function SourceGuideDocument({
  guide,
  renderVisual,
  initialFlow,
  initialStep,
}: {
  guide: SourceGuide;
  renderVisual?: StepVisual;
  initialFlow?: string;
  initialStep?: string;
}) {
  const [choice, setChoice] = useState(initialFlow ?? guide.flows[0].id);
  const flow = guide.flows.find((item) => item.id === choice) ?? guide.flows[0];
  return (
    <div className="reader-document-layout">
      <nav className="reader-chapters" aria-label="详细说明章节">
        {guide.flows.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-current={choice === item.id ? 'page' : undefined}
            onClick={() => setChoice(item.id)}
          >
            {item.title}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setChoice('boundaries')}
          aria-current={choice === 'boundaries' ? 'page' : undefined}
        >
          说明范围
        </button>
      </nav>
      <article className="reader-chapter">
        {choice === 'boundaries' ? (
          <>
            <h2>说明范围</h2>
            {guide.boundaries.map((claim, i) => (
              <p key={i}>{claim.text}</p>
            ))}
          </>
        ) : (
          <>
            <h2>{flow.title}</h2>
            <p>{flow.text}</p>
            {flow.steps.map((step, index) => (
              <section
                key={step.id}
                id={`reader-step-${flow.id}-${step.id}`}
                data-current-step={step.id === initialStep}
              >
                <h3>
                  {index + 1}. {step.title}
                </h3>
                <p>{step.text}</p>
                {renderVisual?.(flow.id, step.id)}
                {step.outcomes.map((branch, i) => (
                  <section key={i}>
                    <h4>{branch.label}</h4>
                    <p>{branch.text}</p>
                  </section>
                ))}
              </section>
            ))}
          </>
        )}
      </article>
    </div>
  );
}
