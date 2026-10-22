import { useEffect, useMemo, useRef, useState } from 'react';
import {
  useEngineering,
  useResource,
  useSymbol,
  callKindLabel,
  dispatchLabel,
} from './engineeringData';
import { displayDiagramTitle } from './data/presentation';
import type {
  CallSite,
  Dependency,
  EngineeringRoute,
  EvidenceBinding,
  SourceFile,
  SourceModule,
  SourceSymbol,
  SymbolLink,
} from './engineeringTypes';
import type { ChatRoute } from './routes';

type Navigate = (route: EngineeringRoute | ChatRoute | { kind: 'graph'; slug: string }) => void;
const statusLabel = (status: string) =>
  status === 'partial' ? '部分复核' : status === 'complete' ? '已复核' : '待复核';
function Loading({ error }: { error?: string }) {
  return (
    <div className="card panel" role="status">
      {error ? `内容读取失败：${error}。请刷新页面重试。` : '正在读取源码索引…'}
    </div>
  );
}
function VersionStamp() {
  const m = useEngineering();
  return (
    m && (
      <p className="engineering-version">
        源码版本 <code>{m.version}</code> · 索引时间{' '}
        {new Date(m.generatedAt).toLocaleString('zh-CN')}
      </p>
    )
  );
}

export function TopicSourceModules({
  diagrams,
  all = false,
  navigate,
}: {
  diagrams: string[];
  all?: boolean;
  navigate: Navigate;
}) {
  const manifest = useEngineering();
  const modules =
    manifest?.modules.filter((m) => all || m.workflows.some((w) => diagrams.includes(w.id))) ?? [];
  if (!modules.length) return null;
  return (
    <section className="section">
      <div className="section-heading">
        <div>
          <h2>{all ? '源码模块结构' : '关联源码模块'}</h2>
          <p>查看职责、调用关系、对应源码和模块复核进度。</p>
        </div>
      </div>
      <div className="topic-grid">
        {modules.map((m) => (
          <button
            className="card topic-card"
            key={m.id}
            onClick={() => navigate({ kind: 'source-module', id: m.id })}
          >
            <div className="topic-card-meta">
              <span className="pill">{statusLabel(m.status)}</span>
              <small>{m.fileCount} 个文件</small>
            </div>
            <h2>{m.title}</h2>
            <p>{m.purpose}</p>
            <strong>模块与源码 →</strong>
          </button>
        ))}
      </div>
    </section>
  );
}

export function SourceSearch({ navigate, moduleId }: { navigate: Navigate; moduleId?: string }) {
  const m = useEngineering(),
    [query, setQuery] = useState('');
  const { data, error } = useResource<SourceSymbol[]>(
    m && query.trim() ? `${m.base}/search.json` : undefined,
  );
  const q = query.trim().toLowerCase();
  const files = q
    ? (m?.files.filter(
        (f) => (!moduleId || f.moduleId === moduleId) && f.path.toLowerCase().includes(q),
      ) ?? [])
    : [];
  const symbols = q
    ? (data?.filter(
        (s) =>
          (!moduleId || s.moduleId === moduleId) &&
          `${s.label} ${s.name}`.toLowerCase().includes(q),
      ) ?? [])
    : [];
  return (
    <section className="card panel knowledge-source-search">
      <h2>查找文件、类或方法</h2>
      <input
        aria-label="搜索源码"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="输入文件路径、类名或方法名…"
      />
      {q && (
        <>
          <p>
            {files.length} 个文件 · {symbols.length} 个符号{!data && !error && ' · 方法索引读取中…'}
          </p>
          {error && <p role="alert">{error}</p>}
          <div className="source-result-list">
            {files.slice(0, 10).map((f) => (
              <button key={f.id} onClick={() => navigate({ kind: 'source-file', id: f.id })}>
                <b>文件</b>
                <code>{f.path}</code>
                <span>→</span>
              </button>
            ))}
            {symbols.slice(0, 30).map((s) => (
              <button key={s.id} onClick={() => navigate({ kind: 'source-method', id: s.id })}>
                <b>{s.kind === 'Method' ? '方法' : s.kind === 'NamedType' ? '类型' : '成员'}</b>
                <code>{s.label}</code>
                <span>→</span>
              </button>
            ))}
          </div>
          {symbols.length > 30 && <small>先显示前 30 项，请补充类名缩小范围。</small>}
        </>
      )}
    </section>
  );
}

function DependencyColumn({
  title,
  dependencies,
  incoming,
  navigate,
}: {
  title: string;
  dependencies: Dependency[];
  incoming?: boolean;
  navigate: Navigate;
}) {
  const manifest = useEngineering();
  return (
    <div className="dependency-column">
      <h3>{title}</h3>
      {dependencies.length ? (
        dependencies
          .sort((a, b) => b.count - a.count)
          .map((dep) => {
            const module = manifest?.modules.find((m) => m.id === (incoming ? dep.from : dep.to));
            return (
              <details className="card dependency-item" key={`${dep.from}/${dep.to}`}>
                <summary>
                  <span>{module?.title ?? '其他模块'}</span>
                  <small>
                    {incoming ? '调用本模块' : '本模块调用'} · {dep.count.toLocaleString()} 处关联
                  </small>
                </summary>
                <button
                  className="text-button"
                  onClick={() =>
                    navigate({ kind: 'source-module', id: incoming ? dep.from : dep.to })
                  }
                >
                  进入模块 →
                </button>
                <p>
                  {Object.entries(dep.kinds)
                    .map(([kind, count]) => `${callKindLabel(kind)} ${count}`)
                    .join(' · ')}
                </p>
                {dep.samples.map((sample, i) => (
                  <div className="dependency-sample" key={i}>
                    <button onClick={() => navigate({ kind: 'source-method', id: sample.from })}>
                      {sample.caller.label}
                    </button>
                    <span>→</span>
                    <button onClick={() => navigate({ kind: 'source-method', id: sample.to! })}>
                      {sample.callee.label}
                    </button>
                    <button
                      className="text-button"
                      onClick={() =>
                        navigate({
                          kind: 'source-file',
                          id: sample.fileId,
                          start: sample.start,
                          end: sample.end,
                        })
                      }
                    >
                      调用位置 L{sample.start}
                    </button>
                  </div>
                ))}
              </details>
            );
          })
      ) : (
        <p>当前静态分析未发现跨模块关联。</p>
      )}
    </div>
  );
}

export function SourceModuleView({ id, navigate }: { id: string; navigate: Navigate }) {
  const manifest = useEngineering(),
    { data: module, error } = useResource<SourceModule>(
      manifest ? `${manifest.base}/modules/${id}.json` : undefined,
    );
  const [fileQuery, setFileQuery] = useState(''),
    [relationshipQuery, setRelationshipQuery] = useState(''),
    [relationPage, setRelationPage] = useState(0);
  useEffect(() => {
    setFileQuery('');
    setRelationshipQuery('');
    setRelationPage(0);
  }, [id]);
  if (!module || !manifest) return <Loading error={error} />;
  const relations = module.relationships.filter((r) =>
    `${r.caller} ${r.callee} ${r.note}`.toLowerCase().includes(relationshipQuery.toLowerCase()),
  );
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">功能说明 / 源码模块</span>
          <h1>{module.title}</h1>
          <p>{module.purpose}</p>
          <code>{module.name}</code>
        </div>
        <button
          className="button"
          onClick={() => {
            window.location.hash = 'modules';
          }}
        >
          ← 功能说明
        </button>
      </div>
      <section className="section card panel module-progress">
        <div className="panel-title">
          <h2>梳理与复核进度</h2>
          <span className="pill">{statusLabel(module.review.status)}</span>
        </div>
        <div className="engineering-metrics">
          <span>
            <b>
              {module.files.filter((f) => f.compileIncluded).length} / {module.files.length}
            </b>{' '}
            已纳入编译源码分析
          </span>
          <span>
            <b>
              {module.reviewedFiles} / {module.files.length}
            </b>{' '}
            复核记录已涉及文件
          </span>
          <span>
            <b>
              {module.currentEvidence} / {module.review.evidenceIds.length}
            </b>{' '}
            与当前源码一致的依据
          </span>
        </div>
        {manifest.projects
          .filter(
            (p) => module.files.some((f) => f.assemblies.includes(p.assembly)) && p.errors > 0,
          )
          .map((p) => (
            <p className="source-warning" key={p.assembly}>
              {p.assembly} 存在 {p.errors}{' '}
              个编译诊断错误，相关静态关系需要确认。可在导入页面阅读诊断详情。
            </p>
          ))}
        <details>
          <summary>查看详细复核记录</summary>
          <p className="review-summary">{module.review.summary}</p>
        </details>
        {!module.reviewCurrent && module.review.evidenceIds.length > 0 && (
          <p className="source-warning">部分复核依据或依赖需要重新确认，可展开详细记录核对。</p>
        )}
        <details>
          <summary>剩余待确认项（{module.review.gaps.length}）</summary>
          <ul>
            {module.review.gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
          {module.review.document && (
            <a
              className="text-button"
              href={`/archify/${module.review.document}`}
              target="_blank"
              rel="noreferrer"
            >
              阅读完整模块复核记录 ↗
            </a>
          )}
        </details>
        <small>
          复核记录日期：{module.review.reviewedAt ?? '未登记'} · 自动解析完成不等于业务复核完成。
        </small>
      </section>
      <section className="section">
        <div className="section-heading">
          <div>
            <h2>关联业务流程</h2>
            <p>以下流程节点具有该模块的源码依据。</p>
          </div>
        </div>
        <div className="card-actions">
          {module.workflows.map((w) => (
            <button
              className="button"
              key={w.id}
              onClick={() => navigate({ kind: 'graph', slug: w.id })}
            >
              {displayDiagramTitle(w.id, w.title)} →
            </button>
          ))}
          {!module.workflows.length && (
            <p>该模块尚未关联业务流程，职责和使用场景需要进一步整理。</p>
          )}
        </div>
      </section>
      <section className="section card panel">
        <h2>模块调用关系</h2>
        <p>
          箭头按调用方 →
          被调用方阅读。数量为源码中的关联位置；虚调用、委托和事件仍需要查看具体关系类型。
        </p>
        <div className="module-dependency-map">
          <DependencyColumn
            title="上游调用方 →"
            dependencies={module.incoming}
            incoming
            navigate={navigate}
          />
          <div className="dependency-center">
            <span>当前模块</span>
            <h3>{module.title}</h3>
            <small>{module.callCount.toLocaleString()} 处内部及外部关联</small>
          </div>
          <DependencyColumn title="→ 下游依赖" dependencies={module.outgoing} navigate={navigate} />
        </div>
      </section>
      {module.entryMethods?.length > 0 && (
        <section className="section card panel">
          <h2>自动识别的入口候选</h2>
          <p>
            根据 Main、Start、Run
            等方法名定位入口候选。进入方法可沿静态调用逐层阅读；业务触发条件仍需结合实际用途确认。
          </p>
          <div className="source-result-list">
            {module.entryMethods.map((method) => (
              <button
                key={method.id}
                onClick={() => navigate({ kind: 'source-method', id: method.id })}
              >
                <code>{method.label}</code>
                <small>{method.outgoingCount} 处调用与关联</small>
                <span>→</span>
              </button>
            ))}
          </div>
        </section>
      )}
      <section className="section card panel">
        <h2>业务调用与协作说明</h2>
        <p>这些是人工整理的代表链路，包含条件和异常语义。完整静态关系可从下方方法进入。</p>
        <input
          aria-label="筛选业务调用"
          placeholder="搜索调用方、目标或业务说明…"
          value={relationshipQuery}
          onChange={(e) => {
            setRelationshipQuery(e.target.value);
            setRelationPage(0);
          }}
        />
        <div className="business-relations">
          {relations.slice(relationPage * 15, (relationPage + 1) * 15).map((r, i) => (
            <details className="business-relation" key={`${relationPage}-${i}`}>
              <summary>
                <span className="pill">{callKindLabel(r.kind)}</span>
                <code>
                  {r.caller} → {r.callee}
                </code>
                {!r.current && <small>依据需确认</small>}
              </summary>
              <p>{r.note}</p>
              {r.evidence.map((e) => (
                <div key={e.id}>
                  <p>
                    <code>{e.method}</code>
                  </p>
                  <BindingLinks binding={e} navigate={navigate} />
                  <pre className="small-code">{e.code}</pre>
                </div>
              ))}
            </details>
          ))}
        </div>
        <Pager
          page={relationPage}
          pages={Math.ceil(relations.length / 15)}
          onChange={setRelationPage}
        />
      </section>
      <section className="section card panel">
        <h2>源码文件</h2>
        <input
          aria-label="筛选模块源码文件"
          placeholder="按文件路径筛选…"
          value={fileQuery}
          onChange={(e) => setFileQuery(e.target.value)}
        />
        <div className="source-result-list">
          {module.files
            .filter((f) => f.path.toLowerCase().includes(fileQuery.toLowerCase()))
            .map((f) => (
              <button key={f.id} onClick={() => navigate({ kind: 'source-file', id: f.id })}>
                <code>{f.path}</code>
                <small>
                  {f.compileIncluded ? `${f.declarationCount} 个声明` : '未纳入编译分析'}
                  {!f.current && ' · 源码变化'}
                </small>
                <span>→</span>
              </button>
            ))}
        </div>
      </section>
      <SourceSearch moduleId={id} navigate={navigate} />
      <VersionStamp />
    </>
  );
}

export function BindingLinks({
  binding,
  navigate,
}: {
  binding: EvidenceBinding;
  navigate: Navigate;
}) {
  const manifest = useEngineering(),
    module = manifest?.modules.find((m) => m.id === binding.moduleId);
  const projectFile = manifest?.files.find((file) => file.id === binding.fileId);
  if (!binding.fileId) return <span className="source-warning">源码未纳入当前索引</span>;
  return (
    <div className="card-actions binding-links">
      <button
        className="button small"
        onClick={() => navigate({ kind: 'source-module', id: binding.moduleId })}
      >
        {module?.title ?? '所属模块'} →
      </button>
      <button
        className="button small primary"
        onClick={() =>
          navigate({
            kind: 'source-file',
            id: binding.fileId,
            start: binding.start,
            end: binding.end,
          })
        }
      >
        完整源码 L{binding.start}–{binding.end} →
      </button>
      {projectFile?.path.replaceAll('\\', '/').startsWith('trunk/') && (
        <button
          className="button small"
          onClick={() =>
            navigate({
              kind: 'project-source',
              path: projectFile.path.replaceAll('\\', '/'),
              start: binding.start,
              end: binding.end,
            })
          }
        >
          项目中查看 →
        </button>
      )}
      {binding.symbolIds?.map((id) => (
        <BindingMethod key={id} id={id} navigate={navigate} />
      ))}
      {!binding.current && <span className="source-warning">依据需重新确认</span>}
    </div>
  );
}
function BindingMethod({ id, navigate }: { id: string; navigate: Navigate }) {
  const { symbol } = useSymbol(id);
  return (
    <button className="button small" onClick={() => navigate({ kind: 'source-method', id })}>
      方法调用：{symbol?.name ?? '读取中'} →
    </button>
  );
}
export function WorkflowSourceLinks({
  graphId,
  nodeId,
  navigate,
}: {
  graphId: string;
  nodeId: string;
  navigate: Navigate;
}) {
  const manifest = useEngineering(),
    bindings = manifest?.nodeBindings[`${graphId}/${nodeId}`];
  if (!manifest) return <Loading />;
  return (
    <section className="node-source-links">
      <h3>对应模块与源码</h3>
      <p>从该节点进入方法调用关系，或查看完整源码上下文。</p>
      {bindings?.length ? (
        bindings.map((b) => <BindingLinks key={b.id} binding={b} navigate={navigate} />)
      ) : (
        <p>当前源码索引尚未关联该流程。请结合源码搜索确认对应位置。</p>
      )}
    </section>
  );
}

function Pager({
  page,
  pages,
  onChange,
}: {
  page: number;
  pages: number;
  onChange: (page: number) => void;
}) {
  return (
    pages > 1 && (
      <div className="source-pager">
        <button className="button small" disabled={!page} onClick={() => onChange(page - 1)}>
          上一页
        </button>
        <span>
          {page + 1} / {pages}
        </span>
        <button
          className="button small"
          disabled={page + 1 >= pages}
          onClick={() => onChange(page + 1)}
        >
          下一页
        </button>
      </div>
    )
  );
}
function SymbolButton({ target, navigate }: { target: SymbolLink | null; navigate: Navigate }) {
  return target ? (
    <button
      className="symbol-link"
      onClick={() => navigate({ kind: 'source-method', id: target.id })}
    >
      <code>{target.label}</code>
      <small>
        {target.origin === 'source'
          ? '查看源码与调用 →'
          : target.sourceType
            ? '所属类型源码已导入；成员未独立索引 →'
            : '外部依赖：源码未导入 →'}
      </small>
    </button>
  ) : (
    <span className="source-warning">目标未解析</span>
  );
}
function CallList({
  title,
  calls,
  navigate,
}: {
  title: string;
  calls: CallSite[];
  navigate: Navigate;
}) {
  const [query, setQuery] = useState(''),
    [page, setPage] = useState(0);
  useEffect(() => {
    setQuery('');
    setPage(0);
  }, [calls]);
  const results = calls.filter((e) =>
    `${e.target?.label} ${callKindLabel(e.kind)} ${dispatchLabel(e.dispatch)}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  return (
    <section className="section card panel">
      <div className="panel-title">
        <h2>{title}</h2>
        <span className="pill">{calls.length} 处关联</span>
      </div>
      {calls.length > 0 && (
        <input
          aria-label={`筛选${title}`}
          placeholder="搜索目标或关系类型…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
        />
      )}
      <div className="call-list">
        {results.slice(page * 30, (page + 1) * 30).map((e, i) => (
          <article key={`${page}-${i}`} className="call-site">
            <div className="call-site-meta">
              <span className="pill">{callKindLabel(e.kind)}</span>
              <small>
                {dispatchLabel(e.dispatch)}
                {e.implicit && ' · 编译器隐式关联'}
                {!e.current && ' · 旧版本分析'}
              </small>
            </div>
            <SymbolButton target={e.target} navigate={navigate} />
            <button
              className="text-button"
              onClick={() =>
                navigate({ kind: 'source-file', id: e.fileId, start: e.start, end: e.end })
              }
            >
              查看关联位置 L{e.start}–{e.end} →
            </button>
          </article>
        ))}
      </div>
      {!calls.length && <p>当前索引未记录该方向的静态调用。</p>}
      <Pager page={page} pages={Math.ceil(results.length / 30)} onChange={setPage} />
    </section>
  );
}

export function SourceMethodView({ id, navigate }: { id: string; navigate: Navigate }) {
  const { symbol, error } = useSymbol(id);
  const manifest = useEngineering();
  if (!symbol || !manifest) return <Loading error={error} />;
  const module = manifest.modules.find((m) => m.id === symbol.moduleId);
  return (
    <>
      <div className="page-header source-method-header">
        <div>
          <span className="eyebrow">方法与调用关系</span>
          <h1>{symbol.name}</h1>
          <code>{symbol.label}</code>
          <p>
            {symbol.assembly} · {symbol.kind} {symbol.methodKind ? `· ${symbol.methodKind}` : ''}
          </p>
        </div>
        {module && (
          <button
            className="button"
            onClick={() => navigate({ kind: 'source-module', id: module.id })}
          >
            ← {module.title}
          </button>
        )}
      </div>
      {manifest.projects.find((p) => p.assembly === symbol.assembly)?.errors ? (
        <p className="source-warning">
          所属工程存在编译错误，请结合源码工程的诊断信息确认依赖与解析范围。
        </p>
      ) : null}
      {!symbol.current && (
        <p className="source-warning">调用分析对应旧源码版本，请更新索引后再确认这些关系。</p>
      )}
      {symbol.origin === 'metadata' ? (
        <section className="card panel">
          <h2>{symbol.sourceType ? '所属源码类型' : '外部依赖'}</h2>
          {symbol.sourceType ? (
            <>
              <p>
                该构造成员没有独立的源码记录。已关联到相同程序集中的源码类型，可以继续阅读类型声明和完整文件。
              </p>
              <SymbolButton
                target={{ ...symbol.sourceType, origin: 'source' }}
                navigate={navigate}
              />
            </>
          ) : (
            <p>这是静态分析解析到的依赖符号。当前没有导入它的源文件，可以查看本项目的调用位置。</p>
          )}
        </section>
      ) : (
        <section className="section card panel">
          <h2>方法源码与上下文</h2>
          {symbol.declarations.length ? (
            symbol.declarations.map((d, i) => (
              <div key={i}>
                <p>
                  <code>
                    {manifest.files.find((f) => f.id === d.fileId)?.path}:{d.start}–{d.end}
                  </code>
                </p>
                <button
                  className="button primary"
                  onClick={() =>
                    navigate({ kind: 'source-file', id: d.fileId, start: d.start, end: d.end })
                  }
                >
                  阅读完整源码与上下文 →
                </button>
                <SourceExcerpt fileId={d.fileId} start={d.start} end={d.end} />
              </div>
            ))
          ) : (
            <>
              <p>编译器生成的成员，没有独立的方法声明。请从文件或调用位置查看上下文。</p>
              {symbol.fileId && (
                <button
                  className="button primary"
                  onClick={() => navigate({ kind: 'source-file', id: symbol.fileId! })}
                >
                  阅读所属完整源码文件 →
                </button>
              )}
            </>
          )}
        </section>
      )}
      {symbol.origin === 'source' && symbol.declarations[0] && (
        <div className="card-actions">
          <button
            className="button"
            onClick={() =>
              navigate({
                kind: 'chat',
                method: symbol.id,
                sourceFile: symbol.declarations[0].fileId,
                start: symbol.declarations[0].start,
                end: symbol.declarations[0].end,
              })
            }
          >
            讨论这个方法 →
          </button>
        </div>
      )}
      <div className="method-call-columns">
        <CallList key={`in-${id}`} title="谁调用这里" calls={symbol.incoming} navigate={navigate} />
        <CallList
          key={`out-${id}`}
          title="这里调用谁"
          calls={symbol.outgoing}
          navigate={navigate}
        />
      </div>
      {symbol.relations.length > 0 && (
        <section className="section card panel">
          <h2>继承、接口与重写关系</h2>
          {symbol.relations.map((r, i) => (
            <div className="call-site" key={i}>
              <small>
                {r.direction === 'incoming' ? '来自' : '指向'} · {r.kind}
              </small>
              <SymbolButton target={r.target} navigate={navigate} />
            </div>
          ))}
        </section>
      )}
      <VersionStamp />
    </>
  );
}
function SourceExcerpt({ fileId, start, end }: { fileId: string; start: number; end: number }) {
  const manifest = useEngineering(),
    { data } = useResource<SourceFile>(
      manifest ? `${manifest.base}/files/${fileId}.json` : undefined,
    );
  return (
    data?.code !== undefined && (
      <pre className="small-code">
        {data.code
          .split(/\r\n|\r|\n/)
          .slice(start - 1, Math.min(end, start + 59))
          .map((line, i) => `${start + i}: ${line}`)
          .join('\n')}
        {end - start >= 60 ? '\n…打开完整源码继续阅读' : ''}
      </pre>
    )
  );
}

export function SourceFileView({
  id,
  start = 1,
  end = start,
  navigate,
}: {
  id: string;
  start?: number;
  end?: number;
  navigate: Navigate;
}) {
  const manifest = useEngineering(),
    { data: file, error } = useResource<SourceFile>(
      manifest ? `${manifest.base}/files/${id}.json` : undefined,
    );
  const [page, setPage] = useState(Math.floor((start - 1) / 200)),
    [focusLine, setFocusLine] = useState(start),
    [lineInput, setLineInput] = useState(String(start)),
    [query, setQuery] = useState(''),
    [methodQuery, setMethodQuery] = useState('');
  useEffect(() => {
    setPage(Math.floor((start - 1) / 200));
    setFocusLine(start);
    setLineInput(String(start));
    setQuery('');
    setMethodQuery('');
  }, [id, start]);
  const lines = useMemo(() => file?.code?.split(/\r\n|\r|\n/) ?? [], [file]);
  const codePane = useRef<HTMLDivElement>(null);
  const scrollToLine = (line: number) => {
    const pane = codePane.current,
      row = pane?.querySelector(`[data-line="${line}"]`);
    if (pane && row)
      pane.scrollTop += row.getBoundingClientRect().top - pane.getBoundingClientRect().top - 80;
  };
  useEffect(() => {
    scrollToLine(focusLine);
  }, [file, focusLine, page]);
  useEffect(() => {
    if (file && lines.length) setPage((page) => Math.min(page, Math.ceil(lines.length / 200) - 1));
  }, [file, lines.length]);
  const matches = useMemo(
    () =>
      query
        ? lines.flatMap((line, i) =>
            line.toLowerCase().includes(query.toLowerCase()) ? [i + 1] : [],
          )
        : [],
    [lines, query],
  );
  if (!file || !manifest) return <Loading error={error} />;
  const module = manifest.modules.find((m) => m.id === file.moduleId);
  const declarations =
    file.declarations?.filter((d) =>
      `${d.label} ${d.name}`.toLowerCase().includes(methodQuery.toLowerCase()),
    ) ?? [];
  const jump = (line: number) => {
    if (Number.isInteger(line) && line >= 1 && line <= lines.length) {
      setPage(Math.floor((line - 1) / 200));
      setFocusLine(line);
      setLineInput(String(line));
      scrollToLine(line);
    }
  };
  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">完整源码</span>
          <h1>{file.path.split('/').pop()}</h1>
          <p>
            <code>{file.path}</code>
          </p>
          <small>
            {file.encoding} · {file.lineCount} 行 ·{' '}
            {file.compileIncluded ? '纳入编译分析' : '未纳入编译分析'} · SHA-256 {file.sha256}
          </small>
        </div>
        <button
          className="button"
          onClick={() => navigate({ kind: 'source-module', id: file.moduleId })}
        >
          ← {module?.title ?? '所属模块'}
        </button>
      </div>
      {!file.current && (
        <p className="source-warning">文件已变化，旧复核记录和调用位置需要重新确认。</p>
      )}
      {!file.exists && <p role="alert">当前工作区缺少该文件；下方保留的是旧版源码快照。</p>}
      {file.exists && (
        <div className="card-actions">
          <button
            className="button primary"
            onClick={() =>
              navigate({
                kind: 'project-source',
                path: file.path,
                start: focusLine,
                end: Math.max(end, focusLine),
              })
            }
          >
            在当前源码区查看 →
          </button>
          <button
            className="button"
            onClick={() =>
              navigate({
                kind: 'chat',
                sourceFile: file.id,
                start: focusLine,
                end: Math.max(end, Math.min(focusLine + 59, file.lineCount)),
              })
            }
          >
            结合这段源码提问 →
          </button>
        </div>
      )}
      <div className="source-reader-layout">
        <aside className="card panel source-symbols">
          <h2>文件中的类型与方法</h2>
          <input
            aria-label="筛选文件声明"
            placeholder="搜索声明…"
            value={methodQuery}
            onChange={(e) => setMethodQuery(e.target.value)}
          />
          <p>{declarations.length} 个声明</p>
          {declarations.map((d, i) => (
            <button
              key={`${d.symbolId}-${i}`}
              onClick={() => navigate({ kind: 'source-method', id: d.symbolId })}
            >
              <code>{d.label}</code>
              <small>
                {d.syntaxKind} · L{d.start}–{d.end}
              </small>
            </button>
          ))}
          {!declarations.length && <p>此文件没有已索引的声明。</p>}
        </aside>
        <section className="card source-code-panel">
          <div className="source-toolbar">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                jump(Number(lineInput));
              }}
            >
              <label>
                跳转行
                <input
                  aria-label="跳转源码行"
                  type="number"
                  min="1"
                  max={lines.length}
                  value={lineInput}
                  onChange={(e) => setLineInput(e.target.value)}
                />
              </label>
              <button className="button small">跳转</button>
            </form>
            <input
              aria-label="搜索文件内容"
              placeholder="搜索文件内容…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button
              className="button small"
              onClick={() => {
                const blob = new Blob([file.code ?? ''], { type: 'text/plain;charset=utf-8' }),
                  url = URL.createObjectURL(blob),
                  link = document.createElement('a');
                link.href = url;
                link.download = file.path.split('/').pop()!;
                link.click();
                URL.revokeObjectURL(url);
              }}
            >
              下载完整源码（UTF-8）
            </button>
          </div>
          {query && (
            <div className="source-matches">
              <span>{matches.length} 处匹配</span>
              {matches.slice(0, 100).map((line) => (
                <button className="text-button" key={line} onClick={() => jump(line)}>
                  L{line}
                </button>
              ))}
            </div>
          )}
          <div className="source-code" aria-label="源码内容" ref={codePane}>
            {lines.slice(page * 200, (page + 1) * 200).map((line, i) => {
              const n = page * 200 + i + 1;
              return (
                <div
                  key={n}
                  data-line={n}
                  className={`code-line ${n >= start && n <= end ? 'selected-source' : ''} ${matches.includes(n) ? 'matched-source' : ''}`}
                >
                  <a href={`#source-file/${id}?start=${n}&end=${n}`} aria-label={`定位第 ${n} 行`}>
                    {n}
                  </a>
                  <code>{line || ' '}</code>
                </div>
              );
            })}
          </div>
          <p className="source-range">
            当前显示 L{page * 200 + 1}–{Math.min((page + 1) * 200, lines.length)} · 关联范围 L
            {start}–{end} · 分页可阅读整个文件
          </p>
          <Pager page={page} pages={Math.ceil(lines.length / 200)} onChange={setPage} />
        </section>
      </div>
      <VersionStamp />
    </>
  );
}
