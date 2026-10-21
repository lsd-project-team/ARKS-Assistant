import { useEffect, useRef, useState } from 'react';
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, Download, RefreshCw, Timer, Upload } from 'lucide-react';
import { api } from '../../app/api/client';
import { useWorkspace } from '../../app/state/store';
import type { ProjectList } from '../../shared/types/api';
import { Button, ErrorText } from '../../shared/ui/ui';
import { timingClient } from './client';
import { timingHash, useTimingNavigation } from './navigation';
import { TimingDetail } from './TimingDetail';
import { TimingStatistics } from './TimingStatistics';
import { TimingSamples } from './TimingSamples';
import './action-timing.css';

export default function ActionTimingPage() {
  const navigation = useTimingNavigation();
  const currentProject = useWorkspace((state) => state.projectId);
  const scope = navigation.projectId || currentProject || 'independent';
  const [action, setAction] = useState('');
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const [detail, setDetail] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState('');
  const upload = useRef<HTMLInputElement>(null);
  const activeScope = useRef(scope);
  activeScope.current = scope;
  const cache = useQueryClient();
  const client = timingClient(scope);
  const projects = useQuery({
    queryKey: ['projects', 'timing'],
    queryFn: ({ signal }) => api<ProjectList>('/projects', { signal }),
  });
  const catalog = useQuery({
    queryKey: ['action-timing', scope, 'catalog'],
    queryFn: ({ signal }) => client.catalog(signal),
  });
  const runs = useInfiniteQuery({
    queryKey: ['action-timing', scope, 'runs'],
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) => client.runs(pageParam, signal),
    getNextPageParam: (last, pages) =>
      pages.flatMap((page) => page.items).length < last.total
        ? pages.flatMap((page) => page.items).length
        : undefined,
  });
  const runRows = runs.data?.pages.flatMap((page) => page.items) || [];
  const run = navigation.runId || runRows[0]?.id || '';
  const summary = useQuery({
    queryKey: ['action-timing', scope, run, 'summary'],
    queryFn: ({ signal }) => client.summary(run, signal),
    enabled: !!run,
  });
  const samples = useQuery({
    queryKey: ['action-timing', scope, run, 'events', action, status, offset],
    queryFn: ({ signal }) => client.events(run, action, status, offset, signal),
    enabled: !!run,
  });
  useEffect(() => {
    setAction('');
    setStatus('');
    setOffset(0);
    setDetail('');
    setError(undefined);
    setNotice('');
  }, [scope]);
  useEffect(() => {
    setOffset(0);
    setDetail('');
  }, [run, action, status]);
  async function importFile(file?: File) {
    if (!file) return;
    setError(undefined);
    setNotice('');
    if (file.size > 16 * 1024 * 1024) {
      setError(new Error('数据包超过16MiB，请缩小采集批次'));
      return;
    }
    setBusy(true);
    try {
      const result = await client.import(file);
      await cache.invalidateQueries({ queryKey: ['action-timing', scope] });
      if (activeScope.current !== scope) return;
      location.hash = timingHash(scope, result.run.id);
      setNotice(
        result.duplicate
          ? '此批次已导入，未重复计数。'
          : `已导入 ${result.imported} 条动作及阶段记录。`,
      );
    } catch (reason) {
      if (activeScope.current === scope) setError(reason);
    } finally {
      setBusy(false);
    }
  }
  async function download(format: 'json' | 'csv') {
    setError(undefined);
    try {
      await client.download(run, format);
    } catch (reason) {
      setError(reason);
    }
  }
  const data = summary.data;
  const failed = (data?.statuses.failed || 0) + (data?.statuses.aborted || 0);
  return (
    <section className="action-timing-workspace" aria-label="动作耗时统计">
      <div className="timing-content">
        <header className="timing-heading">
          <div>
            <span className="timing-eyebrow">
              <Activity size={14} /> ZX2200 · 动作分析
            </span>
            <h1>动作耗时统计</h1>
            <p>沿用源码现有空跑流程，查看每次动作实际经过的时间。</p>
          </div>
          <Button
            className="primary"
            disabled={busy || projects.isPending}
            onClick={() => upload.current?.click()}
          >
            <Upload size={16} />
            {busy ? '正在导入…' : '导入采集数据'}
          </Button>
          <input
            ref={upload}
            type="file"
            accept=".json,.zip"
            hidden
            aria-label="选择耗时采集数据包"
            onChange={(event) => {
              void importFile(event.target.files?.[0]);
              event.target.value = '';
            }}
          />
        </header>
        <div className="timing-filters">
          <label>
            所属项目
            <select
              aria-label="统计所属项目"
              value={scope}
              disabled={busy}
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
          <label className="timing-run-select">
            运行批次
            <select
              aria-label="运行批次"
              value={run}
              disabled={busy || !run}
              onChange={(event) => {
                location.hash = timingHash(scope, event.target.value);
              }}
            >
              {!run && <option value="">尚无采集批次</option>}
              {run && !runRows.some((row) => row.id === run) && (
                <option value={run}>{data?.run.recipe_name || run}</option>
              )}
              {runRows.map((row) => (
                <option key={row.id} value={row.id}>
                  {new Date(row.started_at).toLocaleString()} · {row.recipe_name || '未命名配方'}
                  {row.source_kind === 'collector_test' ? ' · 采集器测试' : ''}
                </option>
              ))}
            </select>
          </label>
          <Button
            title="刷新统计"
            onClick={() => void cache.invalidateQueries({ queryKey: ['action-timing', scope] })}
          >
            <RefreshCw size={15} />
            刷新
          </Button>
          {runs.hasNextPage && (
            <Button disabled={runs.isFetchingNextPage} onClick={() => void runs.fetchNextPage()}>
              更多批次
            </Button>
          )}
        </div>
        <ErrorText
          error={
            error || projects.error || catalog.error || runs.error || summary.error || samples.error
          }
        />
        {notice && (
          <p role="status" className="timing-notice">
            {notice}
          </p>
        )}
        {!run && !runs.isPending && (
          <div className="timing-empty">
            <Timer size={34} />
            <h2>首批五个动作已接入</h2>
            <p>S1 焊点定位、S1 点胶、S2 取片、上视纠偏、固晶。</p>
            <p>导入空跑采集的 JSON 或 ZIP 数据包后，查看动作分布和内部阶段。</p>
            <Button onClick={() => upload.current?.click()}>选择采集数据</Button>
          </div>
        )}
        {(runs.isPending || (!!run && summary.isPending)) && <p role="status">正在读取耗时记录…</p>}
        {data && (
          <>
            <div className="timing-run-meta">
              <span className="timing-badge">
                {data.run.source_kind === 'collector_test' ? '采集器测试数据' : '原有空跑采集'}
              </span>
              <span>
                {data.run.mode} · {data.run.recipe_name || '未命名配方'}
              </span>
              <span title={data.run.source_revision}>
                源码 {data.run.source_revision.slice(0, 12)}
              </span>
              <span>
                {data.run.state === 'completed'
                  ? '已结束'
                  : data.run.state === 'stopped'
                    ? '已停止'
                    : '记录不完整'}
              </span>
            </div>
            {data.run.source_kind === 'collector_test' && (
              <p className="timing-notice">
                此批次用于验证采集和数据通路，数值不代表设备动作耗时。
              </p>
            )}
            {!data.data_complete && (
              <p className="timing-notice warning">
                采集不完整（丢失 {data.run.dropped_events}{' '}
                条记录或存在未完成调用），保留原始记录，暂不计算成功耗时分布。
              </p>
            )}
            <div className="timing-metrics">
              {[
                ['有效动作覆盖', `${data.covered_actions} / 5`],
                ['动作调用', data.action_count],
                ['失败 / 中止', failed],
                ['重试 / 跳过', `${data.statuses.retry || 0} / ${data.statuses.skipped || 0}`],
              ].map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            <div className="timing-section-heading">
              <h2>
                动作分布 <small>ms</small>
              </h2>
              <div>
                <Button onClick={() => void download('csv')}>
                  <Download size={14} />
                  导出统计
                </Button>
                <Button onClick={() => void download('json')}>导出原始记录</Button>
              </div>
            </div>
            <p className="timing-caption">
              仅完整成功调用参与均值和分位数；分支分别计算。调用耗时包含等待和暂停，父子及并行时间不叠加为产品节拍。
            </p>
            <TimingStatistics
              rows={data.rows}
              onSelect={(code) => {
                setAction(code);
                setOffset(0);
              }}
            />
            <TimingSamples
              actions={catalog.data?.actions}
              samples={samples.data}
              action={action}
              status={status}
              offset={offset}
              setAction={setAction}
              setStatus={setStatus}
              setOffset={setOffset}
              setDetail={setDetail}
            />
          </>
        )}
        {detail && run && (
          <TimingDetail scope={scope} run={run} event={detail} onClose={() => setDetail('')} />
        )}
      </div>
    </section>
  );
}
