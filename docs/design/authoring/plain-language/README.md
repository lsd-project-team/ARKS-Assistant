# 两册图解文档的维护

本目录生成TU第8版与纠偏第4版，旧版发布文件不修改。正文、配图和输出职责分开；业务源码只读。

## 文件

- tu_content.py与correction_content.py：直接维护的中文正文，每页一个设备场景或具体问题。
- drawing.py：同源PNG/SVG的绘图基础；保留精确文字、箭头、比例和可编辑图源。
- figures.py：每页对应的产品、设备、坐标、过程或记录插图；补充图不替代正文解释。
- build.py：构建Word、Markdown和旧版章节对照；构建时重验上版依据文件哈希，变化则停止，要求重新核查。
- export.ps1：独立隐藏Word实例更新原生目录并导出PDF，不接管用户文档。
- verify.py：正文逐段与对应页核对、目录页码、图像和字体、20项独立数值复算、源码连续性以及Poppler全页渲染。
- record_review.py：实际看完所有页面后，将全页或变化页的视觉确认绑定最终文件哈希；变化页未明确重看时拒绝记录。

## 运行

先通过Codex工作区依赖加载器取得Python、Node和Poppler路径，再使用该Python执行：

```powershell
& $bundledPython docs/design/authoring/plain-language/build.py
& ./docs/design/authoring/plain-language/export.ps1
& $bundledPython docs/design/authoring/plain-language/verify.py --restore --render
```

三个命令均支持`--book tu`或`--book correction`，PowerShell导出参数对应`-Book tu`或`-Book correction`。默认生成两册。

必须实际尝试规范render_docx入口并诊断失败。本机本次缺soffice.exe，因此使用Word原生PDF导出与Poppler全页渲染进行视觉校样，没有声称LibreOffice通过。生成的页面在output/design-plain-language/tu与correction，不提交临时页面。

Word可能压缩图像，verify.py的--restore按放置顺序恢复原始PNG流，不改变其位置和尺寸。图片段落必须使用自动行高，避免继承正文固定行高而裁切；核对图片的实际显示高度，不能仅看其PDF对象存在。

## 发布核对

所有正文或图片变化之后，重新构建、原生导出、核对和渲染，直接查看全部最终页面，修正问题后重做。visual-review.json只绑定实际看过的当前文件哈希，不能沿用之前版本的确认。

更新两册README和总入口，保留上版文件；检查本次Git路径，再只提交本次文档及生成源并推送。并行任务的未提交或已暂存变更不得混入本次提交。
