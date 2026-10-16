import { createContext, useContext, useState, type ComponentProps, type ReactNode } from 'react';
import ReactMarkdown, { defaultUrlTransform, type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useSourceCitation } from '../../features/source_reader/hooks/useSourceCitation';
import { CodeBlock } from '../../shared/ui/markdown/CodeBlock';
import { api } from '../api/client';
import type { RunContext, ProjectMaterial } from '../../shared/types/api';
import { toast } from '../../shared/utils/toasts';
import { useWorkspace } from '../state/store';
import { MaterialViewer } from '../../features/projects/components/MaterialViewer';
import { HandoverMaterialViewer } from '../../features/handover/materials/components/HandoverMaterialViewer';
import type { HandoverRecord } from '../../features/handover/shared/types';
import { isKnowledgeReference } from '../../features/knowledge/lib/knowledgeReference';

const CitationRun = createContext<string | undefined>(undefined);
const CitationSource = createContext<string | undefined>(undefined);

function MarkdownPre({ children }: { children?: ReactNode }) {
  return <CodeBlock>{children}</CodeBlock>;
}

function MarkdownLink({ href, children }: ComponentProps<'a'>) {
  const openCitation = useSourceCitation();
  const runId = useContext(CitationRun);
  const sourceId = useContext(CitationSource);
  const projectId = useWorkspace((state) => state.projectId);
  const [material, setMaterial] = useState<ProjectMaterial>();
  const [handoverMaterial, setHandoverMaterial] = useState<HandoverRecord>();
  const handoverReference = href?.match(/^handover-source:([\w-]+)\/(\d+)#L(\d+)(?:-L?(\d+))?$/);
  if (handoverReference)
    return (
      <>
        <button
          className="source-link"
          onClick={async () => {
            try {
              setHandoverMaterial(
                await api<HandoverRecord>(
                  `/handover/records/${handoverReference[1]}?version=${handoverReference[2]}`,
                  undefined,
                  '',
                ),
              );
            } catch {
              toast('无法读取这份交接资料的引用版本', undefined, 'error');
            }
          }}
        >
          {children}
        </button>
        {handoverMaterial && (
          <HandoverMaterialViewer
            row={handoverMaterial}
            start={Number(handoverReference[3])}
            end={Number(handoverReference[4] || handoverReference[3])}
            onClose={() => setHandoverMaterial(undefined)}
          />
        )}
      </>
    );
  const debugIssue = href?.match(/^debug-issue:([\w-]+)\/(\d+)$/);
  if (debugIssue)
    return (
      <button
        className="source-link"
        onClick={() => {
          window.location.hash = `handover/issues?record=${encodeURIComponent(debugIssue[1])}&version=${debugIssue[2]}`;
        }}
      >
        {children}
      </button>
    );
  const reference = href?.match(/^material:([\w-]+)\/([\w-]+)\/(\d+)#L(\d+)(?:-L?(\d+))?$/);
  if (reference)
    return (
      <>
        <button
          className="source-link"
          onClick={async () => {
            try {
              const saved = await api<ProjectMaterial>(
                `/projects/${reference[1]}/materials/${reference[2]}?version=${reference[3]}`,
              );
              if (useWorkspace.getState().projectId === projectId) setMaterial(saved);
            } catch {
              toast('无法读取这份项目资料的引用版本');
            }
          }}
        >
          {children}
        </button>
        {material && (
          <MaterialViewer
            material={material}
            start={Number(reference[4])}
            end={Number(reference[5] || reference[4])}
            onClose={() => setMaterial(undefined)}
          />
        )}
      </>
    );
  const source = href?.match(/^source:(.+)#L(\d+)(?:-L?(\d+))?$/);
  if (!source)
    return (
      <a href={href} target="_blank" rel="noreferrer">
        {children}
      </a>
    );
  return (
    <button
      className="source-link"
      onClick={async () => {
        let path = source[1];
        try {
          path = decodeURIComponent(path);
        } catch {
          /* 损坏的编码仍交给路径校验反馈。 */
        }
        try {
          const context = runId
            ? await api<RunContext>(`/runs/${runId}/context`, undefined, projectId)
            : undefined;
          if (useWorkspace.getState().projectId !== projectId) return;
          const evidence = context?.source_evidence
            ?.slice()
            .reverse()
            .find(
              (item) =>
                item.path === path &&
                item.start_line <= Number(source[2]) &&
                item.end_line >= Number(source[3] || source[2]),
            );
          if (runId && !evidence) toast('这条历史引用没有可核对的版本记录，请核对当前源码');
          await openCitation(
            path,
            Number(source[2]),
            Number(source[3] || source[2]),
            evidence?.version,
            evidence?.source_workspace_id ||
              (path.startsWith('@sources/') ? path.split('/')[1] : sourceId),
          );
        } catch {
          toast('无法读取引用依据，请稍后重试');
        }
      }}
    >
      {children}
    </button>
  );
}

// 渲染组件保持同一身份，页面更新和源码跳转才不会重建代码块、丢失展开与换行状态。
const markdownComponents: Components = { pre: MarkdownPre, a: MarkdownLink };

export function Markdown({
  content,
  runId,
  sourceId,
}: {
  content: string;
  runId?: string;
  sourceId?: string;
}) {
  return (
    <CitationRun.Provider value={runId}>
      <CitationSource.Provider value={sourceId}>
        <div className="markdown">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            urlTransform={(url) => (isKnowledgeReference(url) ? url : defaultUrlTransform(url))}
            components={markdownComponents}
          >
            {content}
          </ReactMarkdown>
        </div>
      </CitationSource.Provider>
    </CitationRun.Provider>
  );
}
