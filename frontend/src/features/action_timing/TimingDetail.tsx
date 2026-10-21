import { useQuery } from '@tanstack/react-query';
import { ErrorText, Modal } from '../../shared/ui/ui';
import { timingClient } from './client';
import { branchLabel, eventDuration, milliseconds, statusLabels } from './format';

export function TimingDetail({
  scope,
  run,
  event,
  onClose,
}: {
  scope: string;
  run: string;
  event: string;
  onClose: () => void;
}) {
  const detail = useQuery({
    queryKey: ['action-timing', scope, run, 'detail', event],
    queryFn: ({ signal }) => timingClient(scope).detail(run, event, signal),
  });
  const row = detail.data?.event;
  const duration = row ? eventDuration(row) : null;
  return (
    <Modal
      open
      title={`单次动作记录${detail.data ? ` · ${detail.data.action.name}` : ''}`}
      onClose={onClose}
      className="timing-detail"
    >
      <div className="dialog-body">
        <ErrorText error={detail.error} />
        {detail.isPending && <p role="status">正在读取记录…</p>}
        {row && (
          <>
            <p>
              <span className={`timing-status ${row.status}`}>{statusLabels[row.status]}</span> ·{' '}
              {branchLabel(row.branch)} · 第 {row.attempt} 次尝试
            </p>
            <strong className="timing-duration">
              {milliseconds(duration)} <small>ms</small>
            </strong>
            <p className="muted">调用时间包含等待和暂停；此记录的后台任务不计入同步调用结束。</p>
            {row.reason && <p className="timing-notice">{row.reason}</p>}
            <dl className="timing-context">
              {Object.entries(row.context).map(([key, value]) => (
                <div key={key}>
                  <dt>
                    {(
                      {
                        tu: '载具',
                        product_instance: '产品实例',
                        substrate: '基板',
                        module: '基岛',
                        bond_position: '焊点',
                        process_step: '工序',
                      } as Record<string, string>
                    )[key] || key}
                  </dt>
                  <dd>{value || '—'}</dd>
                </div>
              ))}
              <div>
                <dt>原始返回</dt>
                <dd>{row.raw_result || '—'}</dd>
              </div>
              <div>
                <dt>记录编号</dt>
                <dd>{row.event_id}</dd>
              </div>
            </dl>
            <h3>内部阶段</h3>
            {!detail.data?.stages.length && <p className="muted">本次没有进入已接入的内部阶段。</p>}
            <ol className="timing-stages">
              {detail.data?.stages.map((stage) => {
                const elapsed = eventDuration(stage);
                return (
                  <li key={stage.event_id}>
                    <div>
                      <span>{stage.stage}</span>
                      <span>
                        {milliseconds(elapsed)} ms · {statusLabels[stage.status]}
                      </span>
                    </div>
                    <div className="timing-track">
                      <span
                        className={stage.category}
                        style={{
                          marginLeft: `${duration ? Math.min(100, ((stage.start_ms - row.start_ms) / duration) * 100) : 0}%`,
                          width: `${duration && elapsed != null ? Math.min(100, (elapsed / duration) * 100) : 0}%`,
                        }}
                      />
                    </div>
                    <small className="muted">
                      {
                        (
                          { wait: '信号/运行等待', delay: '配置停留', work: '工作阶段' } as Record<
                            string,
                            string
                          >
                        )[stage.category]
                      }
                      {stage.reason ? ` · ${stage.reason}` : ''}
                    </small>
                  </li>
                );
              })}
            </ol>
          </>
        )}
      </div>
    </Modal>
  );
}
