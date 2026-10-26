# 两册简明图解稿的维护

本目录生成TU 8.2与纠偏4.2。阅读稿只显示具体动作、部件、状态与必要条件，移除分部名称、每页导航、承接句、代码字段和坐标算式。旧版完整技术内容由各册配套资料链接保留。

content.py保存正文、图注与旧版主题对照；pictures.py用相同几何生成PNG和SVG；make.py生成Word、Markdown、目录与源码连续性记录；export.ps1在独立隐藏Word实例中更新目录并导出PDF；check.py检查逐段正文、页码、图像、字体、被移除的文字和源码哈希。

通过Codex依赖加载器获取随包Python，再运行：

```powershell
& $bundledPython docs/design/authoring/simple-guide/make.py
& ./docs/design/authoring/simple-guide/export.ps1
& $bundledPython docs/design/authoring/simple-guide/check.py --restore --render
```

规范render_docx必须实际尝试并诊断错误。本机缺soffice.exe时，采用独立Word原生导出加Poppler逐页渲染，临时页面在output/design-simple-guide，不提交。图像段落使用自动行高；--restore恢复PDF中的原始PNG流，确保插图清晰且不改变摆放。

生成后逐页查看全部页面，检查部件、箭头、图注、段落与页面边界。内容或版式改动后重新导出、检查并查看变化页；未变化页面需确认与本轮已经查看的图像像素一致。全部确认后，传入--book与--reviewed-pages记录实际查看的完整页码，绑定最终文件哈希。

检查生成源语法、相对链接、Git差异和交付文件哈希，仅提交本次文档及生成源并推送。业务源码保持只读。代理校样不等于设备验证或独立真人试读。
