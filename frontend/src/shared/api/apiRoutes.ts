const globalPath =
  /^\/(projects|sources|health|settings|mcp|backup|storage|data|handover|auth|admin|usage)(\/|\?|$)/;

export function scopedApiUrl(path: string, projectId: string) {
  return `/api${globalPath.test(path) ? '' : `/p/${projectId || 'independent'}`}${path}`;
}
