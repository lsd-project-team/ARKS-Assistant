"""提取声明的框架、配置和直接依赖；不执行 MSBuild 属性或条件。"""

import re

from .paths import display, reference
from .xml_files import MetadataError, child_text, elements, values, xml_file


def issue(code, message, path, severity="warning"):
    return {"code": code, "severity": severity, "path": path, "message": message}


def project_file(root, path):
    relative = display(path.relative_to(root).as_posix())
    row = {
        "path": relative,
        "style": "unknown",
        "target_frameworks": [],
        "configurations": [],
        "platforms": [],
        "references": [],
        "project_references": [],
        "package_references": [],
        "imports": [],
        "issues": [],
    }
    try:
        document = xml_file(root, path)
    except MetadataError as error:
        row["issues"].append(issue("project_parse_error", str(error), relative, "error"))
        return row
    if document.tag.split("}")[-1] != "Project":
        row["issues"].append(
            issue("invalid_project_document", "XML 根节点不是 Project。", relative, "error")
        )
        return row
    sdk = document.get("Sdk") or next((item.get("Name") for item in elements(document, "Sdk")), "")
    row["style"] = "sdk" if sdk else "legacy"
    row["sdk"] = display(sdk)
    frameworks = values(document, "TargetFramework") + values(document, "TargetFrameworks")
    row["target_frameworks"] = sorted(
        {part.strip() for value in frameworks for part in value.split(";") if part.strip()}
        | set(values(document, "TargetFrameworkVersion"))
    )
    row["framework_identifier"] = values(document, "TargetFrameworkIdentifier")
    row["requires_windows"] = (
        bool(values(document, "TargetFrameworkVersion"))
        or any(
            "-windows" in framework.lower() or re.fullmatch(r"net[1-4]\d{1,2}", framework.lower())
            for framework in row["target_frameworks"]
        )
        or any(
            value.lower() == "true"
            for tag in ("UseWindowsForms", "UseWPF")
            for value in values(document, tag)
        )
    )
    row["configurations"], row["platforms"] = configurations(document)
    for element in elements(document, "Reference"):
        dependency = {
            "name": display((element.get("Include") or "").split(",")[0]),
            **reference(root, path.parent, child_text(element, "HintPath")),
        }
        row["references"].append(dependency)
    for tag, key in (("ProjectReference", "project_references"), ("Import", "imports")):
        attribute = "Include" if tag == "ProjectReference" else "Project"
        row[key] = [
            reference(root, path.parent, item.get(attribute)) for item in elements(document, tag)
        ]
    row["package_references"] = [
        {
            "name": display(item.get("Include") or item.get("Update") or ""),
            "version": display(item.get("Version") or child_text(item, "Version")),
        }
        for item in elements(document, "PackageReference")
    ]
    add_packages_config(root, path, row)
    if any(item.get("Condition") for item in document.iter()):
        row["issues"].append(
            issue(
                "conditions_not_evaluated",
                "项目含条件声明；框架、配置和依赖为所有声明的并集，"
                "实际选择须由隔离环境中的 MSBuild 确认。",
                relative,
            )
        )
    if not row["target_frameworks"]:
        row["issues"].append(
            issue(
                "framework_not_declared",
                "未直接声明目标框架；可能由导入文件提供，不能据此判断构建环境。",
                relative,
            )
        )
    if row["package_references"] or row.get("packages_config"):
        row["issues"].append(
            issue(
                "package_restore_required",
                "需要在可信镜像准备阶段恢复并固定 NuGet 包；"
                "执行沙箱关闭网络，不在此扫描中访问包源。",
                relative,
            )
        )
    add_reference_issues(row)
    return row


def configurations(document):
    declared = {
        tag: values(document, tag)
        for tag in ("Configuration", "Configurations", "Platform", "Platforms")
    }
    configurations = {
        part.strip()
        for value in declared["Configuration"] + declared["Configurations"]
        for part in value.split(";")
        if part.strip()
    }
    platforms = {
        part.strip()
        for value in declared["Platform"] + declared["Platforms"]
        for part in value.split(";")
        if part.strip()
    }
    for group in elements(document, "PropertyGroup"):
        condition = group.get("Condition", "")
        for expression, selected in re.findall(
            r"['\"]([^'\"]+)['\"]\s*==\s*['\"]([^'\"]+)['\"]", condition
        ):
            compact = expression.replace(" ", "").lower()
            if compact == "$(configuration)|$(platform)" and "|" in selected:
                configuration, platform = selected.split("|", 1)
                configurations.add(display(configuration))
                platforms.add(display(platform))
            elif compact == "$(configuration)":
                configurations.add(display(selected))
            elif compact == "$(platform)":
                platforms.add(display(selected))
    return sorted(configurations), sorted(platforms)


def add_packages_config(root, path, row):
    package_path = path.parent / "packages.config"
    state = reference(root, path.parent, "packages.config")
    if state["status"] == "missing":
        return
    row["packages_config"] = state
    try:
        document = xml_file(root, package_path)
        row["packages_config"]["packages"] = [
            {
                "name": display(item.get("id", "")),
                "version": display(item.get("version", "")),
                "target_framework": display(item.get("targetFramework", "")),
            }
            for item in elements(document, "package")
        ]
    except MetadataError as error:
        row["issues"].append(issue("packages_parse_error", str(error), state["path"], "error"))


def add_reference_issues(row):
    messages = {
        "missing": ("missing_dependency", "源码根内的直接依赖文件缺失。", "error"),
        "external": (
            "external_dependency",
            "依赖指向源码根外，未读取；必须在可信构建环境补齐并消除本机路径依赖。",
            "error",
        ),
        "linked": (
            "linked_dependency",
            "依赖为链接或目录联接，未跟随；隔离副本不包含该内容。",
            "error",
        ),
        "unreadable": ("unreadable_dependency", "依赖无法检查。", "error"),
        "invalid": ("invalid_dependency", "依赖路径无效。", "error"),
    }
    for kind in ("references", "project_references", "imports"):
        for item in row[kind]:
            if item["status"] in messages:
                code, message, severity = messages[item["status"]]
                row["issues"].append(issue(code, message, row["path"], severity))
    if any(item["status"] == "environment" for item in row["references"]):
        row["issues"].append(
            issue(
                "assembly_resolution_required",
                "无 HintPath 的程序集依赖须由目标框架引用包、GAC 或已安装 SDK 解析；"
                "未检查宿主环境。",
                row["path"],
            )
        )
    if any(
        item["absolute"]
        for kind in ("references", "project_references", "imports")
        for item in row[kind]
    ):
        row["issues"].append(
            issue(
                "absolute_path_dependency",
                "项目含绝对依赖路径；本机路径不能直接搬到 Linux 或远程 Windows 构建节点。",
                row["path"],
            )
        )
