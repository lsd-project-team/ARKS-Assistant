import { useQuery } from '@tanstack/react-query';
import type { Client } from '../shared/client';
import { handoverScope, type HandoverRecord } from '../shared/types';
import type { packageGroups, PackageItem } from './packageContents';

function FixedPackageItem({
  item,
  client,
  onOpen,
}: {
  item: PackageItem;
  client: Client;
  onOpen: (id: string, version?: number) => void;
}) {
  const snapshot = useQuery({
    queryKey: ['handover-record', handoverScope, item.record_id, item.version],
    queryFn: () => client.get<HandoverRecord>(`/records/${item.record_id}?version=${item.version}`),
    staleTime: Infinity,
  });
  return (
    <li>
      <button onClick={() => onOpen(item.record_id, item.version)}>
        {/* 名称也读取固定修订，避免工作后来改名后改变旧包的展示。 */}
        <span>{snapshot.data?.title || item.title}</span>
        <small>v{item.version}</small>
      </button>
      {!!snapshot.error && (
        <span className="package-item-error">此固定版本暂时无法读取，点击查看详情。</span>
      )}
    </li>
  );
}

export function PackageContentsList({
  groups,
  client,
  onOpen,
}: {
  groups: ReturnType<typeof packageGroups>;
  client: Client;
  onOpen: (id: string, version?: number) => void;
}) {
  return (
    <div className="package-content-groups">
      {groups.map((group) => (
        <section className="package-content-group" key={group.id}>
          <h4>
            {group.label}
            <span>{group.items.length}</span>
          </h4>
          <ul>
            {group.items.map((item) => (
              <FixedPackageItem
                key={`${item.record_id}:${item.version}`}
                item={item}
                client={client}
                onOpen={onOpen}
              />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
