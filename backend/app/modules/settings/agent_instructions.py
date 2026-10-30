"""账号级全局指令文件；路径由服务端身份确定，项目不能覆盖。"""

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import RLock

MAX_INSTRUCTION_BYTES = 32 * 1024
EMPTY_VERSION = sha256(b"").hexdigest()


class AgentInstructionsStore:
    def __init__(self, data: Path):
        self.root = data / "instructions"
        self.lock = RLock()

    def path(self, account_id):
        if not account_id:
            raise ValueError("请先登录后维护全局指令")
        # 不使用请求提供的文件名或目录；账号标识也不能成为路径穿越入口。
        return self.root / sha256(str(account_id).encode()).hexdigest() / "agent.md"

    def read(self, account_id):
        if not account_id:
            return {
                "name": "agent.md",
                "owner_id": None,
                "content": "",
                "version": EMPTY_VERSION,
                "updated_at": None,
            }
        path = self.path(account_id)
        with self.lock:
            try:
                data = path.read_bytes()
                updated = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
            except FileNotFoundError:
                data, updated = b"", None
            if len(data) > MAX_INSTRUCTION_BYTES:
                raise ValueError("全局 agent.md 超过 32 KiB，请精简后再使用")
            try:
                content = data.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ValueError("全局 agent.md 必须使用 UTF-8 编码") from error
            return {
                "name": "agent.md",
                "owner_id": account_id,
                "content": content,
                "version": sha256(data).hexdigest(),
                "updated_at": updated,
            }

    def save(self, account_id, content, version):
        data = content.encode("utf-8")
        if len(data) > MAX_INSTRUCTION_BYTES:
            raise ValueError("全局 agent.md 最多 32 KiB，请精简后保存")
        with self.lock:
            if self.read(account_id)["version"] != version:
                raise ValueError("全局 agent.md 已在其他窗口更新，请读取最新内容后再保存")
            path = self.path(account_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            try:
                temporary.write_bytes(data)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
            return self.read(account_id)
