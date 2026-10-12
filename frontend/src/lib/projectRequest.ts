export type ProjectRequest = <T>(
  path: string,
  options?: RequestInit,
  projectId?: string,
) => Promise<T>;

// 查询缓存和异步操作固定所属项目，不能在等待期间重新读取当前页面的项目。
export function boundProjectApi(projectId: string, request: ProjectRequest): ProjectRequest {
  return <T>(path: string, options?: RequestInit, override = projectId) =>
    request<T>(path, options, override);
}
