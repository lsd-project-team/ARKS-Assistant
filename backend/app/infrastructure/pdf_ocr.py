"""本地 PDF OCR 的进程隔离及请求级预算，不发送文档到外部服务。"""

import json
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

MAX_OCR_PAGES = 50
OCR_TIMEOUT = 120
MAX_OCR_CHARACTERS = 1_000_000
_slots = threading.BoundedSemaphore(2)


class OcrLimitError(ValueError):
    """累计 OCR 资源超限时拒绝整个附件，不把缺失内容报告为成功。"""


def failed_pages(pages, reason):
    return {number: {"text": "", "partial": True, "error": reason} for number in pages}


def decode_result(output, pages):
    try:
        payload = json.loads(output)
        if not isinstance(payload, dict):
            raise ValueError("OCR 返回结构无效")
        if "limit_error" in payload:
            raise OcrLimitError(str(payload["limit_error"]))
        if payload.get("error"):
            if not isinstance(payload["error"], str):
                raise ValueError("OCR 错误说明无效")
            return failed_pages(pages, payload["error"])
        records = payload["pages"]
        if len(records) != len(pages):
            raise ValueError("OCR 页数不符")
        result, characters = {}, 0
        for record, number in zip(records, pages, strict=True):
            if (
                record["page"] != number
                or not isinstance(record["text"], str)
                or not isinstance(record["partial"], bool)
                or not isinstance(record.get("error", ""), str)
            ):
                raise ValueError("OCR 页内容无效")
            characters += len(record["text"])
            result[number] = record
        if characters > MAX_OCR_CHARACTERS:
            raise OcrLimitError("OCR 识别正文超过 100 万字，请拆分后上传")
        return result
    except OcrLimitError:
        raise
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        return failed_pages(pages, "OCR 返回内容无效，请重新上传或补充文字")


@dataclass
class PdfOcrBudget:
    pages_left: int = MAX_OCR_PAGES
    deadline: float | None = None

    def __call__(self, data, pages):
        if len(pages) > self.pages_left:
            raise OcrLimitError("附件需要 OCR 的页面累计超过 50 页，请拆分后上传")
        self.pages_left -= len(pages)
        if self.deadline is None:
            self.deadline = time.monotonic() + OCR_TIMEOUT
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or not _slots.acquire(timeout=remaining):
            raise OcrLimitError("OCR 等待或识别累计超过 120 秒，请拆分后上传")
        try:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise OcrLimitError("OCR 等待或识别累计超过 120 秒，请拆分后上传")
            # PDFium 不能跨线程并发使用；子进程还允许在超时后真正终止识别。
            process = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "-m",
                    "app.infrastructure.pdf_ocr_worker",
                    "--pages",
                    ",".join(map(str, pages)),
                ],
                input=data,
                capture_output=True,
                timeout=remaining,
                cwd=Path(__file__).resolve().parents[2],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as error:
            raise OcrLimitError("OCR 等待或识别累计超过 120 秒，请拆分后上传") from error
        except OSError:
            return failed_pages(pages, "本地 OCR 进程无法启动，请重新运行 Setup.ps1 安装依赖")
        finally:
            _slots.release()
        if process.returncode:
            return failed_pages(pages, "本地 OCR 运行失败，请重新运行 Setup.ps1 安装依赖")
        return decode_result(process.stdout, pages)
