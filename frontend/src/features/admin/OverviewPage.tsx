import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowUpRight, Database, Eye, ListChecks, Timer, Users } from 'lucide-react';
import { ErrorText } from '../../shared/ui/ui';
import type { Event, Overview } from '../handover/shared/types';
import { adminApi, dateTime, duration } from './client';
import type { UsageOverview } from './types';

export function OverviewPage() {
  const [period, setPeriod] = useState('7');
  const [metric, setMetric] = useState<'visits' | 'tasks' | 'active_ms'>('visits');
  const summary = useQuery({
    queryKey: ['admin-overview', period],
    queryFn: () => adminApi<UsageOverview>(`/admin/overview?period=${period}`),
    refetchInterval: 15000,
  });
  const business = useQuery({
    queryKey: ['admin-business'],
    queryFn: () => adminApi<Overview>('/handover'),
    refetchInterval: 15000,
  });
  const data = summary.data;
  const operations = useQuery({
    queryKey: ['admin-recent-operations'],
    queryFn: async () => {
      const [handover, management] = await Promise.all([
        adminApi<Event[]>('/handover/events'),
        adminApi<
          {
            id: string;
            actor: string;
            action: string;
            target: string;
            detail: string;
            created_at: string;
          }[]
        >('/admin/events?limit=6'),
      ]);
      return { handover, management };
    },
    refetchInterval: 15000,
  });
  const rows = business.data?.records || [];
  const recentOperations = [
    ...(operations.data?.handover || []).map((event) => ({
      id: `handover-${event.id}`,
      title: rows.find((row) => row.id === event.record_id)?.title || '交接记录',
      actor: event.actor,
      detail: event.detail,
      created_at: event.created_at,
      href: `#handover/updates?record=${event.record_id}&version=${event.version}`,
    })),
    ...(operations.data?.management || []).map((event) => ({
      ...event,
      id: `management-${event.id}`,
      href: '#admin/settings',
      title: event.target.startsWith('/') ? event.action : `${event.action} · ${event.target}`,
    })),
  ]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 6);
  const formal = rows.filter(
    (row) => !['task', 'candidate', 'job'].includes(row.kind) && row.state !== 'archived',
  );
  const tasks = rows.filter((row) => row.kind === 'task' && row.state !== 'archived');
  const stats = data && [
    {
      title: '活跃用户',
      value: data.active_users.toLocaleString(),
      unit: '人',
      icon: Users,
    },
    {
      title: '访问量',
      value: data.visits.toLocaleString(),
      unit: '次',
      icon: Eye,
    },
    {
      title: '有效使用时长',
      value: duration(data.active_ms),
      unit: '',
      icon: Timer,
    },
    {
      title: '任务次数',
      value: data.tasks.toLocaleString(),
      unit: '次',
      icon: ListChecks,
    },
    {
      title: '累计数据量',
      value: data.data_total.toLocaleString(),
      unit: '条 · 当前',
      icon: Database,
    },
  ];
  const daily = data?.daily.slice(-30) || [];
  const max = Math.max(1, ...daily.map((row) => row[metric]));
  return (
    <div className="admin-page">
      <header className="admin-heading">
        <div>
          <h1>管理概览</h1>
        </div>
        <div className="admin-segments" aria-label="统计时间范围">
          {[
            ['7', '最近 7 天'],
            ['30', '最近 30 天'],
            ['all', '自开始采集'],
          ].map(([id, label]) => (
            <button key={id} aria-pressed={period === id} onClick={() => setPeriod(id)}>
              {label}
            </button>
          ))}
        </div>
      </header>
      <ErrorText error={summary.error || business.error || operations.error} />
      {summary.isError && (
        <button className="button" onClick={() => void summary.refetch()}>
          重新加载统计
        </button>
      )}
      {summary.isPending && <p role="status">正在读取实际统计…</p>}
      {data && (
        <>
          <div className="admin-stat-grid">
            {stats!.map((item) => (
              <article className="admin-stat" key={item.title}>
                <div className="admin-stat-label">
                  <span>{item.title}</span>
                  <item.icon size={17} />
                </div>
                <strong>
                  {item.value}
                  <small>{item.unit}</small>
                </strong>
              </article>
            ))}
          </div>
          <section className="admin-panel">
            <div className="admin-panel-heading">
              <h2>使用趋势</h2>
              <div className="admin-segments">
                {(
                  [
                    ['visits', '访问量'],
                    ['tasks', '任务次数'],
                    ['active_ms', '有效时长'],
                  ] as const
                ).map(([key, label]) => (
                  <button key={key} aria-pressed={metric === key} onClick={() => setMetric(key)}>
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div
              className="admin-chart"
              role="img"
              aria-label={`${metric === 'visits' ? '访问量' : metric === 'tasks' ? '任务次数' : '有效时长'}每日趋势`}
            >
              {daily.map((row) => (
                <div className="admin-chart-day" key={row.date}>
                  <span className="admin-chart-value">
                    {metric === 'active_ms' ? duration(row[metric]) : row[metric]}
                  </span>
                  <div className="admin-chart-track">
                    <span style={{ height: `${(row[metric] / max) * 100}%` }} />
                  </div>
                  <small>{row.date.slice(5)}</small>
                </div>
              ))}
            </div>
            <details className="admin-metric-rules">
              <summary>查看统计口径与数据构成</summary>
              <p>
                采集开始于 {dateTime(data.collected_since)}
                ，统计普通用户的实际使用，历史访问与时长不补造。 按北京时间汇总
                {data.daily.length > 30 ? '，图表展示最近 30 天' : ''}。
              </p>
              <p>
                访问量按每次加载用户端页面计数；同页切换功能不新增访问。失焦、后台、超过 60
                秒无操作均停止累计时长，同一用户多窗口的重叠时长只计一次。成功的业务保存计为任务；AI
                问答在成功完成后按问题计一次，失败、取消、重新生成和内部调用不重复计数。
              </p>
              <p>
                数据存量包括
                {Object.entries(data.data_breakdown)
                  .map(([label, count]) => `${label} ${count} 条`)
                  .join('、')}
                ；不计回收站消息、历史修订、审计日志、AI
                中间候选或运行事件。数据存量始终显示当前值。
              </p>
            </details>
          </section>
        </>
      )}
      <div className="admin-business-grid">
        {[
          {
            title: '等待审核',
            count: formal.filter((row) => row.state === 'draft').length,
            url: '#handover/updates',
          },
          {
            title: '需要重新复核',
            count: formal.filter((row) => row.state === 'needs_review').length,
            url: '#handover/updates',
          },
          {
            title: '进行中的工作',
            count: tasks.filter((row) => row.payload.work_status === 'doing').length,
            url: '#handover/tasks',
            note: `${tasks.filter((row) => row.payload.work_status === 'blocked').length} 项阻塞工作`,
          },
          {
            title: '交接包',
            count: rows.filter((row) => row.kind === 'package' && row.state !== 'archived').length,
            url: '#handover/packages',
          },
        ].map((item) => (
          <a className="admin-business-card" href={item.url} key={item.title}>
            <div>
              {item.title}
              <ArrowUpRight size={16} />
            </div>
            <strong>{business.isPending ? '—' : item.count}</strong>
            {item.note && <p>{item.note}</p>}
          </a>
        ))}
      </div>
      <section className="admin-panel">
        <div className="admin-panel-heading">
          <h2>近期操作</h2>
          <a href="#handover/updates">查看复核与追溯 →</a>
        </div>
        {recentOperations.length ? (
          recentOperations.map((row) => (
            <a className="admin-recent-row" key={row.id} href={row.href}>
              <div>
                <strong>{row.title}</strong>
                <small>
                  {row.actor} · {row.detail}
                </small>
              </div>
              <small>{dateTime(row.created_at)}</small>
              <ArrowUpRight size={14} />
            </a>
          ))
        ) : (
          <p className="admin-empty">
            {operations.isPending ? '正在读取近期操作…' : '暂无操作记录。'}
          </p>
        )}
      </section>
    </div>
  );
}
