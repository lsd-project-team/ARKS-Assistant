import type { Project } from '../../../shared/types/api';

export function displaySourcePath(path: string, project?: Project) {
  const match = path.match(/^@sources\/([^/]+)\/(.*)$/);
  if (!match) return path;
  const label = project?.source_folders?.find((folder) => folder.source_id === match[1])?.label;
  return `${label || '历史源码目录'}/${match[2]}`;
}
