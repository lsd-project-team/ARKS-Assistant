import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, Code2, Download, RefreshCw, Search } from 'lucide-react';
import { api } from '../../app/api/client';
import { useWorkspace } from '../../app/state/store';
import type { ProjectList } from '../../shared/types/api';
import { Button, ErrorText } from '../../shared/ui/ui';
import { timingHash, useTimingNavigation } from './navigation';
import { knownDelay, sourceTimingClient } from './source-client';
import { SourceTimingDetail } from './SourceTimingDetail';
import './action-timing.css';
import './source-timing.css';

const kinds = [
  ['node', '动作节点'],
  ['controller', '控制器子动作'],
  ['workflow', '换料 / 放行'],
  ['placeholder', '占位节点'],
  ['', '全部入口'],
];

export default function ActionTimingPage() {
  const navigation = useTimingNavigation();
  const currentProject = useWorkspace((state) => state.projectId);
  const scope = navigation.projectId || currentProject || 'independent';
  const [kind, setKind] = useState('node');
  const [group, setGroup] = useState('');
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState('');
  const [error, setError] = useState<unknown>();
  const client = sourceTimingClient(scope);
  const cache = useQueryClient();
  const projects = useQuery({
    queryKey: ['projects', 'source-timing'],
    queryFn: ({ signal }) => api<ProjectList>('/projects', { signal }),
  });
  const report = useQuery({
    queryKey: ['source-timing', scope],
    queryFn: ({ signal }) => client.report(signal),
    staleTime: 0,
  });
  const data = report.data;
  useEffect(() => {
    setSelected('');
    setOffset(0);
    setError(undefined);
  }, [scope, data?.source_revision]);
  useEffect(() => {
    setOffset(0);
  }, [kind, group, search]);
  const rows = data?.rows || [];
  const filtered = rows.filter(
    (row) =>
      (!kind || row.kind === kind) &&
      (!group || row.group === group) &&
      `${row.name} ${row.class_name} ${row.method} ${row.formula}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const nodes = rows.filter((row) => row.kind === 'node');
  async function download() {
    setError(undefined);
    try {
      await client.download();
    } catch (reason) {
      setError(reason);
    }
  }
  return (
    <section className="action-timing-workspace source-timing-workspace" aria-label="动作耗时统计">
      <div className="timing-content">
        <header className="timing-heading">
          <div>
            <span className="timing-eyebrow">
              <Activity size={14} /> ZX2200 · 源码模拟分析
            </span>
            <h1>动作耗时统计</h1>
            <p>从源码现有模拟分支、延时和运动参数直接计算，打开即可查看。</p>
          </div>
          <Button disabled={!rows.length} onClick={() => void download()}>
            <Download size={15} /> 导出分析
          </Button>
        </header>
        <div className="timing-filters">
          <label>
            所属项目
            <select
              aria-label="统计所属项目"
              value={scope}
              onChange={(event) => {
                location.hash = timingHash(event.target.value);
              }}
            >
              <option value="independent">独立工作区</option>
              {projects.data?.projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            模块
            <select
              aria-label="筛选源码模块"
              value={group}
              onChange={(event) => setGroup(event.target.value)}
            >
              <option value="">全部模块</option>
              {[...new Set(rows.map((row) => row.group))].map((label) => (
                <option key={label}>{label}</option>
              ))}
            </select>
          </label>
          <label className="timing-source-search">
            <span>查找动作</span>
            <span>
              <Search size={14} />
              <input
                aria-label="查找源码动作"
                placeholder="动作名、方法名、耗时表达式"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </span>
          </label>
          <Button
            disabled={report.isFetching}
            onClick={() => void cache.invalidateQueries({ queryKey: ['source-timing', scope] })}
          >
            <RefreshCw size={14} /> {report.isFetching ? '正在分析…' : '重新核对源码'}
          </Button>
        </div>
        <ErrorText error={error || projects.error || report.error} />
        {report.isPending && (
          <p role="status" className="timing-notice">
            正在读取源码，计算动作的配置延时和调用分支…
          </p>
        )}
        {data && (
          <>
            <div className="timing-run-meta">
              <span className="timing-badge">源码计算结果</span>
              <span>DryCycle 模拟分支</span>
              <span>{data.source_files} 个源码文件</span>
              <span title={data.source_revision}>版本 {data.source_revision.slice(0, 12)}</span>
            </div>
            <div className="source-explanation">
              <Code2 size={19} />
              <div>
                <strong>按源码默认参数计算，可算部分直接给数值。</strong>
                <p>
                  “可算配置延时”是动作的一部分。运动、信号和循环次数未确定时保留计算式；超时上限单列。结果不代表现场实测。
                </p>
              </div>
            </div>
            <div className="timing-metrics">
              {[
                ['动作节点', nodes.length],
                ['执行 / 子动作入口', rows.length],
                [
                  '有可算延时的动作节点',
                  nodes.filter((row) => (row.known_delay_max_ms || row.known_delay_min_ms || 0) > 0)
                    .length,
                ],
                ['分析方式', '直接读源码'],
              ].map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            <nav className="source-kind-tabs" aria-label="源码动作分类">
              {kinds.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  className={kind === value ? 'active' : ''}
                  aria-pressed={kind === value}
                  onClick={() => setKind(value)}
                >
                  {label}
                  <span>{rows.filter((row) => !value || row.kind === value).length}</span>
                </button>
              ))}
            </nav>
            <p className="timing-caption">
              动作与控制器子动作分层列出；调用点数量含不同分支，不表示执行次数。点击“计算依据”查看参数初值、分支和源码行号。
            </p>
            <div className="timing-table-wrap">
              <table className="timing-table source-action-table">
                <thead>
                  <tr>
                    <th>动作 / 耗时表达式</th>
                    <th>可算配置延时</th>
                    <th>待定部分</th>
                    <th>依据</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(offset, offset + 25).map((row) => (
                    <tr key={row.id}>
                      <td>
                        <button className="source-action-name" onClick={() => setSelected(row.id)}>
                          {row.name}
                        </button>
                        <small>
                          {row.class_name} · {row.group}
                        </small>
                        <p className="source-formula">{row.formula}</p>
                      </td>
                      <td>
                        <strong>{knownDelay(row)}</strong>
                        <small>{row.branch}</small>
                      </td>
                      <td>
                        <span className={row.total_ms == null ? 'source-pending' : 'source-known'}>
                          {row.total_ms == null ? '总耗时未定' : '配置模型可算'}
                        </span>
                        <small>
                          {row.motion_count ? `运动点 ${row.motion_count} · ` : ''}等待点{' '}
                          {row.wait_count}
                        </small>
                        {row.truncated && <small>调用链未完整展开</small>}
                      </td>
                      <td>
                        <Button onClick={() => setSelected(row.id)}>计算依据</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!filtered.length && (
                <div className="timing-empty">
                  <Code2 size={28} />
                  <p>
                    {rows.length
                      ? '当前筛选条件下没有动作。'
                      : '当前项目没有发现 ZX2200 动作，请选择关联了 ZX2200 源码的项目。'}
                  </p>
                </div>
              )}
            </div>
            <div className="timing-pagination">
              <span>
                共 {filtered.length} 个入口 · 第 {Math.floor(offset / 25) + 1} 页
              </span>
              <Button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 25))}>
                上一页
              </Button>
              <Button
                disabled={offset + 25 >= filtered.length}
                onClick={() => setOffset(offset + 25)}
              >
                下一页
              </Button>
            </div>
            <details className="source-scope">
              <summary>计算口径与覆盖范围</summary>
              <p>{data.scope}</p>
              <ul>
                {data.assumptions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {data.notes.length > 0 && <p>{data.notes.join('\n')}</p>}
            </details>
          </>
        )}
        {selected && (
          <SourceTimingDetail
            scope={scope}
            identifier={selected}
            revision={data?.source_revision || ''}
            onClose={() => setSelected('')}
          />
        )}
      </div>
    </section>
  );
}
