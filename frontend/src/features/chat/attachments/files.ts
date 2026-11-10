export const ACCEPTED_ATTACHMENTS =
  '.docx,.pdf,.txt,.md,.cs,.cpp,.c,.h,.json,.yaml,.yml,.xml,.ini,.log,.zip,.xlsx,.csv';
export const MAX_FILE_SIZE = 32 * 1024 * 1024;
export const MAX_ATTACHMENTS = 10;

export function attachmentError(file: Pick<File, 'name' | 'size'>): string {
  const extension = /\.[^.]+$/.exec(file.name)?.[0].toLowerCase();
  if (!extension || !ACCEPTED_ATTACHMENTS.split(',').includes(extension))
    return '不支持此格式，请使用 DOCX、PDF、XLSX、CSV、ZIP 或文本文件';
  if (!file.size) return '文件不能为空';
  if (file.size > MAX_FILE_SIZE) return '单个文件不能超过 32 MB';
  return '';
}
