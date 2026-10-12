export interface SourceDeclaration {
  symbolId: string;
  fileId: string;
  start: number;
  end: number;
  syntaxKind: string;
  label?: string;
  name?: string;
  kind?: string;
}
export interface SourceFile {
  id: string;
  path: string;
  moduleId: string;
  sha256: string | null;
  baselineSha256: string | null;
  current: boolean;
  exists: boolean;
  encoding: string;
  lineCount: number;
  compileIncluded: boolean;
  assemblies: string[];
  declarationCount?: number;
  code?: string;
  declarations?: SourceDeclaration[];
}
export interface SymbolLink {
  id: string;
  label: string;
  moduleId?: string;
  origin: string;
  available?: boolean;
  sourceType?: { id: string; label: string; moduleId?: string; fileId?: string };
}
export interface CallSite {
  from: string;
  to: string | null;
  kind: string;
  dispatch: string;
  operation: string;
  usage: string;
  fileId: string;
  start: number;
  end: number;
  current: boolean;
  implicit: boolean;
  target: SymbolLink | null;
}
export interface DeclaredRelation {
  from: string;
  to: string;
  kind: string;
  current: boolean;
  direction: string;
  target: SymbolLink | null;
}
export interface SourceSymbol extends SymbolLink {
  identity: string;
  name: string;
  kind: string;
  methodKind?: string;
  assembly: string;
  fileId?: string;
  declarations: SourceDeclaration[];
  outgoing: CallSite[];
  incoming: CallSite[];
  relations: DeclaredRelation[];
  current: boolean;
}
export interface Dependency {
  from: string;
  to: string;
  count: number;
  kinds: Record<string, number>;
  current: boolean;
  samples: Array<CallSite & { caller: SymbolLink; callee: SymbolLink }>;
}
export interface EvidenceBinding {
  id: string;
  fileId: string;
  moduleId: string;
  start: number;
  end: number;
  symbolIds: string[];
  current: boolean;
}
export interface EngineeringEvidence extends EvidenceBinding {
  method: string;
  path: string;
  code: string;
  sha256: string;
}
export interface ModuleSummary {
  id: string;
  name: string;
  title: string;
  purpose: string;
  fileCount: number;
  compileFiles: number;
  declarationCount: number;
  callCount: number;
  reviewedFiles: number;
  status: string;
  reviewCurrent: boolean;
  currentEvidence: number;
  evidenceCount: number;
  staleFiles: number;
  workflows: Array<{ id: string; title: string }>;
}
export interface SourceModule extends ModuleSummary {
  files: SourceFile[];
  incoming: Dependency[];
  outgoing: Dependency[];
  entryMethods: Array<{ id: string; label: string; outgoingCount: number }>;
  review: {
    status: string;
    summary: string;
    gaps: string[];
    reviewedAt?: string;
    document?: string;
    evidenceIds: string[];
  };
  relationships: Array<{
    caller: string;
    callee: string;
    kind: string;
    note: string;
    current: boolean;
    evidence: EngineeringEvidence[];
  }>;
}
export interface EngineeringManifest {
  schemaVersion: number;
  version: string;
  generatedAt: string;
  sourceName: string;
  base: string;
  modules: ModuleSummary[];
  files: SourceFile[];
  nodeBindings: Record<string, EvidenceBinding[]>;
  dependencies: Dependency[];
  projects: Array<{
    assembly: string;
    files: number;
    errors: number;
    warnings: number;
    current: boolean;
    notes: string[];
    diagnostics: Array<{ id: string; message: string }>;
  }>;
  counts: {
    files: number;
    compileFiles: number;
    symbols: number;
    calls: number;
    unresolved: number;
    staleFiles: number;
    reviewedRelationships: number;
  };
  previousVersion: string | null;
  changes: Array<{
    path: string;
    fileId: string;
    moduleId: string;
    kind: string;
    impactedCallerCount?: number;
    impactedCallers: SymbolLink[];
  }>;
}
export type ProjectSourceRoute = {
  kind: 'project-source';
  path?: string;
  start?: number;
  end?: number;
  expectedVersion?: string;
};
export type EngineeringRoute =
  | { kind: 'source-module'; id: string }
  | { kind: 'source-file'; id: string; start?: number; end?: number }
  | { kind: 'source-method'; id: string }
  | { kind: 'source-import' }
  | ProjectSourceRoute;
