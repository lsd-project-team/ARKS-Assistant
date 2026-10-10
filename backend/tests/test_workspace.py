import pytest

from app.source_backend import SourceBackend
from app.workspace import decode_source


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "a/../../secret",
        "C:/Windows/test",
        "/etc/passwd",
        "a/../x",
        ".git/config",
        "obj/test",
    ],
)
def test_rejects_escape_and_generated_paths(services, path):
    workspace = services[2]
    with pytest.raises(ValueError):
        workspace.resolve(path)


def test_symlink_cannot_escape(services, tmp_path):
    workspace = services[2]
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    link = workspace.root / "linked.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Windows 未启用创建符号链接权限")
    with pytest.raises(ValueError):
        workspace.read("linked.txt")


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16", "gb18030"])
def test_chinese_encoding_preserved(encoding):
    text = "// 中文注释\nclass 测试 {}"
    assert decode_source(text.encode(encoding))[0] == text


def test_binary_rejected():
    with pytest.raises(ValueError):
        decode_source(b"abc\x00def")


def test_symbols_search_and_readonly_backend(services):
    workspace = services[2]
    symbols = workspace.symbols("Program.cs")["symbols"]
    assert {symbol["name"] for symbol in symbols} == {"Program", "Main"}
    assert workspace.search("Main")["matches"][0]["line"] == 2
    backend = SourceBackend(workspace)
    assert backend.write("/Program.cs", "overwritten").error
    assert backend.read("/Program.cs", offset=1, limit=1).start_line == 2
    assert "Main" in workspace.read("Program.cs")["content"]


def test_search_legacy_chinese_file_preserves_text(services):
    workspace = services[2]
    text = "// 校准入口 Calibration\nclass Legacy {}"
    (workspace.root / "Legacy.cs").write_bytes(text.encode("gb18030"))
    for query in ("校准", "Calibration"):
        matches = workspace.search(query, "*.cs")["matches"]
        assert matches == [{"path": "Legacy.cs", "line": 1, "text": text.splitlines()[0]}]
