# Linux 部署与 Windows 构建节点

助手服务部署在 Linux；ZX2200 是 Windows / .NET Framework 4.8 工程，实际编译和设备验证需要独立 Windows 节点。Linux 上的 Roslyn 分析器可以分析 C#，不能据此声称 ZX2200 已构建通过。

## 构建助手镜像

先在有权访问业务源码的开发环境按既有流程构建 `frontend/dist`。构建脚本只接收已构建页面，不读取或修改 `trunk`，也不绕过前端构建的源码资料一致性检查。

管理员准备并核实三个本机 Linux 基础镜像：Python 3.12 / Debian 12、.NET SDK 8、Docker CLI。使用固定 `sha256` 身份，同一 CPU 架构，不带镜像内置数据卷。版本更新后重新构建和验收；不要把示例中的占位符直接执行。

```sh
python scripts/deployment/build_linux.py \
  --python-image sha256:<核实后的Python镜像身份> \
  --dotnet-image sha256:<核实后的SDK镜像身份> \
  --docker-image sha256:<核实后的DockerCLI镜像身份>
```

构建器只复制助手源码、锁定依赖、数据库迁移、自带分析器、知识资源、执行模板和预构建页面。白名单目录中的链接、硬链接或私有配置会使构建失败。正式 `data`、业务 `trunk` 目录、Windows 虚拟环境和本机凭据不进入上下文。既有知识页面包含源码展示资料，不能把“未读取trunk目录”理解为镜像不含业务源码内容；镜像应作为公司内部制品管理，不公开发布。依赖准备阶段需要下载公开软件包；运行时不会因此获得供应商凭据。

镜像使用 UID/GID `10001:10001`，包含 .NET 运行时和编译好的自带 helper。构建结果及输入文件摘要写到本地 `output/linux-image-*.json`，不自动推送镜像仓库。

## 访问与持久化

以公司域名 `arks.example.com` 为示例，管理员显式设置：

```text
ARKS_ALLOWED_ORIGINS=https://arks.example.com
ARKS_TRUSTED_HOSTS=arks.example.com
TRUNK_AGENT_DATA_DIR=/var/lib/arks
TRUNK_AGENT_WORKSPACE=/workspace
```

`ARKS_ALLOWED_ORIGINS` 接受逗号分隔的完整 HTTP/HTTPS Origin，包含使用的非默认端口；`ARKS_TRUSTED_HOSTS` 接受精确 DNS 名称或 IP，不接受 URL、通配符和端口。两个变量必须同时设置，每个 Origin 的主机都要列入可信主机。配置错误在建立应用服务前直接拒绝启动。未配置时保持本机访问行为。

通过受管 HTTPS 反向代理访问应用，保留原始 `Host` 和 Cookie，支持流式响应，关闭代理缓冲。只把后端端口发布到本机或专用代理网络，不直接对公网开放。容器入口不信任转发头；HTTPS 会话根据显式来源配置设置 Secure Cookie，仍要求登录、权限和 CSRF。可信主机同时用于容器内部健康检查。

当前还有已确认的上线前缺口：既有知识静态资源和编译进前端包的知识数据可在未登录时下载。Host/Origin 白名单不解决会话授权，不能将本说明当作已经通过完整生产安全验收；先完成 [验收记录中的访问边界整改](../verification/linux-runtime.md) 再向公司用户开放。

将持久化卷挂到 `/var/lib/arks`，卷内文件应归 UID/GID `10001:10001`；业务源码单独只读挂到 `/workspace`。保持单服务、单进程使用同一数据目录，不使用多 worker。建议设置只读根文件系统、独立临时目录、禁用提权并配置 CPU、内存和进程限额。

镜像内的 Docker CLI 不代表应用自动拥有执行节点。不要为方便挂载宿主 Docker socket；按执行配置使用管理员准备的隔离节点和固定镜像。Windows 节点的准备与验收见 [Windows 执行器](../architecture/windows-executor.md)。

多语言语义检索还需要公开的 embedding 模型权重，应用镜像不携带本机缓存。管理员为 `/opt/arks/.tools/embedding-models` 准备独立模型卷，在可下载公开权重的受控准备容器中显式执行 `python -m app.modules.knowledge.setup`，完成 384 维输出检查后，运行容器只读挂载该卷。准备模型不需要模型供应商 API 密钥；正常问答只加载本地权重，不自动下载。缺少权重时不能宣称语义检索已就绪，现有关键词检索回退不等于语义模型通过验收。

首次启动生成的引导账号文件属于数据卷，只通过受控运维方式获取并及时更换密码，不把它放进镜像、报告或 Git。供应商配置和远程执行凭据由管理员另外配置，不随镜像分发。

## 现有 Windows 数据迁移

上线前停止写入并创建、校验备份，在独立目录恢复演练。不要只改变两个目录环境变量就认为迁移完成：现有项目、源码根、隔离副本与历史验证中可能包含 Windows 绝对路径和由路径产生的身份。

当前没有自动跨系统身份与路径映射工具。正式迁移需要明确旧根与新根、核对完整源码清单和文件摘要，保留项目及源码逻辑身份；迁移后重新建立当前平台的基线、测试与审核，不能复用 Windows 路径下的旧验证作为 Linux 验证。迁移方案未经演练时保留原环境，不对正式库进行字符串替换。

恢复工具现在支持目标目录本身是独立挂载根：解压暂存位于目标卷内，避免跨文件系统重命名。仍需停服、验证备份及恢复后的数据库、附件和访问权限，不能把备份文件存在等同于恢复可用。

## 隔离运行验收

`scripts/verification/linux_runtime` 只使用自建小型 C# 工程和独立临时数据。检查真实 Linux HTTP、域名来源与 CSRF、Roslyn 语义、隔离副本编辑、重启持久化、SQLite 一致性及备份恢复，不启动模型或业务设备程序。提供另一个设备上的空挂载根可验证独立卷恢复。

执行说明见 [验收脚本](../../scripts/verification/linux_runtime/README.md)。真实公司服务器上线、Windows 构建节点、ZX2200 私有依赖与设备验收需要在对应环境单独完成；本机 Docker 测试不能替代这些条件。
