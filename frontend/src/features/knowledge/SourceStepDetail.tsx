import type { SourceStep } from './sourceGuides';

export function SourceStepDetail({
  step,
  heading = true,
}: {
  step: SourceStep;
  heading?: boolean;
}) {
  return (
    <article className="source-step-detail" aria-live="polite" aria-label={step.title}>
      {heading && <h3>{step.title}</h3>}
      <div className="source-claim">
        <p>{step.text}</p>
      </div>
      {step.outcomes.map((branch, index) => (
        <section className="source-flow-outcome" key={index}>
          <h4>{branch.label}</h4>
          <div className="source-claim">
            <p>{branch.text}</p>
          </div>
        </section>
      ))}
    </article>
  );
}
