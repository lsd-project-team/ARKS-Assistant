# Transport Unit第7.2版维护

仅更新TU分册，旧7.1与纠偏3.2发布文件保持原样。正文、封面和生成器分开维护；正式正文不包含制作过程、哈希日期、执行环境或文件用途说明。

`transport-unit/manuscript.py`是直接维护的正文BLOCKS，`transport-unit/build.py`生成Word、Markdown、原生数学对象、目录及引用；`cover.py`只保留标题与介绍。`appendix.py`控制打印附录中的关键短文件名与方法，详细路径和已读范围外置。

使用Codex工作区依赖加载器提供的Python、Node和Poppler。按以下顺序执行：

1. `transport-unit/audit_scope.py`重验所有C#文件及编译项，再输出方法级入口归属。它复用`output/design-publication-v7.1/syntax-index.json`前会检查每个文件和工程哈希；索引缺失或不符时，先运行保留的`../v7.1/syntax_inventory.py`重新生成。解析依赖为tree-sitter及tree-sitter-c-sharp，临时安装位置沿用忽略目录output/design-publication-v7.1/vendor。
2. 修改正文或插图后，运行`transport-unit/new_figures.py`生成六幅新增工程图PNG/SVG，再运行`transport-unit/build.py`。图源保存在docs/design/transport-unit/v7.2/figures，构建暂存于output/design-publication-v7.2/transport-unit。
3. 执行`transport-unit/export.ps1`，使用本机独立隐藏Word实例更新目录、页码与索引并导出PDF。仅操作本次文档，不接管其他已打开文件。
4. 执行`transport-unit/restore_pdf_images.py`恢复原始PNG图像流，位置和尺寸沿用Word导出。
5. 执行`transport-unit/verify_publication.py`、`transport-unit/verify_text_sync.py`与`transport-unit/verify_arithmetic.py`。文本检查包括逐段正文、图注、图表标题以及根据PDF实际表格边界提取的单元格，不能用跨列抽取顺序误判缺字。
6. 调用规范render_docx入口并检查日志。本机当前缺少soffice.exe；本轮已实际尝试并诊断，再采用Word原生导出与Poppler全页渲染进行视觉检查，不能声称LibreOffice已通过。
7. 将最终PDF全部页面渲染到output/tu-recheck/approved-pages并逐页查看。确认完成后才可运行`transport-unit/publish.py --confirm-all-pages-viewed`绑定最终哈希、核查记录并复制正式交付文件。
8. 更新两册入口，再运行`transport-unit/check_release.py`只读核对实际发布内容。核对Git范围后提交并推送。

业务源码只允许读取trunk/AKRS.ZX2200。evidence.py保留旧24条语义核查并验当前哈希，新增16条结论列本轮实际核读区段。扫描、名称级调用关系、静态语义、数值解释模型与实机验证分别记录，不把候选归属或清单项数写成全项目理解证明。

正文修改后必须重新生成Word与PDF、更新目录和图表索引、核对文本及实际页面。不要通过重新运行旧版过滤器拼接新正文，也不要沿用与当前文件哈希不匹配的全页确认记录。
