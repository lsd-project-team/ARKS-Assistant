"""架构依赖回归：防止业务规则再次依赖启动、HTTP 或存储实现。"""

import ast

from app.core.config import PROJECT_ROOT


def imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)


def test_handover_domain_has_no_technology_or_other_business_dependencies():
    forbidden = []
    folder = PROJECT_ROOT / "backend/app/modules/handover/domain"
    for path in folder.rglob("*.py"):
        for module in imports(path):
            if module.split(".")[0] in {"fastapi", "sqlalchemy", "langchain", "httpx"}:
                forbidden.append((path.name, module))
            if module.startswith("app.") and not module.startswith(
                ("app.core.", "app.modules.handover.domain.")
            ):
                forbidden.append((path.name, module))
    assert not forbidden, forbidden


def test_business_modules_do_not_import_application_bootstrap():
    folder = PROJECT_ROOT / "backend/app/modules"
    forbidden = [
        (str(path.relative_to(folder)), module)
        for path in folder.rglob("*.py")
        for module in imports(path)
        if module in {"app.main", "app.bootstrap"}
    ]
    assert not forbidden, forbidden


def test_handover_use_cases_depend_on_ports_instead_of_technology_adapters():
    folder = PROJECT_ROOT / "backend/app/modules/handover/application"
    forbidden = []
    for path in folder.rglob("*.py"):
        for module in imports(path):
            if module.split(".")[0] in {"fastapi", "sqlalchemy", "httpx", "langchain"}:
                forbidden.append((path.name, module))
            if module.startswith(
                (
                    "app.infrastructure.",
                    "app.modules.handover.infrastructure.",
                    "app.modules.handover.interfaces.",
                )
            ):
                forbidden.append((path.name, module))
    assert not forbidden, forbidden
