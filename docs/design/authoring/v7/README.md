# 两册设计文档生成与维护

正文维护稿已展开为当前版本BLOCKS，不再依赖旧版revision、refine或readability过滤器；删除的制作说明和旧的阈值断言不会由这些过滤器恢复。PDF与Word的封面、正文、表格、公式、精简附录由各册build.py统一产生。

运行前使用Codex工作区依赖加载器取得Python、Word和Poppler。按顺序运行目标册的build.py、export.ps1、restore_pdf_images.py，输出在仓库output/design-publication-v7对应子目录。源码依据仅从trunk/AKRS.ZX2200读取，已发布图源从本轮v7/v3/figures读取；不修改已发布版本。重新导出必须更新字段和目录、执行结构检查、重新渲染全部页面并逐页查看后再发布。

build.py只负责排版，不自动重新声称源码结论仍然有效；源码变更后应重做核查并维护claim-map及审查范围。PDF采用原生Word导出，独立隐藏实例只打开本轮文件；原始PNG流恢复后需再次校样。模板依赖python-docx、lxml、Pillow、pdfplumber与pypdf。

已发布版本可运行check_release.py，核对最终文件哈希、源码范围与定位、入口归属、模板语法和README链接。verify_publications.py重新检查已发布Word/PDF的结构并复算既有算例；verify_supply_compensation.py复算新增供料、选点及补偿边界。后两项只把报告写入output/design-publication-v7，不覆盖已发布记录；重新生成的报告不能代替全页视觉检查。
