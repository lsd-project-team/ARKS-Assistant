import type { Plugin } from 'vite';

export const projectRoot: string;
export const knowledgeRoot: string;
export function knowledgePath(url: string): string;
export function readingDiagram(html: string): string;
export function knowledgeAssets(): Plugin;
