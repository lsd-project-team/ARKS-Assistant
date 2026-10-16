"""为未修改基线提供只读构建前置检查；静态存在不等于可构建。"""

from collections import Counter
from pathlib import Path

from .paths import PROJECT_SUFFIXES, discover, display
from .projects import issue, project_file
from .solutions import solution_file


def inspect_project(workspace) -> dict:
    """检查主源码根的声明，不读取根外依赖、不执行项目文件或构建命令。"""
    root = Path(workspace.root)
    paths, issues = discover(root)
    projects, solutions = [], []
    for path in paths:
        if path.suffix.lower() in PROJECT_SUFFIXES:
            projects.append(project_file(root, path))
        else:
            solutions.append(solution_file(root, path))
    attached = [
        {"source_id": display(key), "label": display(value[0]), "status": "not_included_in_copy"}
        for key, value in getattr(workspace, "attached", {}).items()
    ]
    if attached:
        issues.append(
            issue(
                "attached_sources_not_supported",
                "附加源码根未纳入隔离副本；请将构建所需内容整理到单一主源码根后再创建代码工作。",
                "",
                "error",
            )
        )
    issues.extend(item for row in projects + solutions for item in row["issues"])
    counts = Counter(
        item["status"]
        for row in projects
        for key in ("references", "project_references", "imports")
        for item in row[key]
    )
    framework_set = sorted(
        {framework for row in projects for framework in row["target_frameworks"]}
    )
    requirements = [
        "先在隔离环境中验证未修改的源码基线，再判断修改带来的错误。",
        "静态扫描不加载导入文件、不求值 MSBuild 条件；依赖存在不代表版本或 ABI 正确。",
        "按所选配置和平台准备编译器、目标框架引用程序集、私有 SDK 与固定版本依赖。",
    ]
    if any(row.get("requires_windows") for row in projects):
        requirements.append(
            "声明包含 .NET Framework 或 Windows 桌面目标；"
            "Linux 应用服务器需连接独立 Windows 隔离构建节点，"
            "不能以 Linux 构建代替该项目验收。"
        )
    if any(row["package_references"] or row.get("packages_config") for row in projects):
        requirements.append(
            "在可信镜像准备阶段恢复 NuGet 包并固定镜像摘要；沙箱执行时不开放网络包源。"
        )
    blocked = any(item["severity"] == "error" for item in issues)
    return {
        "schema_version": 1,
        "status": "blocked"
        if blocked
        else "needs_baseline"
        if projects or solutions
        else "no_build_files",
        "buildable": None,
        "primary_only": True,
        "attached_sources": attached,
        "projects": projects,
        "solutions": solutions,
        "summary": {
            "projects": len(projects),
            "solutions": len(solutions),
            "legacy_projects": sum(row["style"] == "legacy" for row in projects),
            "sdk_projects": sum(row["style"] == "sdk" for row in projects),
            "target_frameworks": framework_set,
            "dependency_states": dict(sorted(counts.items())),
            "errors": sum(item["severity"] == "error" for item in issues),
            "warnings": sum(item["severity"] == "warning" for item in issues),
        },
        "requirements": requirements,
        "issues": issues,
        "baseline_steps": [
            "选择解决方案或项目以及 Configuration / Platform；确认隔离执行平台匹配目标。",
            "准备并固定构建镜像、私有依赖和包缓存，检查源码根外及绝对路径依赖。",
            "先执行未修改基线的编译和测试，保存命令、源码版本、镜像摘要、退出码与日志。",
            "在同一环境和配置验证修改副本，对照基线结果；实际设备另行验收。",
        ],
    }


__all__ = ["inspect_project"]
