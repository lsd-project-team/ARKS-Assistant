import { api } from '../../app/api/client';
import type { TimingProject, TimingProjectList } from './ledger-types';

const root = '/action-timing/projects';

export const timingProjects = {
  list: (signal?: AbortSignal) => api<TimingProjectList>(root, { signal }),
  save: (name: string, project: TimingProject | null, signal?: AbortSignal) =>
    api<TimingProject>(project ? `${root}/${project.id}` : root, {
      method: project ? 'PATCH' : 'POST',
      body: JSON.stringify({ name: name.trim(), ...(project ? { version: project.version } : {}) }),
      signal,
    }),
};
