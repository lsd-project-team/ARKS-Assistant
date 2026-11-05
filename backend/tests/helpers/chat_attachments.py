"""附件格式的真实字节夹具；需求值只保存在文档中。"""

import io
import zipfile
from functools import lru_cache
from xml.sax.saxutils import escape

from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


@lru_cache(maxsize=64)
def document_bytes(extension, value=7):
    text = f"NewValue = {value}"
    if extension == ".xlsx":
        book = Workbook()
        sheet = book.active
        sheet.title = "参数"
        sheet.append(["规则", "目标值"])
        sheet.append([text, value])
        sheet["C2"] = "=B2+1"
        output = io.BytesIO()
        book.save(output)
        book.close()
        return output.getvalue()
    if extension == ".docx":
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f"<w:body><w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>"
                "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>表格规则</w:t></w:r></w:p>"
                "</w:tc></w:tr></w:tbl></w:body></w:document>",
            )
        return output.getvalue()
    if extension == ".pdf":
        writer = PdfWriter()
        page = writer.add_blank_page(width=400, height=400)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                ),
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 30 350 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    if extension == ".zip":
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("reference/Example.cs", f"// {text}\nclass Example {{}}")
        return output.getvalue()
    if extension == ".csv":
        return f'规则,目标值\r\n"{text}",{value}\r\n'.encode("utf-8-sig")
    return text.encode()
