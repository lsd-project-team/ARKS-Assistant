import {
  Children,
  isValidElement,
  lazy,
  Suspense,
  createContext,
  useContext,
  useState,
  type ComponentProps,
  type ReactNode,
} from 'react';
import ReactMarkdown, { defaultUrlTransform, type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { useSourceCitation } from '../../features/source_reader/hooks/useSourceCitation';
import { CodeBlock } from '../../shared/ui/markdown/CodeBlock';
import { api } from '../api/client';
import type { RunContext } from '../../shared/types/api';
import { toast } from '../../shared/utils/toasts';
import { useWorkspace } from '../state/store';
import { HandoverMaterialViewer } from '../../features/handover/materials/components/HandoverMaterialViewer';
import type { HandoverRecord } from '../../features/handover/shared/types';
import { isKnowledgeReference } from '../../features/knowledge/lib/knowledgeReference';
import { citationEndLine } from '../../features/source_reader/lib/citationRange';
import { DebugIssueReference } from '../../features/chat/components/DebugIssueReference';

const CitationRun = createContext<string | undefined>(undefined);
const CitationSource = createContext<string | undefined>(undefined);
const Streaming = createContext(false);
const MermaidBlock = lazy(() =>
  import('../../features/chat/rich/MermaidBlock')
    .then((module) => ({ default: module.MermaidBlock }))
    .catch(() => ({
      default: ({ block }: { block: { content: string } }) => (
        <div>
          <p role="status">流程图组件加载失败，已保留源码。</p>
          <CodeBlock>
            <code>{block.content}</code>
          </CodeBlock>
        </div>
      ),
    })),
);

function MarkdownPre({ children }: { children?: ReactNode }) {
  const streaming = useContext(Streaming);
  const code = Children.toArray(children).find((child) => isValidElement(child));
  if (
    isValidElement<{ className?: string; children?: ReactNode }>(code) &&
    code.props.className === 'language-mermaid'
  ) {
    const content = Children.toArray(code.props.children).join('');
    return (
      <Suspense
        fallback={
          <CodeBlock streaming rawContent={content}>
            {children}
          </CodeBlock>
        }
      >
        <MermaidBlock
          block={{ id: 'markdown-mermaid', type: 'mermaid', content }}
          streaming={streaming}
        />
      </Suspense>
    );
  }
  return <CodeBlock streaming={streaming}>{children}</CodeBlock>;
}

function MarkdownLink({ href, children }: ComponentProps<'a'>) {
  const openCitation = useSourceCitation();
  const runId = useContext(CitationRun);
  const sourceId = useContext(CitationSource);
  const projectId = useWorkspace((state) => state.projectId);
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
  const debugIssue = href?.match(/^debug-issue:([\w-]+)\/([1-9]\d*)$/);
  if (debugIssue && Number.isSafeInteger(Number(debugIssue[2])))
    return (
      <DebugIssueReference
        id={debugIssue[1]}
        version={Number(debugIssue[2])}
        label={Children.toArray(children)
          .filter((child) => typeof child === 'string')
          .join('')}
      >
        {children}
      </DebugIssueReference>
    );
  if (!href) return <span>{children}</span>;
  const source = href?.match(/^source:(.+)#L(\d+)(?:-L?(\d+))?$/);
  if (!source)
    return isKnowledgeReference(href || '') ? (
      <span title="引用格式无效">{children}（引用格式无效）</span>
    ) : (
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
          const start = Number(source[2]);
          const end = citationEndLine(
            path,
            start,
            source[3],
            Children.toArray(children)
              .filter((child) => typeof child === 'string')
              .join(''),
            context?.source_evidence || [],
          );
          const evidence = context?.source_evidence
            ?.slice()
            .reverse()
            .find((item) => item.path === path && item.start_line <= start && item.end_line >= end);
          if (runId && !evidence) toast('这条历史引用没有可核对的版本记录，请核对当前源码');
          await openCitation(
            path,
            start,
            end,
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
const markdownComponents: Components = {
  pre: MarkdownPre,
  a: MarkdownLink,
  table: ({ children }) => (
    <div className="markdown-table-scroll" role="region" aria-label="表格，可横向滚动" tabIndex={0}>
      <table>{children}</table>
    </div>
  ),
};

export function Markdown({
  content,
  runId,
  sourceId,
  streaming = false,
}: {
  content: string;
  runId?: string;
  sourceId?: string;
  streaming?: boolean;
}) {
  return (
    <CitationRun.Provider value={runId}>
      <CitationSource.Provider value={sourceId}>
        <Streaming.Provider value={streaming}>
          <div className="markdown">
            <ReactMarkdown
              // 工艺范围常写成20~30g、280~300，单个波浪号不能跨参数误解析为删除线。
              remarkPlugins={[[remarkGfm, { singleTilde: false }], remarkMath]}
              // 只转换数学语法树；不启用 raw HTML，公式中的链接和 HTML 扩展也不受信任。
              rehypePlugins={[
                [rehypeKatex, { throwOnError: false, trust: false, maxExpand: 500, maxSize: 20 }],
              ]}
              urlTransform={(url) => (isKnowledgeReference(url) ? url : defaultUrlTransform(url))}
              components={markdownComponents}
            >
              {content}
            </ReactMarkdown>
          </div>
        </Streaming.Provider>
      </CitationSource.Provider>
    </CitationRun.Provider>
  );
}
