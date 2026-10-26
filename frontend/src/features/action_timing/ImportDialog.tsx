import { useState } from 'react';
import { Download, FileSpreadsheet } from 'lucide-react';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { Select } from '../../shared/ui/Select';
import { ledgerClient } from './ledger-client';
import { durationText, importSummary } from './ledger-format';
import type { DuplicateMode, ImportPreview } from './ledger-types';
import { useLedgerOperation } from './useLedgerOperation';

const operationNames = { add: '新增', update: '更新', skip: '跳过' };

export function ImportDialog({
  scope,
  onSaved,
  onClose,
}: {
  scope: string;
  onSaved: (message: string) => Promise<void>;
  onClose: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<DuplicateMode>('skip');
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [offset, setOffset] = useState(0);
  const operation = useLedgerOperation();
  async function read() {
    await operation.run(async (signal) => {
      if (!file) throw new Error('请先选择要导入的文件');
      if (file.size > 5 * 1024 * 1024) throw new Error('文件超过5MiB，请分批导入');
      setPreview(null);
      const result = await ledgerClient(scope).preview(file, mode, signal);
      if (!signal.aborted) {
        setPreview(result);
        setOffset(0);
      }
    });
  }
  async function commit() {
    if (!preview || preview.errors.length) return;
    if (
      await operation.run(async (signal) => {
        const result = await ledgerClient(scope).commit(preview, mode, signal);
        await onSaved(`导入完成：${importSummary(result.counts)}`);
      })
    )
      onClose();
  }
  return (
    <Modal
      open
      title="导入动作耗时"
      description="支持CSV与Excel（.xlsx），Excel读取第一个工作表；每次最多5000行、5MiB。"
      className="ledger-dialog ledger-import-dialog"
      onClose={() => !operation.busy && onClose()}
    >
      <div className="dialog-body ledger-fields">
        <div className="ledger-import-template">
          <span>
            <FileSpreadsheet size={18} /> 按模板填写，耗时单位为秒
          </span>
          <Button
            disabled={operation.busy}
            onClick={() =>
              void operation.run((signal) =>
                ledgerClient(scope).download('xlsx', undefined, true, signal),
              )
            }
          >
            <Download size={15} />
            下载模板
          </Button>
          <button
            type="button"
            className="ledger-link"
            disabled={operation.busy}
            onClick={() =>
              void operation.run((signal) =>
                ledgerClient(scope).download('csv', undefined, true, signal),
              )
            }
          >
            CSV模板
          </button>
        </div>
        <label>
          选择文件
          <input
            type="file"
            accept=".csv,.xlsx"
            disabled={operation.busy}
            onChange={(event) => {
              setFile(event.target.files?.[0] || null);
              setPreview(null);
              operation.clearError();
            }}
          />
        </label>
        <label>
          遇到同分类、同名动作时
          <Select
            aria-label="重复动作处理方式"
            value={mode}
            disabled={operation.busy}
            onValueChange={(value) => {
              setMode(value as DuplicateMode);
              setPreview(null);
              operation.clearError();
            }}
          >
            <option value="skip">跳过已有动作</option>
            <option value="update">更新已有动作（空耗时保留原值）</option>
          </Select>
        </label>
        <p className="ledger-muted">
          新分类会随动作一并创建。空分类归入“未分类”；更新时备注以文件内容为准。
        </p>
        <ErrorText error={operation.error} reveal />
        {preview && (
          <section aria-label="导入预览" className="ledger-import-preview">
            <p role="status">
              {importSummary(preview.counts)}
              {preview.errors.length
                ? `，发现 ${preview.errors.length} 处问题，请修正后重新预览。`
                : '，确认后写入。'}
            </p>
            {!!preview.errors.length && (
              <ul className="ledger-import-errors" role="alert">
                {preview.errors.slice(0, 50).map((item, index) => (
                  <li key={index}>
                    第 {item.row_number} 行：{item.message}
                  </li>
                ))}
                {preview.errors.length > 50 && (
                  <li>其余 {preview.errors.length - 50} 处问题请修正文件后重新校验。</li>
                )}
              </ul>
            )}
            <div className="ledger-table-scroll">
              <table className="ledger-table">
                <caption className="sr-only">待导入的动作耗时</caption>
                <thead>
                  <tr>
                    <th>行号</th>
                    <th>动作名称</th>
                    <th>分类</th>
                    <th>耗时（秒）</th>
                    <th>处理</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.slice(offset, offset + 20).map((row) => (
                    <tr key={row.row_number}>
                      <td>{row.row_number}</td>
                      <td>{row.name}</td>
                      <td>{row.category}</td>
                      <td>
                        {durationText(
                          row.operation === 'skip'
                            ? row.duration_seconds
                            : row.effective_duration_seconds,
                        )}
                      </td>
                      <td>{operationNames[row.operation]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {preview.rows.length > 20 && (
              <div className="ledger-pagination">
                <span>
                  共 {preview.rows.length} 行，第 {Math.floor(offset / 20) + 1} 页
                </span>
                <Button disabled={!offset || operation.busy} onClick={() => setOffset(offset - 20)}>
                  上一页
                </Button>
                <Button
                  disabled={offset + 20 >= preview.rows.length || operation.busy}
                  onClick={() => setOffset(offset + 20)}
                >
                  下一页
                </Button>
              </div>
            )}
          </section>
        )}
      </div>
      <div className="modal-footer">
        <Button disabled={operation.busy} onClick={onClose}>
          取消
        </Button>
        {preview && (
          <Button disabled={operation.busy || !file} onClick={() => void read()}>
            重新预览
          </Button>
        )}
        <Button
          className="primary"
          disabled={operation.busy || !file || (!!preview && !!preview.errors.length)}
          onClick={() => void (preview ? commit() : read())}
        >
          {operation.busy ? '处理中…' : preview ? '确认导入' : '预览数据'}
        </Button>
      </div>
    </Modal>
  );
}
