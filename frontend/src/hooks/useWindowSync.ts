import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { listenForChanges } from '../lib/querySync';
import { invalidateProjectCaches } from '../lib/projectCache';

export function useWindowSync() {
  const cache = useQueryClient();
  useEffect(
    () =>
      listenForChanges((groups) => {
        invalidateProjectCaches(groups);
        groups.forEach((group) => void cache.invalidateQueries({ queryKey: [group] }));
      }),
    [cache],
  );
}
