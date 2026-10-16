"""解决方案只作为文本清单读取，不加载其中项目或执行任何脚本。"""

import re

from .paths import PROJECT_SUFFIXES, display, reference
from .projects import issue
from .xml_files import MetadataError, text_file


def solution_file(root, path):
    relative = display(path.relative_to(root).as_posix())
    row = {"path": relative, "projects": [], "configurations": [], "issues": []}
    try:
        content = text_file(root, path)
    except MetadataError as error:
        row["issues"].append(issue("solution_parse_error", str(error), relative, "error"))
        return row
    if "Microsoft Visual Studio Solution File" not in content[:1000]:
        row["issues"].append(
            issue(
                "invalid_solution_document",
                "未识别为 Visual Studio 解决方案文件。",
                relative,
                "error",
            )
        )
        return row
    for name, value in re.findall(
        r'^\s*Project\("[^"\r\n]+"\)\s*=\s*"([^"\r\n]*)",\s*"([^"\r\n]+)"', content, re.MULTILINE
    ):
        if not any(value.lower().endswith(suffix) for suffix in PROJECT_SUFFIXES):
            continue
        item = {"name": display(name), **reference(root, path.parent, value)}
        row["projects"].append(item)
        if item["status"] != "exists":
            row["issues"].append(
                issue(
                    "solution_project_unavailable",
                    "解决方案中的项目缺失、位于根外或需要属性求值；不能据此完成基线构建。",
                    relative,
                    "error",
                )
            )
    sections = re.findall(
        r"GlobalSection\(SolutionConfigurationPlatforms\)[^\r\n]*[\r\n]+(.*?)EndGlobalSection",
        content,
        re.DOTALL,
    )
    row["configurations"] = sorted(
        {
            display(line.split("=", 1)[0].strip())
            for section in sections
            for line in section.splitlines()
            if "=" in line
        }
    )
    return row
