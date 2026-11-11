import type { PresentationTopic } from '../data/presentation';

export function GraphReadingNotes({
  reading,
  includeSummary = false,
}: {
  reading: PresentationTopic;
  includeSummary?: boolean;
}) {
  return (
    <section className="section reading-summary" aria-label="图谱说明">
      <article className="card panel">
        <h2>这个环节做什么</h2>
        {includeSummary && <p>{reading.summary}</p>}
        <p>{reading.purpose}</p>
      </article>
      <article className="card panel">
        <h2>哪些条件影响执行</h2>
        <ul>
          {reading.conditions.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </article>
      <article className="card panel">
        <h2>失败时如何理解</h2>
        <ul>
          {reading.exceptions.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </article>
    </section>
  );
}
