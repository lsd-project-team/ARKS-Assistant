"""Shared typographic covers: title and introduction only."""
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

COVERS = {
    'transport-unit': {
        'title': 'Transport Unit\n设计文档',
        'intro': '介绍产品运行模型的层级结构、数据归属与坐标计算，\n说明对象的建立、刷新、跨工位流转及异常处理。',
    },
    'correction-process': {
        'title': '纠偏过程\n设计文档',
        'intro': '介绍供料端定位、产品层级定位、上视与中转台纠偏，\n说明计算依据、结果保存、生效时机及失败处理。',
    },
}


def add_cover(doc, folder):
    spec = COVERS[folder]
    title = doc.add_paragraph(spec['title'], style='Title')
    intro = doc.add_paragraph(spec['intro'], style='Normal')
    for p in (title, intro):
        pf = p.paragraph_format
        pf.first_line_indent = Pt(0)
        pf.left_indent = pf.right_indent = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.keep_together = True
        for run in p.runs:
            run.font.name = 'Microsoft YaHei'
            run.font.color.rgb = RGBColor(0, 0, 0)
            fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
            for key in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
                fonts.set(qn('w:' + key), 'Microsoft YaHei')
    title.paragraph_format.space_before = Pt(156)
    title.paragraph_format.space_after = Pt(38)
    title.paragraph_format.line_spacing = Pt(50)
    title.paragraph_format.keep_with_next = True
    for run in title.runs:
        run.font.size = Pt(38)
        run.font.bold = True
    intro.paragraph_format.space_before = Pt(0)
    intro.paragraph_format.space_after = Pt(0)
    intro.paragraph_format.line_spacing = Pt(22)
    for run in intro.runs:
        run.font.size = Pt(12)
        run.font.bold = False
    return title, intro
