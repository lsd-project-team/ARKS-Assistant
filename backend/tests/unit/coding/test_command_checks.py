from app.agents.tools.coding import _record_command_check


class Checks:
    def __init__(self):
        self.verify = None
        self.test = None

    def record_verify(self, result):
        if result.get("kind") == "test":
            self.test = result
        else:
            self.verify = result


def test_failed_build_command_is_recorded_with_errors():
    checks = Checks()
    output = "Program.cs(3,5): error CS1002: ; expected\n1 Error(s)"
    _record_command_check(checks, "dotnet build", output, 1)
    assert checks.verify["ok"] is False
    assert checks.verify["errors"][0]["code"] == "CS1002"


def test_failed_pytest_is_recorded():
    checks = Checks()
    _record_command_check(checks, "python -m pytest -q", "1 failed, 4 passed", 1)
    assert checks.test["ok"] is False
    assert checks.test["failed"] == 1


def test_successful_python_build_is_recorded():
    checks = Checks()
    _record_command_check(checks, "python -m compileall -q .", "", 0)
    assert checks.verify["ok"] is True
