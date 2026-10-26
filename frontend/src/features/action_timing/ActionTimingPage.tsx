import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Download,
  FolderOpen,
  Plus,
  Search,
  Upload,
} from 'lucide-react';
import { api } from '../../app/api/client';
import { useWorkspace } from '../../app/state/store';
import type { ProjectList } from '../../shared/types/api';
import { Button, ErrorText } from '../../shared/ui/ui';
import { Select } from '../../shared/ui/Select';
import { timingHash, useTimingNavigation } from './navigation';
import { ledgerClient } from './ledger-client';
import { durationText } from './ledger-format';
import type { ActionSort, DurationStatus, LedgerFilters, TimingAction } from './ledger-types';
import { ActionEditor, DeleteActionDialog } from './ActionEditor';
import { CategoryManager } from './CategoryManager';
import { ImportDialog } from './ImportDialog';
import { ExportDialog } from './ExportDialog';
import './ledger.css';

export default function ActionTimingPage() {
  const navigation = useTimingNavigation();
  const currentProject = useWorkspace((state) => state.projectId);
  const scope = navigation.projectId || currentProject || 'independent';
  // 项目切换时销毁旧项目的表单和请求，避免草稿或预览跨项目沿用。
  return <ActionLedger key={scope} scope={scope} />;
}

function ActionLedger({ scope }: { scope: string }) {
  const cache = useQueryClient();
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<DurationStatus>('all');
  const [sort, setSort] = useState<ActionSort>('name');
  const [offset, setOffset] = useState(0);
  const [dialog, setDialog] = useState<'categories' | 'action' | 'import' | 'export' | ''>('');
  const [editing, setEditing] = useState<TimingAction | null>(null);
  const [deleting, setDeleting] = useState<TimingAction | null>(null);
  const [message, setMessage] = useState('');
  const filters: LedgerFilters = { category_id: category, search, duration_status: status, sort };
  const SortIcon =
    sort === 'duration_desc' ? ArrowDown : sort === 'duration_asc' ? ArrowUp : ArrowUpDown;
  const projects = useQuery({
    queryKey: ['projects', 'action-ledger'],
    queryFn: ({ signal }) => api<ProjectList>('/projects', { signal }),
  });
  const report = useQuery({
    queryKey: ['action-ledger', scope, filters, offset],
    queryFn: ({ signal }) => ledgerClient(scope).list(filters, offset, signal),
  });
  const data = report.data;
  const categories = data?.categories || [];
  const writable = !!data?.writable;
  useEffect(() => {
    if (!data) return;
    if (
      category &&
      category !== 'uncategorized' &&
      !data.categories.some((item) => item.id === category)
    ) {
      setCategory('');
      setOffset(0);
    }
    if (offset && offset >= data.total) setOffset(Math.max(0, Math.ceil(data.total / 20) - 1) * 20);
  }, [data, category, offset]);
  function chooseCategory(value: string) {
    setCategory(value);
    setOffset(0);
  }
  async function saved(value: string) {
    await cache.invalidateQueries({ queryKey: ['action-ledger', scope] });
    setMessage(value);
  }
  function addAction() {
    setEditing(null);
    setDialog('action');
  }
  return (
    <section className="action-timing-workspace ledger-workspace" aria-label="动作耗时管理">
      <div className="ledger-content">
        <header className="ledger-heading">
          <h1>动作耗时</h1>
          <div className="ledger-heading-controls">
            <Select
              aria-label="统计所属项目"
              value={scope}
              onValueChange={(value) => {
                location.hash = timingHash(value);
              }}
            >
              <option value="independent">独立工作区</option>
              {projects.data?.projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </Select>
            <Button disabled={!writable} onClick={() => setDialog('import')}>
              <Upload size={16} />
              导入
            </Button>
            <Button disabled={!data} onClick={() => setDialog('export')}>
              <Download size={16} />
              导出
            </Button>
            <Button className="primary" disabled={!writable} onClick={addAction}>
              <Plus size={16} />
              添加动作
            </Button>
          </div>
        </header>
        <ErrorText error={report.error || projects.error} />
        {message && (
          <p className="ledger-notice" role="status">
            {message}
          </p>
        )}
        {data && !writable && (
          <p className="ledger-muted">项目已归档，可查看和导出；恢复项目后可继续编辑。</p>
        )}
        <div className="ledger-layout">
          <aside className="ledger-categories" aria-label="动作分类">
            <div className="ledger-section-heading">
              <h2>分类</h2>
              <button
                className="ledger-link"
                disabled={!writable}
                onClick={() => setDialog('categories')}
              >
                管理
              </button>
            </div>
            <div className="ledger-category-options">
              <CategoryButton
                name="全部动作"
                count={data?.action_count || 0}
                active={!category}
                onClick={() => chooseCategory('')}
              />
              {categories.map((item) => (
                <CategoryButton
                  key={item.id}
                  name={item.name}
                  count={item.count}
                  active={category === item.id}
                  onClick={() => chooseCategory(item.id)}
                />
              ))}
              <CategoryButton
                name="未分类"
                count={data?.uncategorized_count || 0}
                active={category === 'uncategorized'}
                onClick={() => chooseCategory('uncategorized')}
              />
            </div>
          </aside>
          <div className="ledger-table-panel" aria-busy={report.isFetching}>
            <div className="ledger-toolbar">
              <label className="ledger-search">
                <Search size={16} aria-hidden="true" />
                <input
                  aria-label="搜索动作名称"
                  placeholder="搜索动作名称"
                  maxLength={120}
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setOffset(0);
                  }}
                />
              </label>
              <Select
                aria-label="筛选耗时状态"
                value={status}
                onValueChange={(value) => {
                  setStatus(value as DurationStatus);
                  setOffset(0);
                }}
              >
                <option value="all">全部状态</option>
                <option value="filled">已填写</option>
                <option value="missing">待填写</option>
              </Select>
            </div>
            <div className="ledger-table-scroll">
              <table className="ledger-table ledger-action-table">
                <caption className="sr-only">动作耗时表</caption>
                <thead>
                  <tr>
                    <th>动作名称</th>
                    <th>分类</th>
                    <th
                      className="ledger-number"
                      aria-sort={
                        sort === 'duration_asc'
                          ? 'ascending'
                          : sort === 'duration_desc'
                            ? 'descending'
                            : 'none'
                      }
                    >
                      <button
                        className="ledger-sort"
                        aria-label={
                          sort === 'name'
                            ? '按耗时从长到短排序'
                            : sort === 'duration_desc'
                              ? '按耗时从短到长排序'
                              : '恢复默认排序'
                        }
                        title={
                          sort === 'name'
                            ? '从长到短'
                            : sort === 'duration_desc'
                              ? '从短到长'
                              : '恢复默认排序'
                        }
                        onClick={() => {
                          setSort(
                            sort === 'name'
                              ? 'duration_desc'
                              : sort === 'duration_desc'
                                ? 'duration_asc'
                                : 'name',
                          );
                          setOffset(0);
                        }}
                      >
                        耗时（秒）
                        <SortIcon size={14} aria-hidden="true" />
                      </button>
                    </th>
                    <th>备注</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((action) => (
                    <tr key={action.id}>
                      <td className="ledger-action-name">{action.name}</td>
                      <td>{action.category}</td>
                      <td
                        className={`ledger-number ${action.duration_seconds === null ? 'ledger-muted' : ''}`}
                      >
                        {durationText(action.duration_seconds)}
                      </td>
                      <td className="ledger-action-notes">{action.notes || '—'}</td>
                      <td>
                        <div className="ledger-row-actions">
                          <button
                            className="ledger-link"
                            disabled={!writable}
                            onClick={() => {
                              setEditing(action);
                              setDialog('action');
                            }}
                          >
                            编辑
                          </button>
                          <button
                            className="ledger-link ledger-delete"
                            disabled={!writable}
                            onClick={() => setDeleting(action)}
                          >
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {report.isPending && (
              <p className="ledger-empty" role="status">
                正在加载动作…
              </p>
            )}
            {report.isError && !data && (
              <div className="ledger-empty">
                <p>暂时无法加载，请重试。</p>
                <Button onClick={() => void report.refetch()}>重新加载</Button>
              </div>
            )}
            {data && !data.items.length && (
              <div className="ledger-empty">
                <FolderOpen size={30} strokeWidth={1.4} />
                <h2>{data.action_count ? '没有符合条件的动作' : '暂无动作'}</h2>
              </div>
            )}
            <div className="ledger-pagination">
              <span>共 {data?.total || 0} 个动作</span>
              {(data?.total || 0) > 20 && (
                <>
                  <small>
                    第 {Math.floor(offset / 20) + 1} / {Math.ceil((data?.total || 0) / 20)} 页
                  </small>
                  <Button
                    disabled={!offset || report.isFetching}
                    onClick={() => setOffset(Math.max(0, offset - 20))}
                  >
                    上一页
                  </Button>
                  <Button
                    disabled={offset + 20 >= (data?.total || 0) || report.isFetching}
                    onClick={() => setOffset(offset + 20)}
                  >
                    下一页
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      {dialog === 'categories' && (
        <CategoryManager
          scope={scope}
          categories={categories}
          onSaved={saved}
          onClose={() => setDialog('')}
        />
      )}
      {dialog === 'action' && (
        <ActionEditor
          scope={scope}
          categories={categories}
          action={editing}
          categoryId={category === 'uncategorized' ? '' : category}
          onSaved={saved}
          onClose={() => setDialog('')}
        />
      )}
      {dialog === 'import' && (
        <ImportDialog scope={scope} onSaved={saved} onClose={() => setDialog('')} />
      )}
      {dialog === 'export' && (
        <ExportDialog
          scope={scope}
          filters={filters}
          total={data?.total || 0}
          actionCount={data?.action_count || 0}
          onClose={() => setDialog('')}
        />
      )}
      {deleting && (
        <DeleteActionDialog
          scope={scope}
          action={deleting}
          onSaved={saved}
          onClose={() => setDeleting(null)}
        />
      )}
    </section>
  );
}

function CategoryButton({
  name,
  count,
  active,
  onClick,
}: {
  name: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`ledger-category${active ? ' selected' : ''}`}
      onClick={onClick}
      aria-pressed={active}
    >
      <span>{name}</span>
      <small>{count}</small>
    </button>
  );
}
