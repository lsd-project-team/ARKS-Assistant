"""用小型真实文件验证副本容量边界，避免为 1 GB 上限分配巨量测试数据。"""

import pytest

from app.modules.code_changes import files


def test_default_copy_capacity_supports_one_gigabyte_and_keeps_file_limit():
    assert files.MAX_COPY_BYTES == 1_000_000_000
    assert files.MAX_COPY_FILES == 30000


@pytest.mark.parametrize("total_bytes", [15, 16, 17])
def test_snapshot_enforces_total_bytes_including_binary_resources(
    tmp_path, monkeypatch, total_bytes
):
    monkeypatch.setattr(files, "MAX_COPY_BYTES", 16)
    source = tmp_path / "source"
    source.mkdir()
    contents = {"Program.cs": b"start", "resource.dat": b"\x00" * (total_bytes - 5)}
    for relative, content in contents.items():
        (source / relative).write_bytes(content)
    base, work = tmp_path / "base", tmp_path / "work"

    if total_bytes > 16:
        with pytest.raises(ValueError, match="16 字节或 30000 个文件"):
            files.copy_snapshot(source, base, work)
        assert not base.exists() and not work.exists()
    else:
        manifest = files.copy_snapshot(source, base, work)
        assert set(manifest) == set(contents)
        for root in (base, work):
            assert {name: (root / name).read_bytes() for name in contents} == contents
    assert {name: (source / name).read_bytes() for name in contents} == contents


@pytest.mark.parametrize("file_count", [1, 2, 3])
def test_inventory_keeps_file_count_boundary(tmp_path, monkeypatch, file_count):
    monkeypatch.setattr(files, "MAX_COPY_FILES", 2)
    for index in range(file_count):
        (tmp_path / f"source-{index}.cs").write_bytes(b"x")
    if file_count > 2:
        with pytest.raises(ValueError, match="1,000,000,000 字节或 2 个文件"):
            files.inventory(tmp_path)
    else:
        assert set(files.inventory(tmp_path)) == {
            f"source-{index}.cs" for index in range(file_count)
        }


def test_excluded_files_do_not_consume_copy_capacity(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "MAX_COPY_BYTES", 1)
    monkeypatch.setattr(files, "MAX_COPY_FILES", 1)
    (tmp_path / "Program.cs").write_bytes(b"x")
    excluded = tmp_path / ".git"
    excluded.mkdir()
    (excluded / "objects").write_bytes(b"excluded")

    assert set(files.inventory(tmp_path)) == {"Program.cs"}
