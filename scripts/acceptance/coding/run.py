"""编码模块多案例验收：隔离运行一次真实 Agent 任务并调用独立评分。

用法：
    backend\\.venv\\Scripts\\python.exe scripts\\acceptance\\coding\\run.py --case python-cli
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
CASES = BASE / "cases"


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
                return
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
    parser.add_argument("--case", required=True)
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--timeout", type=int, default=1500)
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--no-grade", action="store_true")
    args = parser.parse_args()

    case_dir = CASES / args.case
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "output" / "acceptance" / f"coding-{case['name']}-{stamp}"
    data_dir, project_dir = run_dir / "data", run_dir / "project"
    data_dir.mkdir(parents=True, exist_ok=True)
    project_dir.mkdir(parents=True, exist_ok=True)
    if case.get("seed"):
        source = case_dir / case["seed"]
        for item in source.rglob("*"):
            if item.is_file():
                target = project_dir / item.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
    shutil.copy2(case_dir / "task.md", project_dir / "任务书.md")
    shutil.copy2(ROOT / "data" / "settings.private.json", data_dir / "settings.private.json")

    prompt = (
        "按项目根目录《任务书.md》完成任务。先调用 update_plan 建立计划；"
        "先写 README 与任务要求的全部交付物，再实现代码；"
        "实现后运行任务要求的构建与测试并确保通过；不要留 TODO/占位。"
        "不要修改任务书要求保护的文件（如测试文件）。最终说明改了什么、测试结果与证据。"
    )

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
    result = {"case": case["name"], "run_dir": str(run_dir), "status": "unknown"}
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
            json={"name": f"验收-{case['title']}", "source_root": str(project_dir)},
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
        print(f"[case] {case['name']} project={project_dir}")
        print(f"[case] run={run['id']}")
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
        print(f"[case] status={status} approvals={approvals}")
        if detail.get("error"):
            print("[case] error:", str(detail["error"])[:400])
        (run_dir / "answer.md").write_text(answer, encoding="utf-8")
        result.update(
            {
                "status": status,
                "run_id": run["id"],
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
                    "--case",
                    case["name"],
                    "--project",
                    str(project_dir),
                    "--run-dir",
                    str(run_dir),
                ]
            )
            result["grade_exit"] = code
            print(f"[case] grade exit={code}")
    finally:
        client.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()
        (run_dir / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        print(f"[case] result dir {run_dir}")
    if args.no_grade:
        return 0 if result.get("status") == "completed" else 1
    if result.get("status") != "completed":
        print("[case] 未干净完成，判失败")
        return 1
    return 0 if result.get("grade_exit") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
