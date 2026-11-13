import { sourceGuides } from './src/features/knowledge/sourceGuides.ts';

for (const guide of sourceGuides) {
  console.log(`\n=== guide ${guide.id} | ${guide.title}`);
  for (const flow of guide.flows) {
    console.log(`FLOW\t${flow.id}\t${flow.title}`);
    for (const step of flow.steps) {
      console.log(`STEP\t${step.id}\t${step.title}`);
      for (const outcome of step.outcomes) {
        console.log(`OUT\t${outcome.label}`);
      }
    }
  }
}
