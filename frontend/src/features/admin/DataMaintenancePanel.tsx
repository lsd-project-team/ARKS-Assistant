import { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, RefreshCw, Upload } from 'lucide-react';
import type { BackupReport, StorageStats } from '../../shared/types/api';
import { api } from '../../app/api/client';
import { Button, ErrorText } from '../../shared/ui/ui';
import { toast } from '../../shared/utils/toasts';
import { BackupPreview } from './BackupPreview';
import { sessionFetch } from '../auth/session';
import './data-maintenance.css';

function bytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value >= 1024 * 1024 * 1024) return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GiB`;
  return value < 1024 * 1024
    ? `${(value / 1024).toFixed(1)} KiB`
    : `${(value / (1024 * 1024)).toFixed(1)} MiB`;
}

const groups = [
  ['databases', '对话与检查点'],
  ['memories', '记忆文件'],
  ['archives', '原文档案'],
  ['backups', '导出备份'],
  ['recovery', '恢复前的旧数据'],
  ['other', '其他数据'],
] as const;

export function DataMaintenancePanel() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const submitting = useRef(false);
  const storage = useQuery({ queryKey: ['storage'], queryFn: () => api<StorageStats>('/storage') });
  const fileInput = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<{ filename: string; report: BackupReport }>();

  async function perform(action: () => Promise<void>) {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError(undefined);
    try {
      await action();
    } catch (reason) {
      setError(reason);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  async function inspect(file: File) {
    setPreview(undefined);
    if (file.size > 512 * 1024 * 1024) throw new Error('备份 ZIP 超过 512 MiB 上限');
    const report = await api<BackupReport>('/backup/validate', {
      method: 'POST',
      body: file,
      headers: { 'Content-Type': 'application/zip' },
    });
    setPreview({ filename: file.name, report });
    toast('备份校验通过，当前数据未更改');
  }
  async function backup() {
    const response = await sessionFetch('/api/backup', { method: 'POST' });
    if (!response.ok) {
      const reason = await response.json().catch(() => undefined);
      throw new Error(reason?.detail || '备份失败，请重试');
    }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = `trunk-agent-${new Date().toISOString().slice(0, 10)}.zip`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast('备份已导出（不包含密钥配置）');
    await storage.refetch();
  }
  return (
    <div className="settings-fields">
      {storage.isPending && <p className="muted">正在统计本机存储…</p>}
      <ErrorText error={error || storage.error} reveal={!!error} />
      {storage.data && (
        <section className="storage-summary" aria-label="本机存储统计">
          <div className="storage-heading">
            <strong>已使用 {bytes(storage.data.total_bytes)}</strong>
            <button
              title="刷新存储统计"
              aria-label="刷新存储统计"
              disabled={storage.isFetching}
              onClick={() => void storage.refetch()}
            >
              <RefreshCw size={14} />
            </button>
          </div>
          <dl>
            {groups.map(([key, label]) => (
              <div key={key}>
                <dt>{label}</dt>
                <dd>{bytes(storage.data!.groups[key])}</dd>
              </div>
            ))}
          </dl>
          <p className="muted">
            {storage.data.counts.threads || 0} 个对话 · {storage.data.counts.messages || 0} 条消息 ·{' '}
            数据版本 {storage.data.revision || '未标注'}
          </p>
          <p className="muted">
            磁盘剩余 {bytes(storage.data.disk_free_bytes)}
            {storage.data.unreadable_files > 0 &&
              ` · ${storage.data.unreadable_files} 个文件未能统计`}
          </p>
        </section>
      )}
      <div className="button-row">
        <Button disabled={busy} onClick={() => void perform(backup)}>
          <Download size={14} />
          导出本地备份
        </Button>
        <Button disabled={busy} onClick={() => fileInput.current?.click()}>
          <Upload size={14} />
          选择备份并校验
        </Button>
      </div>
      <input
        ref={fileInput}
        type="file"
        accept=".zip,application/zip"
        hidden
        aria-label="选择需要校验的备份 ZIP"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0];
          event.currentTarget.value = '';
          if (file) void perform(() => inspect(file));
        }}
      />
      <p className="muted">备份不含密钥。导出前请完成或停止当前回复。</p>
      {preview && <BackupPreview {...preview} />}
    </div>
  );
}
