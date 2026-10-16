import type { BackupReport } from '../../../shared/types/api';

export function BackupPreview({ report, filename }: { report: BackupReport; filename: string }) {
  return (
    <section className="backup-preview" aria-label="备份校验结果">
      <strong>校验通过 · {filename}</strong>
      <p className="muted">
        格式 {report.format_version === 0 ? '旧版' : `v${report.format_version}`} · 数据版本{' '}
        {report.database_revision || '未标注'} · {report.file_count} 个文件
      </p>
      <p>
        {report.counts.threads || 0} 个对话 · {report.counts.messages || 0} 条消息 ·{' '}
        {report.counts.runs || 0} 次运行
      </p>
      {report.created_at && (
        <p className="muted">导出时间：{new Date(report.created_at).toLocaleString()}</p>
      )}
      {report.workspace_root && (
        <p className="backup-source muted">源码目录：{report.workspace_root}</p>
      )}
      {report.warnings.map((warning) => (
        <p key={warning} className="muted">
          {warning}
        </p>
      ))}
      <p className="muted">
        仅完成校验，当前数据尚未更改。恢复会替换对话、记忆和检查点；旧数据保存在恢复目录。
      </p>
      <details>
        <summary>查看恢复步骤</summary>
        <ol>
          <li>停止本机服务，并确认没有正在进行的回复。</li>
          <li>在项目目录执行下方命令，将“备份路径”替换为所选 ZIP 的完整路径。</li>
          <li>重新启动服务。原有模型密钥配置保留，新电脑需要重新填写。</li>
        </ol>
        <code>.\scripts\RestoreData.ps1 -Backup '备份路径' -Apply</code>
        <p className="muted">若恢复被中断，先执行 .\scripts\RestoreData.ps1 -Rollback，再启动。</p>
      </details>
    </section>
  );
}
