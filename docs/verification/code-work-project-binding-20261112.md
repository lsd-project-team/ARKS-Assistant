# 代码工作项目绑定（解绑固定项目名）验收

日期：2026-11-12。

## 范围

本轮只改“配置与识别”层：把写死的 `AKRS.ZX2200` 换成按目录结构识别主工程，并把执行环境从一份全局配置改成按项目保存。合并、验证宿主、聊天工具和前端交互行为保持不变；`checks.py` 里生成验证宿主时使用的业务命名空间、`AKRS.ZX2200.exe` 引用和 `VirtualMotionDrivers.Tests` 工程仍属于下一步能力层适配，本轮未改。

## 改动

- `backend/app/modules/code_work/files.py`：新增 `main_project(root)`，按“同名 `.csproj` + `Infrastructure/Simulation/OriginalSimulation.cs`”识别唯一主工程；副本复制、依赖输出复制、可编辑范围、合并锁文件、构建目标、新增文件导入项和事务写回都改为使用识别结果。
- `backend/app/modules/code_work/environment.py`：执行环境按项目 ID 存放在 `code-work.local.json` 的 `projects` 映射中，保存时校验源码根的主工程结构并记录识别结果；`migrate_legacy` 把旧版单份配置迁到默认项目。
- `backend/app/modules/projects/service.py`：启动时迁移旧配置；默认项目之外的项目不继承环境。
- `backend/app/modules/projects/router.py`：项目分派器挂载 `/api/p/{project}/settings/code-work`，每个项目独立读写自己的环境；根路径 `/api/settings/code-work` 仍指默认项目。
- `backend/app/modules/code_work/service.py`：`CodeWork` 使用所属项目的环境；新建副本在状态中记录识别出的主工程，恢复、导出、差异和撤销优先使用该记录，旧副本回退到目录识别。
- 前端：环境面板沿用当前项目作用域请求，增加项目识别结果显示，缓存键带上项目，文案去掉固定项目名。

## 验证

- 新增 `backend/tests/unit/code_work/test_environment.py`：识别通用项目名、缺主工程/多主工程拒绝、按项目隔离保存、旧配置迁移、通用项目完整建副本和编辑闭环。
- `tests/unit/code_work`：98 项通过。
- 代码副本集成：`tests/integration/chat/test_code_work.py`、`test_code_work_complete.py`、`tests/integration/projects/test_removed_code_work.py` 共 13 项通过。两个账号隔离用例改为由管理员为测试项目单独配置源码，验证项目不再继承默认环境。
- 全量后端：1353 项通过、2 项跳过、13 项失败；失败全部位于 `tests/integration/settings` 和 `test_retrieval_budget`，堆栈为本机 `NO_PROXY` 含 `[::1]` 导致的代理地址解析错误（`httpx2.InvalidURL`），与本轮改动无关，此前已有同类记录。
- 前端：`npx tsc -b` 通过，`npm test` 473 项通过。
- 真实数据：重启服务后 `data/code-work.local.json` 由单份配置迁为默认项目 `c410e4aa…` 下的条目，源码路径、MSBuild 和时限原样保留；真实 trunk 中只有 `AKRS.ZX2200` 同时具备两个识别标记，识别结果与原固定名一致。
- 服务：`Start.ps1` 方式启动后 `/api/health` 返回 200，工作区和数据目录不变。

## 未完成和边界

- 项目环境目前只通过接口按项目读写；管理端页面仍是“当前项目的环境”，项目列表式的统一管理界面留待下一步。
- 每个项目一份工作区（项目而不是对话持有副本）尚未实施，当前仍是“一个对话一份副本，全部取自所属项目配置”。
- 验证宿主的业务命名空间、固定测试工程和 `.exe` 名称仍由 ARKS 适配器提供；接入非 ARKS 或非 C# 项目前需先抽验证器接口。
