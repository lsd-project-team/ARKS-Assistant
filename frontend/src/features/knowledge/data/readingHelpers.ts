import { diagramReadings } from './diagramReading.ts';

export const displayDiagramTitle = (id: string, original: string) =>
  diagramReadings[id]?.title ?? original;
