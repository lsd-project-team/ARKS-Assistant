const globalPath =
  /^\/(projects|sources|health|settings|mcp|backup|storage|data|handover|auth|admin|usage)(\/|\?|$)/;
const timingLedgerPath = /^\/action-timing\/(ledger|projects)(\/|\?|$)/;

export function scopedApiUrl(path: string, projectId: string) {
  return `/api${globalPath.test(path) || timingLedgerPath.test(path) ? '' : `/p/${projectId || 'independent'}`}${path}`;
}
