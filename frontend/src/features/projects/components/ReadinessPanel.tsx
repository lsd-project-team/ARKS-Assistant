import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { boundProjectApi } from '../lib/projectRequest';
import { bytesLabel } from '../lib/codeReadiness';
import type { ReadinessReport } from '../types/codeWork';
import { CodeWorkPolicyPanel } from './CodeWorkPolicyPanel';

export function ReadinessPanel({ projectId, readOnly }: { projectId: string; readOnly: boolean }) {
  const request = useMemo(() => boundProjectApi(projectId, api), [projectId]);
  const query = useQuery({
    queryKey: ['code-work-readiness', projectId],
    queryFn: ({ signal }) => request<ReadinessReport>('/code-changes/readiness', { signal }),
    refetchInterval: (current) => (current.state.data?.usage.active_verifications ? 2500 : false),
  });
  const report = query.data;
  return (
    <section className="code-work-panel code-work-readiness" aria-label="构建前置与资源用量">
      <div className="code-work-heading">
        <h2>构建前置与资源用量</h2>
        <Button onClick={() => void query.refetch()}>刷新前置检查</Button>
      </div>
      <ErrorText error={query.error} />
      {query.isPending ? (
        <p className="muted">正在核对构建前置…</p>
      ) : (
        report && (
          <>
            <strong role="status">
              {report.project.status === 'blocked'
                ? '构建前置仍有缺项'
                : report.project.status === 'no_build_files'
                  ? '未发现可识别的构建文件'
                  : '前置扫描完成，仍需原版本基线验证'}
            </strong>
            <details>
              <summary>构建要求与说明</summary>
              <p className="muted">
                应用可部署在 Linux；Linux 沙箱执行通道已接入，节点与镜像是否可用需探测。传统 .NET
                Framework 4.8 项目还需独立 Windows 执行节点、SDK 和私有依赖，并完成 Windows
                执行与原版本构建验收。 静态检查不能证明可构建。
              </p>
              <p className="muted">环境尚未准备时，仍可阅读、修改隔离副本与导出草稿补丁。</p>
              {report.project.primary_only && (
                <p className="muted">
                  构建前置扫描仅覆盖主源码目录；附加目录的阅读覆盖不代表已验证构建。
                </p>
              )}
              {!!report.project.attached_sources?.length && (
                <ul>
                  {report.project.attached_sources.map((source) => (
                    <li key={source.source_id}>
                      {source.label} · {source.status}
                    </li>
                  ))}
                </ul>
              )}
              <ul>
                {[...report.unresolved, ...report.project.requirements].map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
              {!!report.project.projects.length && (
                <details>
                  <summary>查看工程与平台（{report.project.projects.length} 项）</summary>
                  {report.project.projects.map((project) => (
                    <p key={project.path}>
                      <code>{project.path}</code> ·{' '}
                      {project.target_frameworks.join(' / ') || '框架未知'} ·{' '}
                      {project.platforms.join(' / ') || '平台未知'}
                    </p>
                  ))}
                </details>
              )}
              {!!report.project.issues.length && (
                <details>
                  <summary>查看缺项与边界</summary>
                  <ul>
                    {report.project.issues.map((issue, index) => (
                      <li key={index}>
                        <code>{issue.path}</code> {issue.message}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
              {!!report.project.baseline_steps.length && (
                <details>
                  <summary>原版本验证步骤</summary>
                  <ol>
                    {report.project.baseline_steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ol>
                </details>
              )}
            </details>
            <dl className="code-work-counts">
              <div>
                <dt>副本空间</dt>
                <dd>
                  {bytesLabel(report.usage.storage_bytes)} / {report.policy.max_storage_mb} MB
                </dd>
              </div>
              <div>
                <dt>日志空间</dt>
                <dd>{bytesLabel(report.usage.logs_bytes)}</dd>
              </div>
              <div>
                <dt>活动验证</dt>
                <dd>
                  {report.usage.active_verifications} / {report.policy.max_active_verifications}
                </dd>
              </div>
              <div>
                <dt>修改档案</dt>
                <dd>{report.usage.changes}</dd>
              </div>
              <div>
                <dt>当日模型预留 token（UTC）</dt>
                <dd>
                  {report.usage.reading_reserved_tokens} /{' '}
                  {report.usage.reading_token_limit ?? '无上限'}
                </dd>
              </div>
            </dl>
            <CodeWorkPolicyPanel
              key={projectId + JSON.stringify(report.policy)}
              policy={report.policy}
              api={request}
              disabled={readOnly}
              onSaved={() => void query.refetch()}
            />
          </>
        )
      )}
    </section>
  );
}
