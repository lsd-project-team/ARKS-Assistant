# 纠偏过程第3.2版维护与验证

正文直接维护在manuscript.py的BLOCKS中。build.py与cover.py分别维护排版及封面，封面仅保留大标题和介绍。旧版正文、制作说明过滤器不参与生成；TU分册不在本次生成范围内。

使用工作区依赖加载器返回的Python、Node和Poppler。原生Word导出需要本机Word，export.ps1只操作本次独立隐藏实例。规范render_docx入口已实际尝试，缺少捆绑LibreOffice时按原生Word导出、恢复原始PNG流、Poppler渲染的路径验证；不能仅凭DOCX结构认为排版正确。

生成顺序：

1. 需要重绘时执行new_figures.py，生成本次六幅精确工程图的PNG与SVG。图源保存在本册发布目录figures，现有概念生图不重绘。
2. 执行build.py，输出到output/correction-v3.2，生成Word、Markdown及源码依据索引。
3. 执行export.ps1，更新Word原生目录、页码和引用并导出PDF。
4. 执行restore_pdf_images.py，按原始PNG恢复PDF图像流，保持Word导出的图像位置与尺寸。
5. 用捆绑Poppler全页渲染并逐页查看。任何正文、公式、表格或图片改动之后，都要重新验证最终文件。

源码仍只允许读取trunk/AKRS.ZX2200。audit_scope.py重扫当前C#语法树、编译项、构造、泛型UI调用、关键写入及方法声明，扫描不能代替语义阅读。语法依赖优先用已安装tree-sitter与tree-sitter-c-sharp；本次依赖位于忽略目录output/design-publication-v7.1/vendor，可由requirements.txt安装到工作区临时目录后设置PYTHONPATH。

review_records.py保留第3.1版的已核对结论并逐项重新验哈希及锚点，同时保存本次新增区段、结论和候选入口归属。它依赖仓库内保留的v3.1核查资料，不能把该脚本产生的声明当作新的人工阅读。源码有变化时必须重新读受影响方法、调用方和消费者，再更新具体结论与范围。

数值与结构核对：

- verify_new.py：新增图示、整数转换、角度阈值、均值与中位数边界，并生成独立Huber参考结果。
- verify_calculator.ps1：只编译原始CompensateCalculator纯数值类，18项检查，不加载设备程序集或业务流程；先运行verify_new.py。
- verify_publication.py：字体、原生公式、目录页码、书签、引用、图表索引、页面边界、原始图像分辨率及既有几何公式。
- verify_text_sync.py：逐段检查127段维护正文在Word与PDF中完整保留；原生数学下标按其基线处理，不以抽取顺序误判缺字。
- record_qa.py是本次46页发布的复核记录工具，确认标志只允许在全页实际查看后使用。页数、图表或版式改变时必须相应更新实测范围，不能沿用旧确认。

本轮最后两幅图仅调整标注避让，DOCX只替换同尺寸嵌入PNG，文字及字段XML原样保留；PDF同步替换图像流后全部46页重渲染，44页像素一致，变化的38、40页重新直接查看。证据在配套media-pixel-comparison.json和final-qa.json。

发布到docs/design/correction-process/v3.2后，check_release.py只读核对发布文件、哈希、源码范围及验收记录，不重新导出文档。旧版保留，入口及Git提交推送按实际发布结果更新。
