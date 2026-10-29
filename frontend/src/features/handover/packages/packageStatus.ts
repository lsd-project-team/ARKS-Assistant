export function packageStatus(state: string) {
  return state === 'confirmed' ? '已确认' : '未确认';
}
