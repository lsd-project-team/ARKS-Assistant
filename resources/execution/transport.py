"""固定协议传输程序，不从项目载入模块，也不接受用户路径。"""

import os
import shutil
import sys
import tarfile
import time
from pathlib import Path

WINDOWS = os.name == "nt"
WORK = Path("C:/work" if WINDOWS else "/work")
RESULT = Path("/run/arks/result.json")

if sys.argv[1:] == ["prepare"]:
    shutil.copytree("/stage", WORK, dirs_exist_ok=True)
elif sys.argv[1:] == ["wait"]:
    while not RESULT.exists():
        time.sleep(0.1)
    sys.stdout.write(RESULT.read_text(encoding="utf-8"))
elif sys.argv[1:] == ["export"]:
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
        for path in sorted(WORK.rglob("*")):
            if path == RESULT:
                continue
            archive.add(path, arcname=path.relative_to(WORK).as_posix(), recursive=False)
else:
    raise SystemExit(2)
