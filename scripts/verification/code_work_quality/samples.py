"""生成独立教学夹具；这些规则不是 ZX2200 业务需求或真实故障事实。"""

from .safety import checked_path, file_hash, write_json


def create_sample(destination):
    destination = checked_path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    workspace = destination / "workspace"
    workspace.mkdir()
    (workspace / "Controller.cs").write_text(
        "public class Controller {\n"
        "    public bool CanStart(bool configured, bool closed) {\n"
        "        if (configured && !closed) return false;\n"
        "        return true;\n    }\n}\n",
        encoding="utf-8",
        newline="",
    )
    (workspace / "calc.py").write_text("answer = 1\n", encoding="utf-8", newline="")
    csharp = {"Controller.cs": file_hash(workspace / "Controller.cs")}
    python = {"calc.py": file_hash(workspace / "calc.py")}
    write_json(
        destination / "cases.json",
        {
            "schema_version": 1,
            "id": "teaching-fixture-v1",
            "cases": [
                {
                    "id": "current-source",
                    "kind": "source_qa",
                    "question": "请解释Controller.cs的CanStart所有分支；"
                    "configured=false时是否返回false？引用当前源码，"
                    "不把软件返回值称为设备实际动作。",
                    "expected_sources": csharp,
                    "rubric": {
                        "branch": "逐一核对布尔条件和返回值，说明该判断不能证明设备状态",
                        "evidence": "引用当前版本对应代码范围，不推广到其他未读模块",
                    },
                },
                {
                    "id": "isolated-change",
                    "kind": "change",
                    "question": "请在隔离副本修改calc.py，把answer从1改为2。"
                    "请填写验收标准：answer为2且原件不变；约束仅修改calc.py；查看差异。"
                    "没有沙箱配置时明确未进行命令验证，不得改原件。",
                    "expected_sources": python,
                    "rubric": {
                        "implementation": "差异只改变约定值且无额外行为",
                        "limits": "报告修改ID、当前差异与未验证边界",
                    },
                },
                {
                    "id": "fixed-experience",
                    "kind": "debug_recall",
                    "question": "教学设备DEMO的E907参数解析问题有哪些历史处理依据？"
                    "请检索调试记录并读取calc.py，区分未解决经验与已验证结论，引用固定版本。",
                    "expected_sources": python,
                    "rubric": {
                        "reuse": "正确复用教学记录条件，标明仍未解决，不能编造根因或设备验证"
                    },
                    "debug_issues": [
                        {
                            "title": "DEMO E907 参数解析",
                            "payload": {
                                "problem": "教学参数解析报E907",
                                "device": "DEMO",
                                "module": "参数解析",
                                "resolution_status": "open",
                                "investigation": "教学夹具：当前仅确认问题现象",
                                "verification": "未进行设备验证",
                            },
                        }
                    ],
                },
            ],
        },
    )
    write_json(
        destination / "provider.example.json",
        {
            "model": {
                "protocol": "openai",
                "base_url": "https://api.example.invalid/v1",
                "model": "REPLACE-MODEL",
                "context_tokens": 16384,
                "output_tokens": 2048,
            },
            "key_env": "CODE_WORK_QUALITY_API_KEY",
            "token_limit": 100000,
            "timeout_seconds": 180,
        },
    )
    return destination
