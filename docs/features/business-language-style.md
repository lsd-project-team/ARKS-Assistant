# 功能与流程说明的业务语言规范

「流程图谱」和「功能说明」已改为应用自带的独立资料，不再依赖项目源码，也不再声称与某一版源码逐行一致。读者是设备工程师、工艺人员和操作人员，不是维护这段代码的程序员。

## 改写范围

只改写给读者看的说明文字：

- `frontend/src/features/knowledge/reviews/*.ts` 中的流程 `text`、步骤 `text`、分支 `label` / `text`、复核边界 `text`。
- `frontend/src/features/knowledge/data/archifyData.ts` 中 8 张内置图谱的节点 `detail`、卡片 `items`、连线 `label`。
- `frontend/src/features/knowledge/data/presentation.ts` 中专题的 `purpose`、`conditions`、`exceptions`。

不要改：

- 任何 `id`、`topic`、`diagrams`、`initialFlows`、文件导出名和导入关系。
- 流程与步骤的 `title`（页面目录和测试依赖这些标题）。
- `refs` 数组、`sha256`、资源路径、图谱节点 `signals`。
- 测试、构建脚本和图谱 HTML 本身。

## 用语要求

1. 用业务动作和状态描述，不用代码结构描述。例如「就绪检查通过后进入工作状态」，不写「Prepare 返回 true 后 SetState(Working)」。
2. 不出现源码文件名、目录、行号、类名、方法名、变量名、枚举值、`true/false`、箭头函数或代码片段。
3. 状态词统一成中文业务词：

| 原词 | 业务写法 |
| --- | --- |
| Success | 成功 |
| Retry | 重试 |
| Abort | 中止 |
| Ignore | 忽略 |
| Exception | 异常 |
| NoStart | 未启动 |
| Finished / Done | 已完成 |
| None | 无 / 不启用 |
| DryCycle | 空跑 |
| Running | 运行中 |
| WaitStart | 等待启动或停止指令 |
| Working | 工作状态 |

4. 保留事实边界：条件、分支、失败后的处理、未确认之处都要保留，不能为了通顺补造未发生的能力。
5. 每一步 1–3 句，先讲触发条件，再讲动作，最后讲结果或例外。分支标签用短语，例如「来料超时」「检查未通过」。
6. 保留 S1、S2、G0、ETEL、固高、雷赛、BMC、LVDT、PR 等行业术语；其余代码缩写尽量换成业务说法。
7. 读起来像交接说明或操作手册，而不是代码审查记录。不要出现「源码」「代码里」「方法返回」「调用栈」「分支语句」等说法。

## 示例

改写前：

> 仅 Prepare 返回 true 后 SetState(Working)；是状态赋值与记录，不是所有任务启动成功的确认。

改写后：

> 只有就绪检查通过，系统才进入工作状态。这里只表示状态已切换并留下记录，不代表各个生产任务都已经成功启动。

改写前：

> StartTask 先检查输送配置并初始化模块，再分 DryCycle 与普通模式。

改写后：

> 输送任务启动时先检查是否配置了输送并完成初始化，然后区分空跑和正常生产两种模式。
