# 原图提示与来源引用排版

验收日期：2026年10月19日。

## 行为

用户要求移除“3张原图随上述引用直接展示”，并将来源引用放到回答文字结束处。新回复提示明确要求引用紧接最后一句，不单列原图数量、展示方式或“原图如下”说明。

聊天模块提供助手回复专用 Markdown 插件，整理已经保存的回复中的独立记录引用及已明确取消的展示提示，不重写正式消息。只有带真实问题与经验链接的回复才应用整理；用户消息和一般资料查看器沿用原渲染。事实正文、代码、引文中的原话和图片业务说明保留；表格或代码后不适合接行内引用时仍保留独立引用。引用的实际标题、固定版本、顺序及原图关联不变。

## 自动化

Test Files：前端全量测试，新增 `frontend/tests/chat/record-answer-presentation.test.mjs`；后端 `tests/integration/handover/test_debug_images.py`、`tests/integration/knowledge` 和 `tests/architecture`。

Test Cases / Passed：前端 261 项，后端相关业务 18 项，架构 3 项。Failed：0。Skipped：0。Coverage：未采集。新增用例包含原截图格式的整理、已有行内引用、列表末项、多记录引用顺序、业务图片说明、代码/引文保留，以及表格边界。

首次构建发现可空插件参数的 TypeScript 错误，修正参数类型后 TypeScript 与生产构建通过。Ruff、Prettier 和差异检查通过。日志位于本机 `output/handover-cleanup/answer-citation-placement-{frontend,backend,architecture,build}.log`。

## 正式页面

部署前确认运行中的对话、阅读、代码验证和 reading 状态文件均为 0，再更新前端并重启服务。在原普通用户账号中打开用户标注的 7月23—24日回复，不重新生成或修改保存的消息：原先四个段落整理为一个正文段落，来源按钮是该段落的最后一个元素；“原图如下”和“3张原图随上述引用直接展示”均已消失。

只有一组对应记录的三张原图，v4 的第 0、1、2 处全部加载成功，重复图片仍保留。实际视口为 1211×892，未设置覆盖。正式截图及 DOM 检查结果位于 `output/handover-cleanup/answer-citation-placement-existing.{png,json}`。

Test Limitations：本轮验证既有真实回复的展示整理，没有再次调用供应商生成新回复；未来模型也可能产生其他说法，页面只处理已明确取消的独立展示提示，不采用任意含“原图”的句子都删除的规则。

Bugs Found：AI 多生成原图展示说明，并将来源另起段落，导致正文与原图之间出现冗余内容；代码及模型提示已调整。Test Quality：Medium。Markdown 真实渲染用例覆盖内容保留和引用边界，不能由少量真实模型问答推断所有输出格式。
