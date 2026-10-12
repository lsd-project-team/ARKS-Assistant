import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useDebouncedValue } from './useDebouncedValue';

interface Association {
  source_root: string | null;
  deepwiki_repo: string;
  knowledge_available: boolean;
  status: 'matched' | 'unknown';
  note: string;
}

export function useProjectAssociation(root: string, folders: string[], enabled: boolean) {
  const signature = JSON.stringify([
    root.trim(),
    folders.map((value) => value.trim()).filter(Boolean),
  ]);
  const settled = useDebouncedValue(signature, 400);
  const hasPaths = !!root.trim() || folders.some((value) => value.trim());
  const query = useQuery({
    queryKey: ['project-association', settled],
    enabled: enabled && hasPaths && settled === signature,
    retry: false,
    queryFn: ({ signal }) => {
      const [primary, attached] = JSON.parse(settled) as [string, string[]];
      const params = new URLSearchParams({ source_root: primary });
      for (const folder of attached) params.append('source_roots', folder);
      return api<Association>(`/projects/association?${params}`, { signal });
    },
  });
  return {
    ...query,
    data: settled === signature ? query.data : undefined,
    detecting: enabled && hasPaths && (settled !== signature || query.isFetching),
  };
}
