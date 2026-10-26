import { useState } from 'react';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { Select } from '../../shared/ui/Select';
import { ledgerClient } from './ledger-client';
import type { LedgerFilters } from './ledger-types';
import { useLedgerOperation } from './useLedgerOperation';

export function ExportDialog({
  scope,
  filters,
  total,
  actionCount,
  onClose,
}: {
  scope: string;
  filters: LedgerFilters;
  total: number;
  actionCount: number;
  onClose: () => void;
}) {
  const [format, setFormat] = useState<'xlsx' | 'csv'>('xlsx');
  const [range, setRange] = useState('all');
  const operation = useLedgerOperation();
  async function download() {
    if (
      await operation.run((signal) =>
        ledgerClient(scope).download(
          format,
          range === 'filtered' ? filters : undefined,
          false,
          signal,
        ),
      )
    )
      onClose();
  }
  return (
    <Modal
      open
      title="导出动作耗时"
      description="导出文件与导入模板格式一致，可编辑后重新导入。"
      className="ledger-dialog"
      onClose={() => !operation.busy && onClose()}
    >
      <div className="dialog-body ledger-fields">
        <label>
          导出范围
          <Select
            aria-label="导出范围"
            value={range}
            onValueChange={setRange}
            disabled={operation.busy}
          >
            <option value="all">全部动作（{actionCount} 个）</option>
            <option value="filtered">当前筛选结果（{total} 个，包含所有分页）</option>
          </Select>
        </label>
        <label>
          文件格式
          <Select
            aria-label="导出格式"
            value={format}
            onValueChange={(value) => setFormat(value as 'xlsx' | 'csv')}
            disabled={operation.busy}
          >
            <option value="xlsx">Excel（.xlsx）</option>
            <option value="csv">CSV（.csv）</option>
          </Select>
        </label>
        <ErrorText error={operation.error} reveal />
      </div>
      <div className="modal-footer">
        <Button disabled={operation.busy} onClick={onClose}>
          取消
        </Button>
        <Button className="primary" disabled={operation.busy} onClick={() => void download()}>
          {operation.busy ? '导出中…' : '导出文件'}
        </Button>
      </div>
    </Modal>
  );
}
