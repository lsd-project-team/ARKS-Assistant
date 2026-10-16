export interface ChatPosition {
  anchor: string;
  offset: number;
  following: boolean;
}

export interface MessageJump {
  id: string;
  time: number;
  restore?: boolean;
}

export function restoredMessageJump(position?: ChatPosition): MessageJump {
  return {
    id: position && !position.following ? position.anchor : '',
    time: Date.now(),
    restore: true,
  };
}
