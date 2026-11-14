export function displayName(payload) {
  const first = String(payload.first ?? "").trim();
  const last = String(payload.last ?? "").trim();
  return `${first} ${last}`.trim();
}

export function userId(payload) {
  return payload.id;
}
