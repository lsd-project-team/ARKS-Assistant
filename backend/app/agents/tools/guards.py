"""Agent 工具适配器；业务规则由对应服务负责。"""

from langchain_core.tools import ToolException


def source_path(path):
    return path.removeprefix("/workspace/")


def safe_source_tools(items, label="源码工具"):
    def guarded(coroutine):
        async def invoke(**arguments):
            try:
                return await coroutine(**arguments)
            except (ValueError, OSError) as error:
                raise ToolException(
                    f"{label}未完成：{error}。请核对参数后重试，失败结果不能作为证据。"
                ) from error

        return invoke

    for item in items:
        item.coroutine = guarded(item.coroutine)
        item.handle_tool_error = True
    return items
