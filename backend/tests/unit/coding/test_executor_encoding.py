from app.modules.coding.executor import _decode_output


def test_decode_output_utf8():
    assert _decode_output("中文输出".encode()) == "中文输出"


def test_decode_output_falls_back_to_gbk():
    assert _decode_output("中文输出".encode("gb18030")) == "中文输出"
