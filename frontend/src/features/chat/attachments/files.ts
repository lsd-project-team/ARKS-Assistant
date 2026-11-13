export const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp'];
export const ACCEPTED_ATTACHMENTS = [
  '.docx',
  '.pdf',
  '.txt',
  '.md',
  '.cs',
  '.cpp',
  '.c',
  '.h',
  '.json',
  '.yaml',
  '.yml',
  '.xml',
  '.ini',
  '.log',
  '.zip',
  '.xlsx',
  '.csv',
  ...IMAGE_EXTENSIONS,
].join(',');
export const MAX_FILE_SIZE = 32 * 1024 * 1024;
export const MAX_ATTACHMENTS = 10;

export function extensionOf(name: string): string {
  return /\.[^.]+$/.exec(name)?.[0].toLowerCase() || '';
}

export function isImageAttachment(file: {
  name?: string;
  filename?: string;
  kind?: string;
}): boolean {
  const name = file.filename || file.name || '';
  return file.kind === 'image' || IMAGE_EXTENSIONS.includes(extensionOf(name));
}

export function attachmentError(file: Pick<File, 'name' | 'size'>): string {
  const extension = extensionOf(file.name);
  if (!extension || !ACCEPTED_ATTACHMENTS.split(',').includes(extension))
    return '不支持此格式，请使用 DOCX、PDF、XLSX、CSV、ZIP、PNG/JPG/GIF/WebP 图片或文本文件';
  if (!file.size) return '文件不能为空';
  if (file.size > MAX_FILE_SIZE) return '单个文件不能超过 32 MB';
  return '';
}

function clipboardExtension(file: File): string {
  if (file.type === 'image/jpeg') return '.jpg';
  if (file.type === 'image/webp') return '.webp';
  if (file.type === 'image/gif') return '.gif';
  return '.png';
}

/** 粘贴的截图通常只有 image.png 这个名字，按时间生成可辨认的文件名。 */
export function clipboardImages(files: File[], now = new Date()): File[] {
  const stamp = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
  ].join('');
  const clock = [
    String(now.getHours()).padStart(2, '0'),
    String(now.getMinutes()).padStart(2, '0'),
    String(now.getSeconds()).padStart(2, '0'),
  ].join('');
  return files
    .filter((file) => file.type.startsWith('image/'))
    .map((file, index) => {
      // 同一次粘贴多张时加序号，避免重名影响辨识；服务端按附件编号保存，不依赖文件名唯一。
      const suffix = index ? `-${index + 1}` : '';
      return new File([file], `截图-${stamp}-${clock}${suffix}${clipboardExtension(file)}`, {
        type: file.type || 'image/png',
      });
    });
}
