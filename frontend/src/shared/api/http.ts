export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function requestJsonResponse(
  fetcher: (url: string, options: RequestInit) => Promise<Response>,
  url: string,
  options?: RequestInit,
): Promise<Response> {
  const response = await fetcher(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      typeof body?.detail === 'string' ? body.detail : `请求失败 (${response.status})`,
      response.status,
    );
  }
  return response;
}
