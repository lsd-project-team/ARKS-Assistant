import { useMemo, useState } from 'react';
import { FileText } from 'lucide-react';
import { handoverClient } from '../../handover/shared/client';
import { OriginalMaterialViewer } from '../../handover/materials/OriginalMaterialViewer';
import type { HandoverRecord } from '../../handover/shared/types';
import type { FileBlock as FileData } from './types';

export function FileBlock({ block }: { block: FileData }) {
  const client = useMemo(handoverClient, []);
  const [row, setRow] = useState<HandoverRecord>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function open() {
    setLoading(true);
    setError('');
    try {
      const result = await client.get<HandoverRecord>(
        `/records/${encodeURIComponent(block.record_id)}`,
      );
      if (result.kind !== 'source') throw new Error('这条记录不是文件资料');
      // 现有附件接口只提供当前文件，旧版本不能冒充历史附件预览。
      if (block.version !== undefined && result.version !== block.version)
        throw new Error('文件版本已变化，无法预览原引用版本');
      setRow(result);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : '文件无法读取，请重试');
    } finally {
      setLoading(false);
    }
  }
  return (
    <section className="rich-file">
      <button type="button" disabled={loading} onClick={() => void open()}>
        <FileText size={20} aria-hidden="true" />
        <span>
          {block.name}
          <small>
            {loading ? '正在读取…' : '预览或下载文件'}
            {block.version ? ` · v${block.version}` : ''}
          </small>
        </span>
      </button>
      {error && <p role="alert">{error}</p>}
      {row && (
        <OriginalMaterialViewer row={row} client={client} onClose={() => setRow(undefined)} />
      )}
    </section>
  );
}
