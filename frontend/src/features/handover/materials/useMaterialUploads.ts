import { useEffect, useRef, useState } from 'react';
import type { Client } from '../shared/client';

type UploadState = 'pending' | 'uploading' | 'uploaded' | 'failed' | 'invalid';
type UploadItem = { file: File; state: UploadState; error?: unknown };
const maxFileSize = 32 * 1024 * 1024;

function selectedFile(file: File): UploadItem {
  const error = !file.size
    ? '文件不能为空。'
    : file.size > maxFileSize
      ? '文件不能超过 32 MB。'
      : undefined;
  return { file, state: error ? 'invalid' : 'pending', error };
}

export function useMaterialUploads(client: Client, onSaved: () => void, onClose: () => void) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [busy, setBusy] = useState(false);
  const uploading = useRef(false);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  function select(files: File[]) {
    // 分次选择时保留已保存结果和待重试文件，下一轮只处理新文件及失败项。
    if (!uploading.current) setItems((current) => [...current, ...files.map(selectedFile)]);
  }
  function remove(index: number) {
    if (!uploading.current) setItems((current) => current.filter((_, at) => at !== index));
  }
  function close() {
    if (!uploading.current) onClose();
  }
  function update(index: number, state: UploadState, error?: unknown) {
    if (alive.current)
      setItems((current) =>
        current.map((item, at) => (at === index ? { ...item, state, error } : item)),
      );
  }
  async function save() {
    if (uploading.current || !items.some(canUpload)) return;
    uploading.current = true;
    setBusy(true);
    let saved = 0;
    // 每个原文件独立保存；部分失败仍继续，重试只处理尚未成功的文件。
    try {
      for (const [index, item] of items.entries()) {
        if (!alive.current) return;
        if (!canUpload(item)) continue;
        update(index, 'uploading');
        try {
          await client.upload(item.file, {});
          saved += 1;
          update(index, 'uploaded');
        } catch (error) {
          update(index, 'failed', error);
        }
      }
    } finally {
      uploading.current = false;
      if (alive.current) setBusy(false);
      if (saved) onSaved();
    }
  }
  return { items, busy, select, remove, close, save, pending: items.filter(canUpload).length };
}

function canUpload(item: UploadItem) {
  return item.state === 'pending' || item.state === 'failed';
}
