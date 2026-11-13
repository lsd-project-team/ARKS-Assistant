"""SP900 一次性生成验收基准：隔离数据目录 + 空项目 + 真实 Agent 运行 + 独立评分。

用法（在项目根目录）：
    backend\\.venv\\Scripts\\python.exe scripts\\acceptance\\sp900\\run.py
可选参数：--port 8790 --timeout 1800 --keep --no-grade
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
TASK = BASE / "task" / "开发任务书.md"
REFERENCES = BASE / "reference"
PROMPT = """按项目根目录的《任务书.md》从零实现完整的 SP900 点胶机上位机（C# / .NET 8 WinForms）。

要求：
1. 先调用 update_plan 建计划：协议层 + 回放自测 → 构建通过 → 界面（骨架已就绪）→ verify build → check_ui + view_image 自检 → 验收。
2. 协议严格按任务书第 3 节实现；写回放自测工程 tests/Sp900SelfTest，覆盖任务书第七节的 8 项要求。
   不要额外增加依赖编码页/系统区域设置（如 GBK 936）或其他设备未要求的测试；
   自己新增的测试若反复失败，先删除或修正，不要卡在同一个失败用例上。
3. 界面：生成模式会自动准备 WinForms 骨架（App.csproj/Program.cs/MainForm.cs/UiParts.cs/ScreenshotTool.cs/Actions.cs），
   MainForm.cs/UiParts.cs/Program.cs/ScreenshotTool.cs 受保护，写入会被拒绝；协议与按钮动作写到 Actions.cs 或新文件，
   通过 Channel/Mode/Pressure/Time/Vacuum 等内部字段读写参数，用 WriteLog/SetStatus 更新界面。
   骨架已有两页签与日志区，保持页签数量为 2，不要重复 TabPage；
   保留 `--screenshot <png路径> <标签页索引>` 契约与全层级 bounds 打印。
4. 完成前必须 verify build（0 错误 0 警告）、verify test（回放自测）与 check_ui 通过，并用 view_image 看截图核对；不要留 TODO、占位或未实现。
5. 最终回答按任务书第九节逐项列出证据（构建、自测数量、截图路径），未满足项明确说明。
6. input/ 下有参考界面截图（good-main.png 等）和一张反例 failure-1552.png，界面不要低于参考、不能出现反例那种空页/浮动滚动框。
"""


def sanitized_env(data_dir):
    env = {
        key: value
        for key, value in os.environ.items()
        if key.lower() not in {"http_proxy", "https_proxy", "no_proxy", "all_proxy"}
    }
    env["NO_PROXY"] = "localhost,127.0.0.1,::1"
    env["TRUNK_AGENT_DATA_DIR"] = str(data_dir)
    return env


def wait_health(client, deadline=120):
    for _ in range(deadline * 2):
        try:
            response = client.get("/api/health")
            if response.status_code == 200 and response.json().get("ok"):
                return response.json()
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError("服务未就绪")


def approve_pending(client, project_id):
    try:
        payload = client.get(f"/api/p/{project_id}/coding/approvals").json()
    except (httpx.HTTPError, ValueError):
        return 0
    approved = 0
    for item in payload.get("approvals", []):
        if item.get("status") != "pending":
            continue
        try:
            client.post(
                f"/api/p/{project_id}/coding/approvals/{item['id']}",
                json={"approved": True, "scope": "session"},
            )
            approved += 1
        except httpx.HTTPError:
            pass
    return approved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--no-grade", action="store_true")
    parser.add_argument("--prompt", default="", help="覆盖默认验收提示，用于冒烟验证")
    args = parser.parse_args()
    prompt = args.prompt or PROMPT

    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "output" / "acceptance" / f"sp900-{stamp}"
    data_dir, project_dir = run_dir / "data", run_dir / "project"
    data_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "input").mkdir(parents=True)
    shutil.copy2(ROOT / "data" / "settings.private.json", data_dir / "settings.private.json")
    shutil.copy2(TASK, project_dir / "任务书.md")
    for image in sorted(REFERENCES.glob("*.png")):
        shutil.copy2(image, project_dir / "input" / image.name)

    log = (run_dir / "server.log").open("wb")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
        ],
        cwd=ROOT / "backend",
        env=sanitized_env(data_dir),
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=0x08000000,
    )
    client = httpx.Client(
        base_url=f"http://127.0.0.1:{args.port}",
        trust_env=False,
        timeout=httpx.Timeout(180, connect=10),
    )
    result = {"run_dir": str(run_dir), "status": "unknown"}
    try:
        wait_health(client)
        for _ in range(60):
            if (data_dir / "auth.initial-accounts.json").is_file():
                break
            time.sleep(0.5)
        credentials = json.loads(
            (data_dir / "auth.initial-accounts.json").read_text(encoding="utf-8")
        )
        admin = next(item for item in credentials if item["username"] == "admin")
        login = client.post(
            "/api/auth/login", json={"username": "admin", "password": admin["password"]}
        )
        login.raise_for_status()
        client.headers["X-Arks-CSRF"] = login.json()["csrf_token"]
        created = client.post(
            "/api/projects",
            json={"name": "SP900 一次性生成验收", "source_root": str(project_dir)},
        )
        created.raise_for_status()
        payload = created.json()
        project = payload.get("project", payload)
        project_id = project.get("id") or project["project"]["id"]
        client.put(
            f"/api/p/{project_id}/coding/settings",
            json={"approval_mode": "full", "enabled": True},
        ).raise_for_status()
        started = client.post(
            f"/api/p/{project_id}/threads/start", json={"content": prompt}
        )
        started.raise_for_status()
        run = started.json()
        print(f"[bench] project={project_dir}")
        print(f"[bench] run={run['id']} thread={run['thread_id']}")
        answer, detail, approvals = "", {}, 0
        status = "timeout"
        deadline = time.time() + args.timeout
        while time.time() < deadline:
            try:
                detail = client.get(f"/api/p/{project_id}/runs/{run['id']}").json()
            except (httpx.HTTPError, ValueError):
                time.sleep(2)
                continue
            status = detail.get("status", "")
            answer = detail.get("answer") or ""
            approvals += approve_pending(client, project_id)
            if status in {"completed", "failed", "interrupted", "cancelled"}:
                break
            time.sleep(2)
        print(f"[bench] status={status} approvals={approvals}")
        if detail.get("error"):
            print("[bench] error:", str(detail["error"])[:500])
        (run_dir / "answer.md").write_text(answer, encoding="utf-8")
        result.update(
            {
                "status": status,
                "run_id": run["id"],
                "thread_id": run["thread_id"],
                "project_id": project_id,
                "project_dir": str(project_dir),
                "auto_approvals": approvals,
                "error": detail.get("error", ""),
            }
        )
        if not args.no_grade:
            code = subprocess.call(
                [
                    sys.executable,
                    str(BASE / "grade.py"),
                    "--project",
                    str(project_dir),
                    "--run-dir",
                    str(run_dir),
                ]
            )
            result["grade_exit"] = code
            print(f"[bench] grade exit={code}")
    finally:
        client.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()
        (run_dir / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if args.keep:
            print(f"[bench] kept {run_dir}")
        else:
            print(f"[bench] result dir {run_dir}")
    if args.no_grade:
        return 0 if result.get("status") == "completed" else 1
    if result.get("status") != "completed":
        print(f"[bench] 未干净完成：status={result.get('status')}，即使工件评分通过也判失败")
        return 1
    return 0 if result.get("grade_exit") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
