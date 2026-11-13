"""界面自检：控件树解析、截图分析与关键布局断言。"""

from app.modules.coding.ui_checks import (
    analyze_screenshot,
    evaluate_layout,
    parse_layout,
)


def control(kind, name="", width=100, height=100, visible=True):
    return {
        "type": kind,
        "name": name,
        "x": 0,
        "y": 0,
        "width": width,
        "height": height,
        "dock": "None",
        "visible": visible,
    }


def good_layout():
    rows = [
        control("TabControl", "tabs", 1180, 438),
        control("TabPage", "params", 1172, 406),
        control("TabPage", "device", 1172, 406),
    ]
    rows += [control("RibbonButton", f"b{index}", 88, 84) for index in range(6)]
    rows += [control("NumericUpDown", f"n{index}", 120, 28) for index in range(6)]
    rows.append(control("RichTextBox", "logBox", 1160, 156))
    return rows


GOOD_SHOTS = [{"path": "ui_tab0.png", "width": 1180, "height": 800, "stddev": 30.0}]


def test_layout_line_is_parsed():
    line = (
        "  TabControl tabs bounds={X=0,Y=152,Width=1180,Height=438} "
        "dock=Fill visible=True"
    )
    rows = parse_layout(line)
    assert rows == [
        {
            "type": "TabControl",
            "name": "tabs",
            "x": 0,
            "y": 152,
            "width": 1180,
            "height": 438,
            "dock": "Fill",
            "visible": True,
        }
    ]


def test_good_layout_passes():
    report = evaluate_layout(good_layout(), GOOD_SHOTS)
    assert report["ok"] is True, report["issues"]
    assert report["counts"]["buttons"] == 6
    assert report["counts"]["inputs"] == 6


def test_broken_layout_reports_every_problem():
    rows = [
        control("TabControl", "tabs", 1180, 32),
        control("TabPage", "params", 1172, 0),
        control("RibbonButton", "connect", 88, 84),
        control("Button", "tiny", 0, 0),
    ]
    shots = [{"path": "ui_tab0.png", "width": 400, "height": 200, "stddev": 0.4}]
    report = evaluate_layout(rows, shots)
    text = "\n".join(report["issues"])
    assert report["ok"] is False
    assert "标签页高度过小" in text
    assert "大按钮不足" in text
    assert "输入控件不足" in text
    assert "日志区" in text
    assert "0 尺寸" in text
    assert "截图尺寸过小" in text
    assert "空白" in text


def test_missing_screenshots_fail():
    report = evaluate_layout(good_layout(), [])
    assert "没有生成截图" in "\n".join(report["issues"])


def test_screenshot_analysis_reads_png(tmp_path):
    from PIL import Image

    path = tmp_path / "shot.png"
    Image.new("RGB", (1180, 800), "white").save(path)
    result = analyze_screenshot(path)
    assert result["width"] == 1180 and result["height"] == 800
    assert result["stddev"] == 0
