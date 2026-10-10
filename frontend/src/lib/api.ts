export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === 'string' ? body.detail : `请求失败 (${response.status})`,
    );
  }
  return response.json() as Promise<T>;
}
export const jsonBody = (value: unknown) => JSON.stringify(value);
export const query = (value: string) => encodeURIComponent(value);
