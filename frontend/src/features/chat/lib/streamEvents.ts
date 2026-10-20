type Payload = Record<string, unknown>;
type EventSourceLike = Pick<EventSource, 'addEventListener' | 'removeEventListener'>;

// 延用 SSE 的递增序号，重连重放不重复追加；坏 JSON 不打断后续事件。
export function subscribeRunEvents(source: EventSourceLike, malformed: () => void) {
  let cursor = 0;
  let active = true;
  const listeners: [string, EventListener][] = [];
  return {
    listen(kind: string, handle: (payload: Payload) => void) {
      const listener: EventListener = (event) => {
        if (!active) return;
        const message = event as MessageEvent;
        const sequence = Number(message.lastEventId);
        if (!Number.isSafeInteger(sequence) || sequence <= 0 || !message.data) {
          malformed();
          return;
        }
        if (sequence <= cursor) return;
        let payload: unknown;
        try {
          payload = JSON.parse(message.data);
        } catch {
          malformed();
          return;
        }
        if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
          malformed();
          return;
        }
        cursor = sequence;
        handle(payload as Payload);
      };
      source.addEventListener(kind, listener);
      listeners.push([kind, listener]);
    },
    dispose() {
      active = false;
      for (const [kind, listener] of listeners) source.removeEventListener(kind, listener);
    },
  };
}

export function createAnswerBuffer(
  append: (text: string) => void,
  replace: (text: string) => void,
  schedule: (callback: () => void) => unknown = (callback) => setTimeout(callback, 32),
  unschedule: (id: unknown) => void = (id) => clearTimeout(id as ReturnType<typeof setTimeout>),
) {
  let pending = '';
  let timer: unknown;
  function clear() {
    if (timer !== undefined) unschedule(timer);
    timer = undefined;
  }
  function flush() {
    clear();
    const text = pending;
    pending = '';
    if (text) append(text);
  }
  return {
    token(text: unknown) {
      if (typeof text !== 'string') return;
      pending += text;
      if (timer === undefined) timer = schedule(flush);
    },
    replace(text: unknown) {
      if (typeof text !== 'string') return;
      clear();
      pending = '';
      replace(text);
    },
    finish(text?: unknown) {
      if (typeof text === 'string') this.replace(text);
      else flush();
    },
    dispose() {
      clear();
      pending = '';
    },
  };
}
