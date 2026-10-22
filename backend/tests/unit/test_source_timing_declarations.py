"""生成文件只提供字段类型；不能把窗体布局当作设备动作执行。"""

import hashlib

from app.modules.action_timing.source_estimator import Estimator
from app.modules.action_timing.source_index import SourceIndex
from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace
from tests.unit.test_source_timing_scope import project


def document(path, content, project_name="main"):
    return {
        "path": path,
        "content": content,
        "version": hashlib.sha256(content.encode()).hexdigest(),
        "project": project_name,
    }


def test_designer_field_follows_source_method_without_running_layout_or_field_initializer():
    index = SourceIndex(
        [
            document(
                "Main.cs",
                """partial class Demo { public void Run() { driver.Pause(); } }
            class Driver { public Driver() { Thread.Sleep(500); }
                public void Pause() { Thread.Sleep(9); } }""",
            )
        ],
        [
            document(
                "Main.Designer.cs",
                """partial class Demo {
            Driver driver = new Driver();
            void InitializeComponent() { Thread.Sleep(999); } }""",
            )
        ],
    )
    result = Estimator(index).estimate(index.by_method[("Demo", "Run")][0])
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 9
    assert result["total_ms"] == 9
    assert ("Demo", "InitializeComponent") not in index.by_method
    assert not index.classes["Demo"].initializers


def test_generated_field_type_uses_its_own_imports_when_source_types_share_a_name():
    index = SourceIndex(
        [
            document(
                "Main.cs",
                """using First; namespace UI {
            partial class Demo { public void Run() { worker.Pause(); } } }
            namespace First { class Worker { public void Pause() { Thread.Sleep(999); } } }
            namespace Second { class Worker { public void Pause() { Thread.Sleep(17); } } }""",
            )
        ],
        [
            document(
                "Main.Designer.cs",
                """using Second;
            namespace UI { partial class Demo { Worker worker; } }""",
            )
        ],
    )
    result = Estimator(index).estimate(index.by_method[("Demo", "Run")][0])
    assert result["total_ms"] == 17


def test_generated_fields_do_not_merge_other_projects_or_namespaces():
    index = SourceIndex(
        [document("Main.cs", "namespace UI { partial class Demo { void Run() {} } }")],
        [
            document(
                "Other.cs", "namespace UI { partial class Demo { Driver wrongProject; } }", "other"
            ),
            document("Else.cs", "namespace Else { partial class Demo { Driver wrongNamespace; } }"),
        ],
    )
    assert index.classes["Demo"].types == {}


def test_compiled_designer_change_invalidates_report_but_excluded_copy_does_not_bind(tmp_path):
    main = tmp_path / "AKRS.ZX2200"
    project(
        main,
        "AKRS.ZX2200",
        {
            "Main.cs": """partial class DemoActionNode : ActionNode {
            public int DoWork() { driver.Pause(); return 0; } }
            class First { public void Pause() { Thread.Sleep(9); } }
            class Second { public void Pause() { Thread.Sleep(17); } }""",
            "Main.Designer.cs": "partial class DemoActionNode { First driver; }",
        },
    )
    (main / "Uncompiled.Designer.cs").write_text(
        "partial class DemoActionNode { Second driver; }", encoding="utf-8"
    )
    service = SourceTiming(Workspace(tmp_path))
    first = service.report()
    row = next(row for row in first["rows"] if row["class_name"] == "DemoActionNode")
    assert row["total_ms"] == 9
    assert first["source_files"] == 1
    assert first["source_coverage"]["generated"] == 1
    (main / "Main.Designer.cs").write_text(
        "partial class DemoActionNode { Second driver; }", encoding="utf-8"
    )
    second = service.report()
    row = next(row for row in second["rows"] if row["class_name"] == "DemoActionNode")
    assert row["total_ms"] == 17
    assert second["source_revision"] != first["source_revision"]
