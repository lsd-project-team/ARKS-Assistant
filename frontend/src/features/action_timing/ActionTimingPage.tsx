import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, RefreshCw, Search } from 'lucide-react';
import { api } from '../../app/api/client';
import { useWorkspace } from '../../app/state/store';
import type { ProjectList } from '../../shared/types/api';
import { Button, ErrorText } from '../../shared/ui/ui';
import { timingHash, useTimingNavigation } from './navigation';
import { actionPresentation, filterActions } from './presentation';
import { sourceTimingClient } from './source-client';
import { SourceTimingDetail } from './SourceTimingDetail';
import './action-timing.css';
import './source-timing.css';

const pageSize = 10;

export default function ActionTimingPage() {
  const navigation = useTimingNavigation();
  const currentProject = useWorkspace((state) => state.projectId);
  const scope = navigation.projectId || currentProject || 'independent';
  const [auxiliary, setAuxiliary] = useState(false);
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
    setGroup('');
    setError(undefined);
  }, [scope, data?.source_revision]);
  useEffect(() => {
    setOffset(0);
  }, [auxiliary, group, search]);
  const rows = data?.rows || [];
  const filtered = filterActions(rows, { auxiliary, group, search });
  const groups = [
    ...new Set(rows.filter((row) => (row.kind !== 'node') === auxiliary).map((row) => row.group)),
  ];
  // 刷新或切换筛选后，旧页码不能让仍有结果的列表显示为空。
  const pageOffset = Math.min(
    offset,
    Math.max(0, Math.ceil(filtered.length / pageSize) - 1) * pageSize,
  );

  function download() {
    setError(undefined);
    try {
      client.download(filtered);
    } catch (reason) {
      setError(reason);
    }
  }
  return (
    <section className="action-timing-workspace source-timing-workspace" aria-label="动作耗时统计">
      <div className="timing-content">
        <header className="timing-heading">
          <div>
            <h1>动作耗时统计</h1>
            <p>
              {auxiliary ? '查看换料、放行及控制器子动作的模拟耗时' : '查看各工位动作的模拟耗时'}
            </p>
          </div>
        </header>
        <div className="source-timing-toolbar">
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
          <select
            aria-label="筛选工位"
            value={group}
            onChange={(event) => setGroup(event.target.value)}
          >
            <option value="">全部工位</option>
            {groups.map((label) => (
              <option key={label}>{label}</option>
            ))}
          </select>
          <label className="timing-source-search">
            <Search size={16} aria-hidden="true" />
            <input
              aria-label="搜索动作名称"
              placeholder="搜索动作名称"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <Button
            className="source-refresh-button"
            aria-label="刷新耗时"
            title="刷新耗时"
            disabled={report.isFetching}
            onClick={() => void cache.invalidateQueries({ queryKey: ['source-timing', scope] })}
          >
            <RefreshCw size={16} className={report.isFetching ? 'source-refreshing' : ''} />
          </Button>
          <Button className="source-export-button" disabled={!filtered.length} onClick={download}>
            <Download size={16} /> 导出表格
          </Button>
        </div>
        <ErrorText error={error || projects.error || report.error} />
        {report.isPending && (
          <p role="status" className="timing-notice">
            正在计算动作耗时…
          </p>
        )}
        {data && (
          <>
            <div className="timing-table-wrap">
              <table
                className="timing-table source-action-table"
                aria-label={auxiliary ? '辅助动作耗时表' : '动作耗时表'}
              >
                <thead>
                  <tr>
                    <th scope="col">工位</th>
                    <th scope="col">动作名称</th>
                    <th scope="col">动作耗时</th>
                    <th scope="col">说明</th>
                    <th scope="col">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(pageOffset, pageOffset + pageSize).map((row) => {
                    const view = actionPresentation(row);
                    return (
                      <tr key={row.id}>
                        <td>{view.station}</td>
                        <td className="source-action-name">{view.name}</td>
                        <td>
                          <strong
                            className={
                              view.hasDuration ? 'source-action-duration' : 'source-action-pending'
                            }
                          >
                            {view.duration}
                          </strong>
                          {view.remainder && (
                            <small className="source-action-remainder">{view.remainder}</small>
                          )}
                        </td>
                        <td className="source-action-note">{view.note}</td>
                        <td>
                          <button
                            type="button"
                            className="source-detail-link"
                            onClick={() => setSelected(row.id)}
                          >
                            查看详情
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {!filtered.length && (
                <div className="timing-empty">
                  <p>
                    {rows.length
                      ? '没有找到符合条件的动作。'
                      : '当前项目没有可分析的动作，请选择关联 ZX2200 源码的项目。'}
                  </p>
                </div>
              )}
            </div>
            <div className="timing-pagination">
              <span>共 {filtered.length} 个动作</span>
              {filtered.length > pageSize && (
                <>
                  <span className="source-page-number">
                    第 {Math.floor(pageOffset / pageSize) + 1} /{' '}
                    {Math.ceil(filtered.length / pageSize)} 页
                  </span>
                  <Button
                    disabled={!pageOffset}
                    onClick={() => setOffset(Math.max(0, pageOffset - pageSize))}
                  >
                    上一页
                  </Button>
                  <Button
                    disabled={pageOffset + pageSize >= filtered.length}
                    onClick={() => setOffset(pageOffset + pageSize)}
                  >
                    下一页
                  </Button>
                </>
              )}
            </div>
            <footer className="source-timing-footer">
              <p>耗时根据源码模拟逻辑计算，详情中可查看计算依据。</p>
              <button
                type="button"
                className="source-detail-link"
                onClick={() => {
                  setAuxiliary(!auxiliary);
                  setGroup('');
                  setSearch('');
                }}
              >
                {auxiliary ? '返回主要动作' : '查看辅助动作'}
              </button>
            </footer>
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
