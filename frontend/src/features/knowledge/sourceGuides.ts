import { startupGuide } from './reviews/startup.ts';
import { recoveryGuide } from './reviews/recovery.ts';
import { transportGuide } from './reviews/transport.ts';
import { s1Guide } from './reviews/s1.ts';
import { s2Guide } from './reviews/s2.ts';
import { waferGuide } from './reviews/wafer.ts';
import { g0Guide } from './reviews/g0.ts';
import { productCoordinatesGuide } from './reviews/productCoordinates.ts';
import { publicVisionGuide } from './reviews/publicVision.ts';

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
export const sourceGuides: SourceGuide[] = [
  g0Guide,
  productCoordinatesGuide,
  publicVisionGuide,
  startupGuide,
  recoveryGuide,
  transportGuide,
  s1Guide,
  s2Guide,
  waferGuide,
];
export function guideForPage(id: string) {
  return sourceGuides.find((guide) => guide.topic === id || guide.diagrams.includes(id));
}
