"""从真实容器基线到审核交付，只有显式提供可信镜像才运行。"""

import io
import json
import os
from zipfile import ZipFile

import pytest

from app.modules.code_changes import CodeChanges
from app.modules.code_changes.delivery import delivery_package, review_change

IMAGE = os.environ.get("ARKS_TEST_EXECUTION_IMAGE")
pytestmark = pytest.mark.skipif(not IMAGE, reason="须显式提供可信固定镜像进行隔离交付验收")


async def test_real_sandbox_baseline_edit_test_review_and_delivery(services):
    paths, database, workspace, *_ = services
    (workspace.root / "calc.py").write_text("def add(a, b):\n return a + b\n", encoding="utf-8")
    before_test = (
        "import unittest\nimport calc\nclass TestCalc(unittest.TestCase):\n"
        " def test_add(self):\n  self.assertEqual(calc.add(2, 3), 5)\n"
    )
    (workspace.root / "test_calc.py").write_text(before_test, encoding="utf-8")
    original = {name: (workspace.root / name).read_bytes() for name in ("calc.py", "test_calc.py")}
    service = CodeChanges(paths, database, workspace, "sandbox-delivery")
    try:
        change = service.create(
            "新增减法",
            "增加相同参数格式的减法并验证加法未回归",
            acceptance_criteria=["add(2,3)=5", "subtract(6,2)=4"],
            allowed_paths=["calc.py", "test_calc.py"],
        )
        profile = service.save_profile(
            "真实容器单元测试",
            ["python", "-m", "unittest", "discover"],
            20,
            executor={
                "kind": "container",
                "platform": "linux",
                "image": IMAGE,
                "context": "default",
            },
            baseline_required=True,
            category="test",
        )
        service.verify(change["id"], profile["id"], "baseline")
        baseline = await service.wait(change["id"], 60)
        assert baseline["latest_verification"]["status"] == "passed", baseline
        assert baseline["status"] == "ready"
        source = service.read_file(change["id"], "calc.py")
        service.edit_file(
            change["id"],
            "calc.py",
            source["content"],
            source["content"] + "\ndef subtract(a, b):\n return a - b\n",
            source["version"],
        )
        tests = service.read_file(change["id"], "test_calc.py")
        service.edit_file(
            change["id"],
            "test_calc.py",
            tests["content"],
            tests["content"]
            + " def test_subtract(self):\n  self.assertEqual(calc.subtract(6, 2), 4)\n",
            tests["version"],
        )
        service.verify(change["id"], profile["id"])
        passed = await service.wait(change["id"], 60)
        assert passed["status"] == "passed", passed
        proof = passed["latest_verification"]["executor"]["evidence"]
        assert proof["protocol"] == 2 and proof["isolated"]
        assert proof["image_id"] == IMAGE
        review_change(
            service,
            change["id"],
            passed["change_version"],
            passed["requirements_version"],
            "按实际结果复核",
            "test-reviewer",
        )
        with ZipFile(io.BytesIO(delivery_package(service, change["id"]))) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["verification"]["status"] == "passed"
            assert manifest["baseline"]["status"] == "passed"
            assert manifest["verification"]["executor"]["evidence"]["image_id"] == IMAGE
            assert "subtract" in archive.read("changes.patch").decode()
        for name, expected in original.items():
            assert (workspace.root / name).read_bytes() == expected
    finally:
        await service.shutdown()
