import { useState } from 'react';
import { useWorkspace } from '../lib/store';
import { Button, Modal } from './ui';
import { toast } from '../lib/toasts';
import { Select } from './Select';

const SHORTCUTS = [
  { label: '快速打开文件', keys: ['Ctrl + P'] },
  { label: '源码全文搜索', keys: ['Ctrl + Shift + F'] },
  { label: '当前文件查找', keys: ['Ctrl + F'] },
  { label: '跳转到行', keys: ['Ctrl + G'] },
  { label: '重新打开关闭的标签', keys: ['Ctrl + Shift + T'] },
  { label: '文件前进 / 后退', keys: ['Alt + ←', 'Alt + →'] },
  { label: '发送 / 换行', keys: ['Enter', 'Shift + Enter'] },
];

export function ReaderPreferences({
  lineCount,
  onClose,
}: {
  lineCount: number;
  onClose: () => void;
}) {
  const { activePath, sourceFontSize, sourceLineHeight, setReader, resetLayout, openFile } =
    useWorkspace();
  const [line, setLine] = useState('');
  function locate() {
    const number = Number(line);
    if (!Number.isInteger(number) || number < 1 || number > lineCount) {
      toast(`请输入 1 到 ${lineCount} 之间的行号`, undefined, 'error');
      return;
    }
    openFile(activePath, number, 'pinned', number);
    onClose();
  }
  return (
    <Modal
      open
      title="阅读与布局"
      description="调整源码显示，快速定位行号。"
      className="reader-dialog"
      onClose={onClose}
    >
      <div className="dialog-body reader-preferences">
        <div className="reader-display-fields">
          <label>
            源码字号{' '}
            <Select
              aria-label="源码字号"
              value={sourceFontSize}
              onValueChange={(value) => setReader(Number(value), sourceLineHeight)}
            >
              {[10, 11, 12, 13, 14, 16, 18, 20, 22].map((size) => (
                <option key={size} value={size}>
                  {size} px
                </option>
              ))}
            </Select>
          </label>
          <label>
            行高{' '}
            <Select
              aria-label="行高"
              value={sourceLineHeight}
              onValueChange={(value) => setReader(sourceFontSize, Number(value))}
            >
              {[1.3, 1.5, 1.6, 1.8, 2, 2.2, 2.4].map((height) => (
                <option key={height} value={height}>
                  {height}
                </option>
              ))}
            </Select>
          </label>
        </div>
        <form
          className="reader-jump"
          onSubmit={(event) => {
            event.preventDefault();
            locate();
          }}
        >
          <label htmlFor="reader-line">跳转到行</label>
          <div className="reader-jump-controls">
            <input
              id="reader-line"
              aria-label="跳转行号"
              type="number"
              min={1}
              max={lineCount}
              value={line}
              onChange={(event) => setLine(event.target.value)}
              placeholder={`1–${lineCount}`}
            />
            <Button disabled={!activePath || !line}>跳转</Button>
          </div>
        </form>
        <section className="reader-shortcuts" aria-labelledby="reader-shortcuts-title">
          <h3 id="reader-shortcuts-title">常用快捷键</h3>
          <dl className="shortcut-list">
            {SHORTCUTS.map(({ label, keys }) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>
                  {keys.map((key) => (
                    <kbd key={key}>{key}</kbd>
                  ))}
                </dd>
              </div>
            ))}
          </dl>
        </section>
        <div className="reader-layout-reset">
          <p>恢复问答、源码和文件树的默认布局。</p>
          <Button
            onClick={() => {
              resetLayout();
              toast('布局已恢复默认');
              onClose();
            }}
          >
            恢复默认布局
          </Button>
        </div>
      </div>
    </Modal>
  );
}
