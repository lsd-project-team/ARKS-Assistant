# 两册7.1/3.1版维护与验证

正文维护稿已解析为本次版本BLOCKS，不依赖旧版revision/refine/readability过滤器。正式稿删除的制作说明不会因旧过滤器重新出现。源码根只有trunk/AKRS.ZX2200，保持只读。

每册按build.py → export.ps1 → restore_pdf_images.py顺序生成。输出是仓库忽略目录output/design-publication-v7.1对应子目录，已发布v7.1/v3.1保持不变。图源从各册已发布figures读取。PDF与Word共用正文、原生目录、OMML公式和精简引用附录。

先使用工作区依赖加载器取得Python和Poppler，依赖见requirements.txt；原生Word导出需本机安装Word。导出脚本只操作本次独立隐藏实例。规范render_docx入口缺少LibreOffice时，使用本次记录的Word导出和Poppler全页校样路径。不要把文件结构检查当作视觉通过。

verify_publications.py核对暂存导出稿的结构、字体、图像分辨率、目录书签和既有算例，verify_supply_compensation.py核对供料/补偿算例。verify_revision.py按语法表达式比较八个入口纯条件1024组组合并核对新增10组数值。syntax_inventory.py可重扫本目录，coverage_discovery.py从语法调用与赋值重新发现候选；扫描不代表业务逐文件通读或精确类型绑定。所有读取均有源码范围断言。语法依赖可装入忽略目录output/design-publication-v7.1/vendor。

new_figures.py与diagrams.py保留本轮五幅精确工程图的绘制源；所有现用图本身随各册以SVG/PNG保存。概念生图提示词保存在各册illustration-provenance.json。

check_release.py只读核查已经发布的文件哈希、源码锚点、覆盖归属、要求与页面检查记录，并编译维护脚本语法，不执行排版器。重新生成后必须重新做源码结论核对、计算验证、阅读走查和最终全页直接查看，再由维护者更新发布目录及记录；脚本不自动签署用户验收。
