"""源码报告可重用，但源码、分析器与授权目录变化后不能命中旧结果。"""

import gzip
import hashlib
import json

import pytest

from app.modules.action_timing import source_report_cache
from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.collection import SourceCollection
from app.modules.source_analysis.workspace import Workspace


def sample(tmp_path, delay=12):
    root = tmp_path / "source"
    root.mkdir()
    path = root / "Demo.cs"
    path.write_text(
        f"class Demo : ActionNode {{public int DoWork(){{Thread.Sleep({delay});return 0;}}}}",
        encoding="utf-8",
    )
    return Workspace(root), path, tmp_path / "cache"


def delay(report):
    return next(row for row in report["rows"] if row["class_name"] == "Demo")["known_delay_min_ms"]


def test_new_service_reuses_the_same_source_report_detail_coverage_and_csv(tmp_path, monkeypatch):
    workspace, _, directory = sample(tmp_path)
    first = SourceTiming(workspace, directory)
    report, summary, coverage, exported = (
        first.report(),
        first.summary(),
        first.coverage(),
        first.export_csv(),
    )
    assert first.disk_cache.path.is_file()

    def unexpected_build(*args):
        pytest.fail("源码未变且缓存完整时不应重新展开全部方法")

    monkeypatch.setattr(SourceTiming, "_build", unexpected_build)
    second = SourceTiming(Workspace(workspace.root), directory)
    assert second.report() == report
    assert second.summary() == summary
    assert second.coverage() == coverage
    assert second.export_csv() == exported
    assert second.detail(report["rows"][0]["id"]) == report["rows"][0]


def test_source_change_invalidates_both_memory_and_disk_results(tmp_path):
    workspace, path, directory = sample(tmp_path)
    first = SourceTiming(workspace, directory)
    before = first.report()
    path.write_text(
        path.read_text(encoding="utf-8").replace("Sleep(12)", "Sleep(21)"), encoding="utf-8"
    )
    updated = first.report()
    assert delay(updated) == 21 and updated["source_revision"] != before["source_revision"]
    assert delay(SourceTiming(Workspace(workspace.root), directory).report()) == 21
    assert len(list(directory.glob("*.json.gz"))) == 1


def test_added_uncompiled_file_invalidates_coverage_even_when_compiled_code_is_unchanged(tmp_path):
    workspace, _, directory = sample(tmp_path)
    (workspace.root / "AKRS.ZX2200.csproj").write_text(
        '<Project><ItemGroup><Compile Include="Demo.cs"/></ItemGroup></Project>', encoding="utf-8"
    )
    service = SourceTiming(workspace, directory)
    before = service.coverage()
    (workspace.root / "Unused.cs").write_text("class Unused {}", encoding="utf-8")
    after = service.coverage()
    assert after["source_revision"] != before["source_revision"]
    assert (
        next(row for row in after["files"] if row["path"] == "Unused.cs")["status"]
        == "not_compiled"
    )
    assert delay(SourceTiming(Workspace(workspace.root), directory).report()) == 12


def test_changed_dependency_source_is_recalculated_instead_of_using_cached_delay(tmp_path):
    workspace, path, directory = sample(tmp_path)
    path.write_text(
        "class Demo : ActionNode {public int DoWork(){Driver.Wait();return 0;}}", encoding="utf-8"
    )
    (workspace.root / "AKRS.ZX2200.csproj").write_text(
        '<Project><ItemGroup><Compile Include="Demo.cs"/>'
        '<ProjectReference Include="Driver/Driver.csproj"/></ItemGroup></Project>',
        encoding="utf-8",
    )
    package = workspace.root / "Driver"
    package.mkdir()
    (package / "Driver.csproj").write_text(
        "<Project><PropertyGroup><AssemblyName>Driver</AssemblyName></PropertyGroup>"
        '<ItemGroup><Compile Include="Driver.cs"/></ItemGroup></Project>',
        encoding="utf-8",
    )
    dependency = package / "Driver.cs"
    dependency.write_text(
        "class Driver {public static void Wait(){Thread.Sleep(7);}}", encoding="utf-8"
    )
    first = SourceTiming(workspace, directory)
    before = first.report()
    assert delay(before) == 7
    dependency.write_text(
        dependency.read_text(encoding="utf-8").replace("Sleep(7)", "Sleep(19)"), encoding="utf-8"
    )
    after = SourceTiming(workspace, directory).report()
    assert delay(after) == 19 and after["source_revision"] != before["source_revision"]


def test_changed_hardware_dll_fingerprint_invalidates_the_cache(tmp_path):
    workspace, _, directory = sample(tmp_path)
    (workspace.root / "AKRS.ZX2200.csproj").write_text(
        '<Project><ItemGroup><Compile Include="Demo.cs"/>'
        '<Reference Include="AKRS.Galaxy2.LogicHardware"><HintPath>Hardware.dll</HintPath>'
        "</Reference></ItemGroup></Project>",
        encoding="utf-8",
    )
    artifact = workspace.root / "Hardware.dll"
    artifact.write_bytes(b"unverified package v1")
    before = SourceTiming(workspace, directory).report()
    artifact.write_bytes(b"unverified package v2")
    after = SourceTiming(workspace, directory).report()
    assert after["source_revision"] != before["source_revision"]
    assert (
        after["source_dependencies"][0]["sha256"]
        == hashlib.sha256(artifact.read_bytes()).hexdigest()
    )
    assert delay(after) == 12


def test_analyzer_change_rebuilds_a_report_with_unchanged_business_sources(tmp_path, monkeypatch):
    workspace, _, directory = sample(tmp_path)
    SourceTiming(workspace, directory).report()
    original = SourceTiming._build
    built = []

    def measured(self, index):
        built.append(index.revision)
        return original(self, index)

    monkeypatch.setattr(source_report_cache, "engine_signature", lambda: "new-analyzer")
    monkeypatch.setattr(SourceTiming, "_build", measured)
    assert delay(SourceTiming(workspace, directory).report()) == 12
    assert len(built) == 1


@pytest.mark.parametrize("component", ["python", "parser"])
def test_runtime_and_parser_versions_are_included_in_the_analyzer_fingerprint(
    component, monkeypatch
):
    before = source_report_cache.engine_signature()
    if component == "python":
        monkeypatch.setattr(source_report_cache.sys, "version", "changed Python runtime")
    else:
        original = source_report_cache.version
        monkeypatch.setattr(
            source_report_cache,
            "version",
            lambda name: (
                "changed parser version" if name == "tree-sitter-c-sharp" else original(name)
            ),
        )
    assert source_report_cache.engine_signature() != before


def test_missing_runtime_package_metadata_disables_only_disk_caching(tmp_path, monkeypatch):
    workspace, _, directory = sample(tmp_path)

    def missing(name):
        raise source_report_cache.PackageNotFoundError(name)

    monkeypatch.setattr(source_report_cache, "version", missing)
    service = SourceTiming(workspace, directory)
    assert delay(service.report()) == 12 and not service.disk_cache.enabled
    assert not directory.exists()


@pytest.mark.parametrize(
    "damage",
    ["not-gzip", "truncated", "deflate-corruption", "bad-header", "wrong-format", "bad-report"],
)
def test_corrupt_or_incompatible_cache_falls_back_to_real_source_calculation(tmp_path, damage):
    workspace, _, directory = sample(tmp_path)
    first = SourceTiming(workspace, directory)
    first.report()
    path = first.disk_cache.path
    if damage == "not-gzip":
        path.write_bytes(b"not a report")
    elif damage == "truncated":
        path.write_bytes(path.read_bytes()[:18])
    elif damage == "deflate-corruption":
        compressed = bytearray(gzip.compress(b"cache payload", mtime=0))
        compressed[10] = 0x06  # reserved DEFLATE block type
        path.write_bytes(compressed)
    else:
        metadata = first.disk_cache.metadata(first.signature)
        if damage == "wrong-format":
            metadata["format"] += 1
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            stream.write(("invalid" if damage == "bad-header" else json.dumps(metadata)) + "\n")
            json.dump({"rows": []}, stream)
    second = SourceTiming(workspace, directory)
    assert delay(second.report()) == 12
    assert second.disk_cache.load(second.signature) is not None


def test_read_only_or_unusable_cache_location_does_not_prevent_analysis(tmp_path):
    workspace, _, directory = sample(tmp_path)
    directory.write_text("cache parent is a file", encoding="utf-8")
    assert delay(SourceTiming(workspace, directory).report()) == 12


def test_interrupted_cache_write_preserves_the_previous_complete_file(tmp_path, monkeypatch):
    workspace, _, directory = sample(tmp_path)
    service = SourceTiming(workspace, directory)
    report = service.report()
    before = service.disk_cache.path.read_bytes()

    def interrupted(*args, **kwargs):
        raise OSError("simulated interrupted write")

    monkeypatch.setattr(source_report_cache.json, "dump", interrupted)
    service.disk_cache.save(service.signature, report)
    assert service.disk_cache.path.read_bytes() == before
    assert not list(directory.glob("*.tmp"))
    assert delay(SourceTiming(workspace, directory).report()) == 12


def test_cache_is_never_written_inside_a_source_root(tmp_path):
    workspace, path, _ = sample(tmp_path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    directory = workspace.root / "cache"
    service = SourceTiming(workspace, directory)
    assert delay(service.report()) == 12
    assert not directory.exists() and not service.disk_cache.enabled
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_different_primary_roots_do_not_share_cache_files(tmp_path):
    workspace, _, directory = sample(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    (other / "Demo.cs").write_text(
        "class Demo : ActionNode {public int DoWork(){Thread.Sleep(27);return 0;}}",
        encoding="utf-8",
    )
    first, second = SourceTiming(workspace, directory), SourceTiming(Workspace(other), directory)
    assert delay(first.report()) == 12 and delay(second.report()) == 27
    assert first.disk_cache.path != second.disk_cache.path


def test_attached_roots_are_part_of_the_cache_identity_and_read_only_boundary(tmp_path):
    workspace, _, directory = sample(tmp_path)
    attached = tmp_path / "package"
    attached.mkdir()
    (attached / "Other.cs").write_text("class Other {}", encoding="utf-8")
    folders = [{"source_id": "package", "label": "包源码", "root": str(attached)}]
    combined = SourceCollection(workspace.root, folders)
    first = SourceTiming(workspace, directory)
    second = SourceTiming(combined, directory)
    assert first.disk_cache.path != second.disk_cache.path
    assert delay(second.report()) == 12
    forbidden = SourceTiming(combined, attached / "cache")
    assert delay(forbidden.report()) == 12 and not (attached / "cache").exists()
