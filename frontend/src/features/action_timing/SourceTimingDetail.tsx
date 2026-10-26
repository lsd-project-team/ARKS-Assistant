import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { sourceTimingClient } from './source-client';
import { actionPresentation } from './presentation';
import type { SourceStage } from './source-types';
import {
  componentTime,
  missingLabels,
  motionFixedNote,
  motionCompletion,
} from './source-detail-presentation';

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
      {motionFixedNote(row.motion_model) && <p>{motionFixedNote(row.motion_model)}</p>}
      {row.motion_model && (
        <details>
          <summary>运动参数与计算公式</summary>
          <p>
            目标 / 位移：{row.motion_model.target ?? '未定'}；速度：
            {row.motion_model.velocity ?? row.motion_model.velocity_expression}
          </p>
          <p>{row.motion_model.formula}</p>
          <p>
            加速度：{row.motion_model.acceleration ?? row.motion_model.acceleration_expression}；
            减速度：{row.motion_model.deceleration ?? row.motion_model.deceleration_expression}；
            J：{row.motion_model.jerk ?? '未定'}
          </p>
          {motionCompletion(row.motion_model) && (
            <p>完成规则：{motionCompletion(row.motion_model)}</p>
          )}
          <p>{row.motion_model.conditions}</p>
          <p>尚未确定：{row.motion_model.unresolved.join('；')}</p>
        </details>
      )}
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
  const [supplementaryLimit, setSupplementaryLimit] = useState(40);
  const [missingLimit, setMissingLimit] = useState(3);
  const data = detail.data;
  const view = data ? actionPresentation(data) : null;
  const stages = data?.stages?.filter((row) => !filter || row.kind === filter) || [];
  const supplementary =
    data?.supplementary_stages?.filter((row) => !filter || row.kind === filter) || [];
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
            {data.status_reason && <p>{data.status_reason}</p>}
            {!!data.missing_requirements?.length && (
              <section aria-label="完整耗时的具体缺项">
                <h3>完整耗时还缺什么</h3>
                <ul>
                  {data.missing_requirements.slice(0, missingLimit).map((item, n) => (
                    <li key={`${item.path}:${item.line}:${n}`}>
                      <strong>{missingLabels[item.category] || item.category}</strong>
                      {item.background && <small>（后台分支）</small>}
                      <ul>
                        {item.required.map((value) => (
                          <li key={value}>{value}</li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
                {data.missing_requirements.length > missingLimit && (
                  <Button onClick={() => setMissingLimit(missingLimit + 6)}>
                    继续查看具体缺项（剩余 {data.missing_requirements.length - missingLimit} 处）
                  </Button>
                )}
              </section>
            )}
            {!!(data.known_components?.length || data.source_components?.length) && (
              <details>
                <summary>查看可算的条件、后台及每轮等待组成</summary>
                <p>以下是等待组成，不是完整动作总时长；可能与上方已知停留重合，不能逐项相加。</p>
                {[...(data.source_components || []), ...(data.known_components || [])].map(
                  (part, n) => (
                    <div key={n} className="source-phase">
                      <strong>
                        {part.scope === 'background'
                          ? '后台停留'
                          : part.scope === 'expanded'
                            ? '已展开停留'
                            : '条件/每轮组成'}
                        ：{componentTime(part)}
                      </strong>
                      {!!part.conditions.length && <p>条件：{part.conditions.join('；')}</p>}
                      <p>{part.note}</p>
                      {part.sources.map((source, i) => (
                        <code key={i} className="source-location">
                          {source.path}:{source.line}
                          {source.fixed_repetitions != null && source.fixed_repetitions > 1 && (
                            <span>
                              （{source.fixed_repetitions} 次 × {source.milliseconds} ms）
                            </span>
                          )}
                        </code>
                      ))}
                    </div>
                  ),
                )}
              </details>
            )}
            <details className="source-detail-evidence">
              <summary>查看计算依据</summary>
              <p>{data.formula}</p>
              {data.analysis_unit === 'single_cycle' && (
                <p>此项计算一个工作循环，子动作已包含在本流程中。</p>
              )}
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
                          <td>
                            {parameter.value == null
                              ? '未能求值'
                              : typeof parameter.value === 'object'
                                ? JSON.stringify(parameter.value)
                                : String(parameter.value)}
                          </td>
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
                  setSupplementaryLimit(40);
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
              {!!data.supplementary_stages?.length && (
                <details>
                  <summary>查看补充源码依据（不重复计时）</summary>
                  <p>
                    以下保留另一次展开核对到的参数、运动和等待依据；不与上方阶段合成执行顺序，
                    不重复加到已知停留中。
                  </p>
                  <ol className="source-phases">
                    {supplementary.slice(0, supplementaryLimit).map((row, n) => (
                      <Phase key={`${row.path}:${row.line}:${n}`} row={row} />
                    ))}
                  </ol>
                  {!supplementary.length && <p className="muted">当前筛选没有补充阶段。</p>}
                  {supplementary.length > supplementaryLimit && (
                    <Button onClick={() => setSupplementaryLimit(supplementaryLimit + 40)}>
                      继续查看补充依据（剩余 {supplementary.length - supplementaryLimit} 项）
                    </Button>
                  )}
                </details>
              )}
            </details>
          </>
        )}
      </div>
    </Modal>
  );
}
