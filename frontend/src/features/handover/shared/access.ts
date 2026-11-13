import { tabs, type Tab } from './types.ts';

export function handoverTabs() {
  return tabs;
}
export function allowedHandoverTab(_tab: Tab) {
  return true;
}
