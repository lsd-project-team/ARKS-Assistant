import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { projectRoot } from './resources.mjs';
import { sourceGuides } from '../../src/features/knowledge/sourceGuides.ts';
import { validateAtlasCoverage } from './atlas-coverage-validation.mjs';

const coverage = JSON.parse(
  await readFile(resolve(projectRoot, 'docs/development/zx2200-atlas-coverage.json'), 'utf8'),
);
const plan = await readFile(resolve(projectRoot, coverage.plan), 'utf8');
const counts = validateAtlasCoverage({ plan, coverage, guides: sourceGuides });
console.log(
  `功能图谱清单核对：${counts.topics} 专题、${counts.requirements} 条要求，逐项复核 ${counts.reviewed} 条、待复核 ${counts.pending} 条。`,
);
