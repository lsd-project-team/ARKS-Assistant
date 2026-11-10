"""仅在独立子进程中加载 PDFium 和 OCR 模型，原件通过标准输入读取。"""

import argparse
import contextlib
import json
import math
import sys
from importlib.resources import files

from app.infrastructure.pdf_ocr import MAX_OCR_CHARACTERS, MAX_OCR_PAGES, OcrLimitError

MAX_IMAGE_EDGE = 2500
MIN_TEXT_SCORE = 0.5
CONFIDENT_TEXT_SCORE = 0.8


def create_engine():
    from rapidocr import RapidOCR

    # 固定发行版自带中英文模型；显式指定本地路径，缺失时失败而不下载。
    models = files("rapidocr") / "models"
    params = {
        # 保留低分识别行交给下方过滤，避免库先丢弃后无法标记识别不完整。
        "Global.text_score": 0.0,
        "Global.log_level": "error",
        "EngineConfig.onnxruntime.intra_op_num_threads": 2,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    }
    for task, name in {
        "Det": "PP-OCRv6_det_small.onnx",
        "Cls": "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
        "Rec": "PP-OCRv6_rec_small.onnx",
    }.items():
        path = models / name
        if not path.is_file():
            raise FileNotFoundError("安装包缺少 OCR 模型，请重新运行 Setup.ps1")
        params[f"{task}.model_path"] = str(path)
    return RapidOCR(params=params)


def recognize_page(page, engine):
    width, height = page.get_size()
    if not all(math.isfinite(value) and value > 0 for value in (width, height)):
        raise ValueError("PDF 页面尺寸无效")
    scale = min(2.5, MAX_IMAGE_EDGE / max(width, height))
    bitmap = page.render(scale=scale)
    try:
        result = engine(bitmap.to_numpy())
    finally:
        bitmap.close()
    lines, partial = [], False
    for text, score in zip(result.txts or [], result.scores or [], strict=True):
        score = float(score)
        if not text.strip():
            continue
        if not math.isfinite(score) or score < MIN_TEXT_SCORE:
            partial = True
            continue
        lines.append(text)
        partial |= score < CONFIDENT_TEXT_SCORE
    return {
        "text": "\n".join(lines),
        "partial": partial,
        "error": "" if lines else "未识别到文字，请提供清晰扫描件或补充文字",
    }


def recognize_pages(data, pages):
    import pypdfium2 as pdfium

    if not pages or len(pages) > MAX_OCR_PAGES or len(set(pages)) != len(pages):
        raise OcrLimitError("OCR 页数无效或超过 50 页，请拆分后上传")
    engine, records, characters = create_engine(), [], 0
    with pdfium.PdfDocument(data) as document:
        for number in pages:
            if not 1 <= number <= len(document):
                raise ValueError("OCR 页码超出 PDF 范围")
            page = document.get_page(number - 1)
            try:
                record = recognize_page(page, engine)
            except Exception:
                record = {"text": "", "partial": True, "error": "页面渲染或识别失败"}
            finally:
                page.close()
            characters += len(record["text"])
            if characters > MAX_OCR_CHARACTERS:
                raise OcrLimitError("OCR 识别正文超过 100 万字，请拆分后上传")
            records.append({"page": number, **record})
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", required=True)
    args = parser.parse_args()
    try:
        data = sys.stdin.buffer.read(32 * 1024 * 1024 + 1)
        if not data or len(data) > 32 * 1024 * 1024:
            raise ValueError("OCR 原文件为空或超过限制")
        pages = [int(value) for value in args.pages.split(",")]
        # 第三方库日志不能混入机器读取的 JSON 正文。
        with contextlib.redirect_stdout(sys.stderr):
            response = {"pages": recognize_pages(data, pages)}
    except OcrLimitError as error:
        response = {"limit_error": str(error)}
    except (ImportError, FileNotFoundError):
        response = {"error": "本地 OCR 组件未就绪，请重新运行 Setup.ps1 安装依赖"}
    except Exception:
        response = {"error": "本地 OCR 无法读取此 PDF，请重新导出后上传"}
    sys.stdout.buffer.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    main()
