# 连续讲解版文档维护

本目录生成TU 8.1版与纠偏4.1版。两册共用P1、N1、基板1／基岛2／A点与芯片C1，正常主线先讲完整，配置、人工操作和异常再按需查。上版文件与业务源码不修改。

## 内容和配图

- tu_story.py与correction_story.py保存正文、当前阶段、所在部分、下一页承接句与旧主题对照。
- case_data.py保存共用输入和未舍入计算，两个版本的case-ledger.json必须一致。
- story_figures.py画主流程的设备动作、前后位置与记录，复用plain-language绘图基础生成同源PNG和SVG。旧版绘图文件不改动。
- publish.py从同一正文生成Word、Markdown、阅读索引、计算与代码索引及源码连续性报告。遇到依据文件变化立即停止，先重新核查。
- export.ps1只使用本次独立隐藏Word实例，更新原生目录、页码、嵌入字体并导出PDF。
- story_verify.py复用已验证的段落、图片与目录检查，再检查两册共用数字、每页导航与承接、独立公式和最终文件哈希。

## 生成和检查

先用Codex依赖加载器取得随包Python与工具路径，再运行：

```powershell
& $bundledPython docs/design/authoring/flow-guide/publish.py
& ./docs/design/authoring/flow-guide/export.ps1
& $bundledPython docs/design/authoring/flow-guide/story_verify.py --restore --render
```

三个入口均支持单册选择。Python参数为`--book tu`或`--book correction`，PowerShell参数为`-Book tu`或`-Book correction`。

本轮实际尝试了规范render_docx，两册均因PATH缺soffice.exe而失败。采用独立Word原生导出，再用Poppler按110 dpi渲染全部页面。页面位于output/design-flow-guide/tu与correction，只作校样，不提交。

PDF可能继承Word对图像的压缩。`--restore`按实际放置顺序恢复原始PNG数据，位置与显示尺寸保持一致，核对实际分辨率至少300 dpi。图片段落必须用自动行高，否则正文固定行高会裁图。

## 发布

逐页直接查看渲染图，检查图文关系、承接、文字避让与页面边界。改动后重新生成、导出与渲染；已经查看且像素完全一致的页面可以沿用本轮查看结果，像素有变化的页面必须重新直接查看。全部查看后，以`--record-reviewed-pages`显式传入实际确认的全册页码，生成绑定最终哈希的visual-review.json。

核对相对链接、生成源语法、Git差异与最终文件哈希，更新总入口和分册入口。仅提交本次文档与生成源并推送，不混入其他任务的工作。数字为说明例，静态源码核对与代理校样均不代表实机验收。
