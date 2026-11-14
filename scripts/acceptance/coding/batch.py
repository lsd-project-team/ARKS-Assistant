"""顺序跑多个编码验收案例并汇总。"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        default="python-cli,dotnet-console,bugfix-python,refactor-python,bugfix-multi,web-static,winforms-tool",
    )
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--timeout", type=int, default=1500)
    args = parser.parse_args()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    report_dir = ROOT / "output" / "acceptance" / f"coding-batch-{stamp}"
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for name in [item.strip() for item in args.cases.split(",") if item.strip()]:
        started = time.time()
        code = subprocess.call(
            [
                sys.executable,
                str(BASE / "run.py"),
                "--case",
                name,
                "--port",
                str(args.port),
                "--timeout",
                str(args.timeout),
                "--keep",
            ]
        )
        summary.append(
            {"case": name, "exit": code, "seconds": round(time.time() - started)}
        )
        print(f"[batch] {name} exit={code}")
    report = {"cases": summary, "passed": sum(1 for row in summary if row["exit"] == 0)}
    (report_dir / "batch.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
