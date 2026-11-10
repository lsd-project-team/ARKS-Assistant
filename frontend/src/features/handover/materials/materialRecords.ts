import { text, type HandoverRecord } from '../shared/types.ts';

export function materialName(row: HandoverRecord) {
  return row.original_file?.name || text(row.payload.filename) || row.title;
}

export const materialFileTypes = [
  { id: 'pdf', label: 'PDF', extensions: ['pdf'] },
  { id: 'word', label: 'Word', extensions: ['doc', 'docx', 'docm', 'odt', 'rtf'] },
  {
    id: 'spreadsheet',
    label: '表格',
    extensions: ['xls', 'xlsx', 'xlsm', 'xlsb', 'csv', 'tsv', 'ods'],
  },
  {
    id: 'image',
    label: '图片',
    extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tif', 'tiff', 'svg', 'avif', 'heic'],
  },
  { id: 'other', label: '其他', extensions: [] },
] as const;

export function materialFileType(row: HandoverRecord) {
  // 只按可见文件名归类，不读取文件正文；历史无后缀文本与未知格式归入“其他”。
  const extension = materialName(row)
    .trim()
    .match(/\.([^.]+)$/)?.[1]
    .toLowerCase();
  return (
    materialFileTypes.find((type) => type.extensions.some((item) => item === extension))?.id ||
    'other'
  );
}

export function materialFiles(rows: HandoverRecord[], search = '') {
  const words = search.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return rows
    .filter((row) => {
      if (row.kind !== 'source' || row.state === 'archived') return false;
      const metadata = `${materialName(row)} ${row.created_by || ''}`.toLocaleLowerCase();
      return words.every((word) => metadata.includes(word));
    })
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
}
