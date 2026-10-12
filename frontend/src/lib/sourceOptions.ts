import type { SourceOptions } from '../types.ts';

export const DEFAULT_SOURCES: SourceOptions = {
  use_deepwiki: true,
  use_knowledge: true,
  use_memory: true,
};

export function resolvedSources(options?: Partial<SourceOptions>): SourceOptions {
  return { ...DEFAULT_SOURCES, ...options };
}
