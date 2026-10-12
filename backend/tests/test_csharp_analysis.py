import pytest

from app.csharp_analysis import HELPER, CSharpAnalysis
from app.workspace import Workspace


def test_roslyn_overload_interface_deferred_incremental_and_unknown(tmp_path):
    assert HELPER.is_file(), "Setup.ps1 必须准备真实 Roslyn 分析器"
    (tmp_path / "Sample.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"/>')
    first = tmp_path / "Entry.cs"
    first.write_text("""interface IWorker { void Run(int value); }
class Worker : IWorker {
 public void Run(int value) {}
 public void Run(string value) {}
 public void Start(IWorker worker) {
  if (worker == null) return;
  worker.Run(1);
  Run("text");
  System.Action action = () => Run(2);
 }
}""")
    (tmp_path / "Other.cs").write_text("class Other { void Go(Worker x) { x.Run(3); } }")
    index = CSharpAnalysis(Workspace(tmp_path))
    try:
        result = index.analyze("Entry.cs", 7)
        assert result["stats"]["reparsed_files"] == 2
        calls = result["calls"]
        assert calls[0]["target"]["symbol"] == "IWorker.Run(int)"
        assert calls[0]["possible_implementations"][0]["symbol"] == "Worker.Run(int)"
        assert calls[1]["target"]["symbol"] == "Worker.Run(string)"
        assert calls[2]["deferred"] and calls[2]["target"]["symbol"] == "Worker.Run(int)"
        assert any(row["kind"] == "ReturnStatement" for row in result["control_flow"])
        cached = index.analyze("Entry.cs", 3)
        assert cached["stats"]["reparsed_files"] == cached["stats"]["rebuilt_projects"] == 0
        assert {item["path"] for item in cached["callers"]} == {"Other.cs", "Entry.cs"}
        first.write_text(first.read_text().replace('Run("text")', "Missing.Call()"))
        changed = index.analyze("Entry.cs", 7)
        assert changed["stats"]["reparsed_files"] == 1
        assert changed["calls"][1]["resolved"] is False
        assert changed["diagnostics"] and changed["completeness"].startswith("partial")
    finally:
        index.close()
    with pytest.raises(ValueError):
        index.analyze("../outside.cs", 1)
