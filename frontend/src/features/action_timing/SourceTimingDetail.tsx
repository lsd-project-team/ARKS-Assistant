import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { sourceTimingClient } from './source-client';
import { actionPresentation } from './presentation';
import type { SourceStage } from './source-types';

const labels: Record<string, string> = {
  delay: '延时',
  motion: '运动',
  wait: '等待',
  timeout: '超时上限',
  background: '后台分支',
  loop: '循环',
  call: '待定调用',
  unresolved: '展开边界',
};
function Phase({ row }: { row: SourceStage }) {
  return (
    <li className={`source-phase ${row.background ? 'background' : ''}`}>
      <div className="source-phase-heading">
        <span className={`source-phase-kind ${row.kind}`}>{labels[row.kind]}</span>
        <strong>{row.label}</strong>
        {row.milliseconds != null && (
          <span>
            {row.milliseconds} ms{row.repeat ? ' / 每轮' : ''}
          </span>
        )}
        {row.background && <span className="source-pending">后台，不计入同步总时长</span>}
      </div>
      {row.conditions.length > 0 && (
        <p className="source-condition">条件：{row.conditions.join('；')}</p>
      )}
      {row.note && <p>{row.note}</p>}
      <code className="source-location">
        {row.path}:{row.line} · {row.method}
      </code>
      <pre>{row.code}</pre>
      {row.definitions?.length ? (
        <details>
          <summary>位置 / 速度等参数的源码定义</summary>
          {row.definitions.map((definition) => (
            <div key={`${definition.path}:${definition.line}`}>
              <code className="source-location">
                {definition.path}:{definition.line}
              </code>
              <pre>{definition.code}</pre>
            </div>
          ))}
        </details>
      ) : null}
    </li>
  );
}

export function SourceTimingDetail({
  scope,
  identifier,
  revision,
  onClose,
}: {
  scope: string;
  identifier: string;
  revision: string;
  onClose: () => void;
}) {
  const detail = useQuery({
    queryKey: ['source-timing', scope, revision, 'detail', identifier],
    queryFn: ({ signal }) => sourceTimingClient(scope).detail(identifier, signal),
  });
  const [filter, setFilter] = useState('');
  const [limit, setLimit] = useState(40);
  const data = detail.data;
  const view = data ? actionPresentation(data) : null;
  const stages = data?.stages?.filter((row) => !filter || row.kind === filter) || [];
  return (
    <Modal
      open
      title={view ? `${view.name} · 动作详情` : '动作详情'}
      onClose={onClose}
      className="source-timing-detail"
    >
      <div className="dialog-body">
        <ErrorText error={detail.error} />
        {detail.isPending && <p role="status">正在展开源码依据…</p>}
        {data && view && (
          <>
            <div className="source-detail-overview">
              <strong>{view.duration}</strong>
              {view.remainder && <small>{view.remainder}</small>}
              <p>{view.note}</p>
            </div>
            <details className="source-detail-evidence">
              <summary>查看计算依据</summary>
              {data.status_reason && <p>{data.status_reason}</p>}
              <p>{data.formula}</p>
              <p className="timing-caption">
                数值来自源码显式初值。此处没有运行设备，运动和信号等待不以超时值代替。
              </p>
              <code className="source-location">
                入口：{data.entry.path}:{data.entry.line} · {data.class_name}.{data.method}
              </code>
              {data.truncated && (
                <p className="timing-notice warning">
                  存在循环调用、标签跳转或展开深度限制，当前结果只包含已核到的部分。
                </p>
              )}
              <h3>源码参数初值</h3>
              {data.parameters?.length ? (
                <div className="timing-table-wrap">
                  <table className="timing-table source-parameter-table">
                    <thead>
                      <tr>
                        <th>参数</th>
                        <th>显式初值</th>
                        <th>源码</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.parameters.map((parameter) => (
                        <tr key={parameter.name}>
                          <td>
                            <code>{parameter.name}</code>
                          </td>
                          <td>{parameter.value == null ? '未能求值' : String(parameter.value)}</td>
                          <td>
                            <code>
                              {parameter.path}:{parameter.line}
                            </code>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="muted">当前展开片段没有可引用的参数显式初值。</p>
              )}
              <h3>延时、运动与等待</h3>
              <select
                aria-label="筛选源码耗时阶段"
                value={filter}
                onChange={(event) => {
                  setFilter(event.target.value);
                  setLimit(40);
                }}
              >
                <option value="">全部阶段</option>
                {Object.entries(labels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <ol className="source-phases">
                {stages.slice(0, limit).map((row, n) => (
                  <Phase key={`${row.path}:${row.line}:${n}`} row={row} />
                ))}
              </ol>
              {!stages.length && (
                <p className="muted">此入口没有已识别的显式耗时阶段；这不等于实际执行耗时为零。</p>
              )}
              {stages.length > limit && (
                <Button onClick={() => setLimit(limit + 40)}>
                  继续展开（剩余 {stages.length - limit} 项）
                </Button>
              )}
            </details>
          </>
        )}
      </div>
    </Modal>
  );
}
