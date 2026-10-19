"""从仓库根目录 python -m scripts.verification.code_work_quality 显式执行。"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


def main():
    parser = argparse.ArgumentParser(
        description="Agent质量证据套件；run --live会消耗真实API。默认不读取正式配置。"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample")
    sample.add_argument("destination", type=Path)
    run = commands.add_parser("run")
    for flag in ("cases", "workspace", "config", "output"):
        run.add_argument("--" + flag, type=Path, required=True)
    run.add_argument("--live", action="store_true")
    run.add_argument("--allow-verification", action="store_true")
    review = commands.add_parser("review")
    for flag in ("report", "ratings"):
        review.add_argument("--" + flag, type=Path, required=True)
    for flag in ("report-sha256", "case-id", "reviewer"):
        review.add_argument("--" + flag, required=True)
    verify = commands.add_parser("verify-review")
    verify.add_argument("--report", type=Path, required=True)
    verify.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "sample":
            from .samples import create_sample

            print(create_sample(args.destination))
        elif args.command == "run":
            if not args.live:
                parser.exit(1, "run必须显式指定--live；真实运行会消耗供应商API与Token。\n")
            # 授权门先于模型/运行时导入；未授权命令不应等待整套供应商依赖启动。
            from .runner import run_suite
            from .safety import file_hash

            path = asyncio.run(
                run_suite(
                    args.cases,
                    args.workspace,
                    args.config,
                    args.output,
                    live=args.live,
                    allow_verification=args.allow_verification,
                )
            )
            outcome = json.loads(path.read_text(encoding="utf-8"))["outcome"]
            print(
                json.dumps(
                    {
                        "report": str(path),
                        "report_sha256": file_hash(path),
                        "outcome": outcome,
                        "semantic_review": "required",
                    }
                )
            )
            if outcome == "failed":
                return 1
        elif args.command == "review":
            from .review import save_review
            from .safety import checked_path

            ratings = json.loads(checked_path(args.ratings).read_text(encoding="utf-8"))
            print(
                save_review(args.report, args.report_sha256, args.case_id, args.reviewer, ratings)
            )
        else:
            from .review import verify_review

            print(verify_review(args.report, args.review))
    except Exception as error:
        # 参数/Pydantic/供应商异常可能回显原输入；终端只报告错误类型，不打印凭据。
        parser.exit(
            1, f"质量套件未完成（{type(error).__name__}）。核对隔离路径、场景版本与公开配置。\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
