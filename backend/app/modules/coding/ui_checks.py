"""界面自检：解析 --screenshot 打印的控件树，校验截图与关键布局。"""

import re
from pathlib import Path

from PIL import Image, ImageStat

BOUNDS = re.compile(
    r"^\s*(?P<type>\w+)\s*(?P<name>[^\s]*)\s+"
    r"bounds=\{X=(?P<x>-?\d+),Y=(?P<y>-?\d+),Width=(?P<w>\d+),Height=(?P<h>\d+)\}\s+"
    r"dock=(?P<dock>\S+)\s+visible=(?P<visible>True|False)\s*$",
    re.MULTILINE,
)
INPUT_TYPES = {"TextBox", "NumericUpDown", "ComboBox", "MaskedTextBox"}
LOG_TYPES = {"RichTextBox", "ListView", "ListBox"}
BUTTON_TYPES = {"RibbonButton", "Button"}
MIN_TABPAGE_HEIGHT = 300
MIN_BUTTON = 60
MIN_INPUTS = 5
MIN_BUTTONS = 6
MIN_LOG_HEIGHT = 150
MIN_SHOT_WIDTH = 800
MIN_SHOT_HEIGHT = 600
MIN_SHOT_STDDEV = 5.0


def parse_layout(output):
    rows = []
    for match in BOUNDS.finditer(output or ""):
        rows.append(
            {
                "type": match.group("type"),
                "name": match.group("name"),
                "x": int(match.group("x")),
                "y": int(match.group("y")),
                "width": int(match.group("w")),
                "height": int(match.group("h")),
                "dock": match.group("dock"),
                "visible": match.group("visible") == "True",
            }
        )
    return rows


def analyze_screenshot(path):
    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            gray = image.convert("L")
            stddev = round(float(ImageStat.Stat(gray).stddev[0]), 2)
    except (OSError, ValueError) as error:
        return {"path": Path(path).name, "error": str(error), "width": 0, "height": 0, "stddev": 0}
    return {"path": Path(path).name, "width": width, "height": height, "stddev": stddev}


def evaluate_layout(rows, screenshots, expected_tabs=2):
    issues, notes = [], []
    if not rows:
        issues.append("没有解析到控件树，截图工具需要打印每个控件的 bounds")
    tabs = [row for row in rows if row["type"] == "TabControl"]
    pages = [row for row in rows if row["type"] == "TabPage"]
    buttons = [
        row
        for row in rows
        if row["type"] in BUTTON_TYPES
        and row["visible"]
        and row["width"] >= MIN_BUTTON
        and row["height"] >= MIN_BUTTON
    ]
    inputs = [row for row in rows if row["type"] in INPUT_TYPES and row["visible"]]
    logs = [
        row
        for row in rows
        if row["type"] in LOG_TYPES and row["visible"] and row["height"] >= MIN_LOG_HEIGHT
    ]
    empty = [
        row
        for row in rows
        if row["visible"]
        and row["type"] != "Label"
        and (row["width"] == 0 or row["height"] == 0)
    ]
    if len(tabs) < 1:
        issues.append("找不到 TabControl")
    if len(pages) < expected_tabs:
        issues.append(f"标签页数量不足：{len(pages)} < {expected_tabs}")
    if pages and max(page["height"] for page in pages) < MIN_TABPAGE_HEIGHT:
        issues.append(
            f"标签页高度过小：最高 {max(page['height'] for page in pages)}px "
            f"< {MIN_TABPAGE_HEIGHT}px（页面内容会被压成 0 高）"
        )
    if len(buttons) < MIN_BUTTONS:
        issues.append(f"功能区大按钮不足：{len(buttons)} < {MIN_BUTTONS}")
    if len(inputs) < MIN_INPUTS:
        issues.append(
            f"参数输入控件不足：{len(inputs)} < {MIN_INPUTS}"
            "（控件树需要覆盖全部层级，不能限制深度）"
        )
    if not logs:
        issues.append(f"找不到高度 ≥{MIN_LOG_HEIGHT}px 的日志区")
    if empty:
        detail = "，".join(f"{row['type']} {row['name']}" for row in empty[:5])
        issues.append(f"存在可见的 0 尺寸控件：{detail}")
    if not screenshots:
        issues.append("没有生成截图")
    for shot in screenshots:
        if shot.get("error"):
            issues.append(f"截图读取失败：{shot['path']}（{shot['error']}）")
            continue
        if shot["width"] < MIN_SHOT_WIDTH or shot["height"] < MIN_SHOT_HEIGHT:
            issues.append(
                f"截图尺寸过小：{shot['path']} {shot['width']}×{shot['height']}"
            )
        if shot["stddev"] < MIN_SHOT_STDDEV:
            issues.append(f"截图疑似空白：{shot['path']} 像素标准差 {shot['stddev']}")
    tabs_height = max((row["height"] for row in tabs), default=0)
    notes.append(f"控件 {len(rows)} 个；标签页 {len(pages)} 个；大按钮 {len(buttons)} 个")
    notes.append(f"输入控件 {len(inputs)} 个；日志区 {len(logs)} 个；TabControl 高 {tabs_height}px")
    return {
        "ok": not issues,
        "issues": issues,
        "notes": notes,
        "counts": {
            "controls": len(rows),
            "tabs": len(tabs),
            "pages": len(pages),
            "buttons": len(buttons),
            "inputs": len(inputs),
            "logs": len(logs),
        },
        "screenshots": screenshots,
    }
