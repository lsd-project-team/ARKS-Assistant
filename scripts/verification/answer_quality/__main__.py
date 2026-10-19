import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from scripts.verification.answer_quality.runner import main  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--live", required=True, action="store_true")
parser.add_argument("--output", required=True)
parser.add_argument("--seed", type=int, default=20261019)
parser.add_argument("--ids", nargs="*")
parser.add_argument("--concurrency", type=int, choices=(1, 2, 3), default=2)
parser.add_argument("--timeout", type=int, choices=(300, 600), default=600)
parser.add_argument("--audit", action="store_true")
args = parser.parse_args()
try:
    asyncio.run(main(args))
except Exception as error:
    print(f"测评未完成：{type(error).__name__}", file=sys.stderr)
    raise SystemExit(1) from None
