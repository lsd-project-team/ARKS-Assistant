import io

from pypdf import PdfReader


def parse_pdf(data):
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
