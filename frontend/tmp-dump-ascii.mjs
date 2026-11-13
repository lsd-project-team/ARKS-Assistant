import { sourceGuides } from './src/features/knowledge/sourceGuides.ts';

for (const guide of sourceGuides) {
  for (const flow of guide.flows) {
    const items = [
      ['FLOW', flow.title],
      ...flow.steps.flatMap((step) => [
        ['STEP', step.title],
        ...step.outcomes.map((o) => ['OUT', o.label]),
      ]),
    ];
    for (const [kind, value] of items) {
      if (/[A-Za-z]/.test(value)) {
        console.log(`${guide.id}\t${kind}\t${value}`);
      }
    }
  }
}
