import io

from pypdf import PdfReader


def apply_ocr(data, pages, empty, ocr):
    results = ocr(data, empty)
    recognized, uncertain, failed = [], [], []
    remaining = []
    for number in empty:
        result = results[number]
        if result["text"].strip():
            pages[number - 1] = f"[第 {number} 页] [OCR 识别]\n{result['text']}"
            recognized.append(number)
            if result["partial"]:
                uncertain.append(number)
        else:
            remaining.append(number)
            reason = result.get("error") or "未识别到文字"
            pages[number - 1] += f"[OCR 未读取：{reason}]"
            failed.append(f"{number}（{reason}）")
    notes = (
        f"共 {len(pages)} 页；OCR 已识别页：{recognized or '无'}；"
        f"OCR 低置信或识别不完整页：{uncertain or '无'}；"
        f"无可提取文字页：{remaining or '无'}。"
        "本地 OCR 结果按识别行保存；表格关系和图片含义未解析。"
    )
    if failed:
        notes += " 未读取页：" + ", ".join(failed)
    status = (
        "needs_ocr"
        if len(remaining) == len(pages)
        else "partial"
        if remaining or uncertain
        else "readable"
    )
    return "\n\n".join(pages), status, notes, []


def parse_pdf(data, *, ocr=None):
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("暂不支持加密 PDF")
        if len(reader.pages) > 300:
            raise ValueError("PDF 超过 300 页，请按范围拆分")
        pages, empty = [], []
        for index, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            pages.append(f"[第 {index} 页]\n{text}")
            if not text.strip():
                empty.append(index)
        if ocr is not None and empty:
            return apply_ocr(data, pages, empty, ocr)
        status = "needs_ocr" if len(empty) == len(pages) else "partial" if empty else "readable"
        notes = (
            f"共 {len(pages)} 页；无可提取文字页：{empty or '无'}。"
            "不执行 OCR，图形与扫描内容须人工补充。"
        )
        return "\n\n".join(pages), status, notes, []
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("PDF 解析失败，请导出为普通文本 PDF 后重试") from error
