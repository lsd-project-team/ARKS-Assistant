"""全目录加载必须以工程引用和已授权目录为边界，不能混入副本和包内同名类。"""

import hashlib

from app.modules.action_timing.source_index import SourceIndex, walk
from app.modules.action_timing.source_scope import load_scope
from app.modules.source_analysis.collection import SourceCollection
from app.modules.source_analysis.workspace import Workspace


def project(folder, assembly, files, references=""):
    folder.mkdir(parents=True, exist_ok=True)
    includes = "".join(f'<Compile Include="{name}" />' for name in files)
    path = folder / f"{assembly}.csproj"
    path.write_text(
        f"<Project><PropertyGroup><AssemblyName>{assembly}</AssemblyName></PropertyGroup><ItemGroup>{includes}{references}</ItemGroup></Project>",
        encoding="utf-8",
    )
    for name, content in files.items():
        (folder / name).write_text(content, encoding="utf-8")
    return path


def index_sources(*sources):
    return SourceIndex(
        [
            {
                "path": f"{n}.cs",
                "content": source,
                "version": hashlib.sha256(source.encode()).hexdigest(),
                "project": str(n),
            }
            for n, source in enumerate(sources)
        ]
    )


def test_collection_package_fingerprint_tracks_the_referenced_binary(tmp_path):
    folder = tmp_path / "AKRS.ZX2200"
    project(
        folder,
        "AKRS.ZX2200",
        {"Demo.cs": "class Demo{}"},
        '<Reference Include="AKRS.Galaxy2.Infrastructure">'
        "<HintPath>libs/AKRS.Galaxy2.Infrastructure.dll</HintPath></Reference>",
    )
    binary = folder / "libs/AKRS.Galaxy2.Infrastructure.dll"
    binary.parent.mkdir()
    binary.write_bytes(b"first-version")
    before = load_scope(Workspace(tmp_path))
    assert before.references[0]["sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest()
    binary.write_bytes(b"different-version")
    after = load_scope(Workspace(tmp_path))
    assert before.revision != after.revision
    assert after.references[0]["sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest()


def test_project_compile_list_and_transitive_dependencies_exclude_unbuilt_copies(tmp_path):
    main = tmp_path / "AKRS.ZX2200"
    project(
        main,
        "AKRS.ZX2200",
        {"Main.cs": "class Main {}"},
        '<ProjectReference Include="../Machine/Machine.csproj" />',
    )
    project(
        tmp_path / "Machine",
        "Machine",
        {"Signal.cs": "class Signal {}"},
        '<ProjectReference Include="../Leaf/Leaf.csproj" />',
    )
    project(tmp_path / "Leaf", "Leaf", {"Leaf.cs": "class Leaf {}"})
    project(tmp_path / "output/AKRS.ZX2200", "AKRS.ZX2200", {"Other.cs": "class Wrong {}"})
    (main / "Old.cs").write_text("class NotCompiled {}", encoding="utf-8")
    result = load_scope(Workspace(tmp_path))
    assert {row["path"] for row in result.documents} == {
        "AKRS.ZX2200/Main.cs",
        "Machine/Signal.cs",
        "Leaf/Leaf.cs",
    }
    assert [row["role"] for row in result.projects] == ["business", "dependency", "dependency"]
    assert (
        next(row for row in result.files if row["path"] == "AKRS.ZX2200/Old.cs")["status"]
        == "not_compiled"
    )
    before = result.revision
    (main / "AKRS.ZX2200.csproj").write_text(
        (main / "AKRS.ZX2200.csproj").read_text().replace("Main.cs", "Old.cs"), encoding="utf-8"
    )
    assert load_scope(Workspace(tmp_path)).revision != before


def test_sibling_outside_workspace_is_not_read_and_attached_dependency_is_resolved(tmp_path):
    main = tmp_path / "AKRS.ZX2200"
    project(
        main,
        "AKRS.ZX2200",
        {"Main.cs": "class Main {}"},
        '<ProjectReference Include="../Machine/Machine.csproj" />',
    )
    dependency = tmp_path / "other/Machine"
    project(dependency, "Machine", {"Signal.cs": "class Signal {}"})
    limited = load_scope(Workspace(main))
    assert len(limited.documents) == 1
    assert limited.references[0]["status"] == "missing"
    combined = load_scope(
        SourceCollection(main, [{"source_id": "machine", "label": "依赖", "root": str(dependency)}])
    )
    assert {row["path"] for row in combined.documents} == {"Main.cs", "@sources/machine/Signal.cs"}
    assert combined.references[0]["status"] == "source"


def test_same_class_names_across_packages_do_not_merge_and_var_uses_factory_type():
    index = index_sources(
        "namespace Business { class Driver { "
        "public static Driver GetInstance() { return null; } "
        "public void Wait() { Thread.Sleep(12); } } "
        "class Demo { void Run() { var driver = Driver.GetInstance(); driver.Wait(); } } }",
        "namespace Package { class Driver { public void Wait() { Thread.Sleep(999); } } }",
    )
    method = index.by_method[("Demo", "Run")][0]
    call = next(
        node
        for node in walk(method.body)
        if node.type == "invocation_expression" and node.text == b"driver.Wait()"
    )
    target = index.resolve(call, method)
    assert target is not None and target.unit.path == "0.cs"
    assert len(index.type_names["Driver"]) == 2


def test_inherited_method_and_typed_overload_resolve_without_guessing():
    index = index_sources(
        "class Base { public void Wait(int n) {} public void Wait(string s) {} } "
        "class Derived : Base { public void Run() { this.Wait(5); } }"
    )
    method = index.by_method[("Derived", "Run")][0]
    call = next(node for node in walk(method.body) if node.type == "invocation_expression")
    assert index.resolve(call, method).parameters[0][1] == "int"
