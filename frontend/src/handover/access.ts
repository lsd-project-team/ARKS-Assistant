import { tabs, type Tab } from './types.ts';

export function canReview(role: string | undefined) {
  return role === 'admin';
}
export function handoverTabs(role: string | undefined) {
  return tabs.filter((tab) => tab.id !== 'updates' || canReview(role));
}
export function allowedHandoverTab(tab: Tab, role: string | undefined) {
  return tab !== 'updates' || canReview(role);
}
