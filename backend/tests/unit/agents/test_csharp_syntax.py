import json

from app.agents.tools.coding import _csharp_syntax_result


class Work:
    def __init__(self, content):
        self.content = content

    def read_file(self, path):
        return {"content": self.content}


def test_broken_csharp_gets_syntax_errors():
    result = json.dumps({"ok": True, "path": "A.cs"})
    output = json.loads(
        _csharp_syntax_result(result, "A.cs", Work("public class A { void M( { } }"))
    )
    assert output["syntax_errors"]
    assert "next" in output


def test_valid_csharp_unchanged():
    result = json.dumps({"ok": True})
    assert _csharp_syntax_result(result, "A.cs", Work("public class A { }")) == result


def test_non_csharp_unchanged():
    result = json.dumps({"ok": True})
    assert _csharp_syntax_result(result, "a.py", Work("def broken(")) == result
