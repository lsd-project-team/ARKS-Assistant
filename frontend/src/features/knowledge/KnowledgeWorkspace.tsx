import { useMemo, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useProjectApi } from '../projects/hooks/useProjectApi';
import { useAppearance } from '../settings/lib/appearance';
import { EngineeringContext, BaselineContext, useResource } from './engineeringData';
import type { EngineeringManifest } from './engineeringTypes';
import { refreshSnapshot, type FileChecks } from './freshness';
import { sourceCheckId, sourceEvidence, sourceReviewVersion } from './sourceGuides';
import { routeNames, workspacePath, type Route } from './routes';
import { WorkspaceHeading } from '../../app/layouts/WorkspaceHeader';
import { GraphAtlas, DiagramDetail, TopicDetail, diagramRoute } from './KnowledgePages';
import { ShowcaseHome } from './PresentationViews';
import {
  EngineeringDirectory,
  SourceModuleView,
  SourceFileView,
  SourceMethodView,
} from './EngineeringViews';
import './legacy-styles.css';

const EMPTY_CHECKS: FileChecks = {};
export default function KnowledgeWorkspace({
  route,
  navigate,
}: {
  route: Route;
  navigate: (route: Route) => void;
}) {
  const api = useProjectApi();
  const mode = useAppearance((state) => state.mode);
  const scroller = useRef<HTMLDivElement>(null);
  const manifest = useQuery({
    queryKey: ['knowledge-manifest'],
    queryFn: async () => {
      const response = await fetch('/engineering/manifest.json');
      if (!response.ok) throw new Error(`资料读取失败 (${response.status})`);
      return response.json() as Promise<EngineeringManifest>;
    },
    staleTime: Infinity,
  });
  const baseline = useQuery({
    queryKey: ['knowledge-baseline', manifest.data?.version, sourceReviewVersion],
    enabled: !!manifest.data,
    queryFn: () =>
      api<{ files: FileChecks }>('/knowledge/check', {
        method: 'POST',
        body: JSON.stringify({
          files: [
            ...manifest.data!.files.map((file) => ({
              id: file.id,
              path: workspacePath(file.path),
              sha256: file.sha256,
            })),
            ...Object.entries(sourceEvidence.sources).map(([id, source]) => ({
              id: sourceCheckId(id),
              path: source.path,
              sha256: source.sha256,
            })),
          ],
        }),
      }),
    staleTime: 30000,
    refetchInterval: 60000,
  });
  const checks = baseline.data?.files ?? EMPTY_CHECKS;
  const { data: evidence } = useResource<{
    refs: Record<string, { fileId?: string; sha256: string; current: boolean }>;
    modules: Record<string, string[]>;
  }>(manifest.data ? `${manifest.data.base}/evidence-baseline.json` : undefined);
  const evidenceChecks = useMemo(() => {
    if (!evidence) return checks;
    const result = { ...checks };
    for (const [id, ref] of Object.entries(evidence.refs)) {
      const file = ref.fileId ? checks[ref.fileId] : undefined;
      result[id] = file?.version
        ? { ...file, status: ref.current && file.version === ref.sha256 ? 'match' : 'changed' }
        : { status: file?.status ?? 'unavailable' };
    }
    // 跨模块的调用位置不能只看少量示例；关联模块有变化时，整条依赖都需复核。
    for (const module of manifest.data?.modules ?? []) {
      const files = manifest.data!.files.filter((file) => file.moduleId === module.id);
      result[module.id] = {
        status: files.every((file) => checks[file.id]?.status === 'match') ? 'match' : 'changed',
      };
    }
    return result;
  }, [checks, evidence, manifest.data]);
  const engineering = useMemo(() => {
    if (!manifest.data) return null;
    const next = refreshSnapshot(manifest.data, evidenceChecks);
    const staleByModule = new Map<string, number>();
    for (const file of next.files) {
      if (!file.current)
        staleByModule.set(file.moduleId, (staleByModule.get(file.moduleId) ?? 0) + 1);
    }
    next.modules = next.modules.map((module) => {
      const ids = evidence?.modules[module.id];
      const currentEvidence =
        ids?.filter((id) => evidenceChecks[id]?.status === 'match').length ??
        module.currentEvidence;
      return {
        ...module,
        currentEvidence,
        staleFiles: staleByModule.get(module.id) ?? 0,
        reviewCurrent:
          module.reviewCurrent &&
          !staleByModule.has(module.id) &&
          currentEvidence === module.evidenceCount,
      };
    });
    next.counts.staleFiles = next.files.filter((file) => !file.current).length;
    return next;
  }, [manifest.data, evidenceChecks, evidence]);
  useEffect(() => {
    scroller.current?.scrollTo({ top: 0 });
  }, [route]);
  const theme = mode === 'dark' ? 'dark' : 'light';
  let page;
  switch (route.kind) {
    case 'graphs':
      page = <GraphAtlas navigate={navigate} />;
      break;
    case 'graph':
      page = (
        <DiagramDetail
          key={route.slug}
          id={route.slug}
          focusedSignal={route.signal}
          navigate={navigate}
          theme={theme}
        />
      );
      break;
    case 'catalog':
      page = <DiagramDetail key={route.id} id={route.id} navigate={navigate} theme={theme} />;
      break;
    case 'topic':
      page = <TopicDetail key={route.id} id={route.id} navigate={navigate} />;
      break;
    case 'source-module':
      page = <SourceModuleView key={route.id} id={route.id} navigate={navigate} />;
      break;
    case 'source-method':
      page = <SourceMethodView key={route.id} id={route.id} navigate={navigate} />;
      break;
    case 'source-file':
      page = <SourceFileView key={route.id} {...route} navigate={navigate} />;
      break;
    default:
      page = (
        <>
          <ShowcaseHome
            onTopic={(id) => navigate({ kind: 'topic', id })}
            onDiagram={(id) => navigate(diagramRoute(id))}
            onAllDiagrams={() => navigate({ kind: 'graphs' })}
          />
          <EngineeringDirectory navigate={navigate} />
        </>
      );
  }
  return (
    <section className="knowledge-workspace" aria-label="流程与功能资料" ref={scroller}>
      <WorkspaceHeading className="knowledge-page-heading">
        <div className="breadcrumb">
          <strong>{routeNames[route.kind]}</strong>
        </div>
      </WorkspaceHeading>
      <div className="knowledge-content">
        {manifest.error ? (
          <div className="card panel" role="alert">
            {manifest.error.message}
            <button className="button" onClick={() => void manifest.refetch()}>
              重新读取资料
            </button>
          </div>
        ) : (
          <EngineeringContext.Provider value={engineering}>
            <BaselineContext.Provider value={evidenceChecks}>{page}</BaselineContext.Provider>
          </EngineeringContext.Provider>
        )}
      </div>
    </section>
  );
}
