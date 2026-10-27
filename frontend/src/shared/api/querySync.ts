// 窗口之间只广播变更路径，不传消息正文、设置值或密钥。
const channelName = 'trunk-data-changes';
let publisher: BroadcastChannel | undefined;

export function changed(path: string) {
  if (typeof BroadcastChannel === 'undefined') return;
  publisher ||= new BroadcastChannel(channelName);
  publisher.postMessage(path);
}

export function queryGroups(path: string): string[] {
  if (/^\/action-timing\/(ledger|projects)(\/|\?|$)/.test(path))
    return ['timing-projects', 'action-ledger'];
  if (/^\/projects(\/|\?|$)/.test(path))
    return ['projects', 'project', 'project-threads', 'project-materials', 'threads', 'storage'];
  if (/^\/(threads|runs|queue)(\/|$)/.test(path)) {
    return ['threads', 'thread', 'queue', 'context', 'memories', 'storage'];
  }
  if (/^\/memories(\/|$)/.test(path)) return ['memories', 'memory-history', 'storage'];
  if (path === '/settings') return ['settings'];
  if (path === '/source-options') return ['source-preferences'];
  return [];
}

export function listenForChanges(receive: (groups: string[]) => void) {
  if (typeof BroadcastChannel === 'undefined') return () => {};
  const listener = new BroadcastChannel(channelName);
  listener.onmessage = (event: MessageEvent<unknown>) => {
    if (typeof event.data === 'string') receive(queryGroups(event.data));
  };
  return () => listener.close();
}
