import evidenceData from './data/source-evidence.json' with { type: 'json' };
import { startupGuide } from './reviews/startup.ts';
import { recoveryGuide } from './reviews/recovery.ts';
import { transportGuide } from './reviews/transport.ts';
import { s1Guide } from './reviews/s1.ts';
import { s2Guide } from './reviews/s2.ts';
import { waferGuide } from './reviews/wafer.ts';

export interface SourceClaim {
  text: string;
  refs: string[];
}
export interface SourceOutcome extends SourceClaim {
  label: string;
}
export interface SourceStep extends SourceClaim {
  id: string;
  title: string;
  outcomes: SourceOutcome[];
}
export interface SourceFlow extends SourceClaim {
  id: string;
  title: string;
  steps: SourceStep[];
  sequential?: boolean;
}
export interface SourceGuide {
  id: string;
  topic: string;
  diagrams: string[];
  initialFlows?: Record<string, string>;
  title: string;
  flows: SourceFlow[];
  boundaries: SourceClaim[];
}
export interface EvidenceSource {
  path: string;
  sha256: string;
}
export interface EvidenceRange {
  file: string;
  method: string;
  start: number;
  end: number;
  code: string;
}

export const sourceEvidence = evidenceData as {
  sources: Record<string, EvidenceSource>;
  ranges: Record<string, EvidenceRange>;
  diagrams: Record<string, { path: string; sha256: string }>;
};
export const sourceGuides: SourceGuide[] = [
  startupGuide,
  recoveryGuide,
  transportGuide,
  s1Guide,
  s2Guide,
  waferGuide,
];
export const sourceReviewVersion = Object.values(sourceEvidence.sources)
  .map((file) => file.sha256)
  .join(':');
export const sourceCheckId = (file: string) => `source-guide:${file}`;
export function sourceDiagramRevision(url: string) {
  return Object.values(sourceEvidence.diagrams)
    .find((diagram) => `/${diagram.path}` === url)
    ?.sha256.slice(0, 16);
}
export function guideForPage(id: string) {
  return sourceGuides.find((guide) => guide.topic === id || guide.diagrams.includes(id));
}
